"""Main pipeline orchestrator for art-openings-syd."""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from fetch import fetch_all
from instagram import fetch_instagram
from parse import parse_result, is_exhibition, is_current
from state import load_state, save_state, set_record, sweep_closed
from dedup import is_duplicate
from notify import notify_new_exhibition, check_alerts
from build_data import build


def make_id(title, venue, url):
    """Generate a stable record ID."""
    raw = f"{title}|{venue}|{url}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


MANUAL_FILE = "manual.json"

# Fields refreshed from manual.json on every run. "status" is deliberately not
# here: sweep_closed and build_data's 30-day auto-close own it once a record
# exists, and rewriting it each run would resurrect finished shows.
MANUAL_FIELDS = (
    "title", "artist", "venue", "address", "suburb",
    "start_date", "end_date", "opening_date", "opening_time",
    "website", "instagram", "description",
)


def merge_manual(state):
    """Merge hand-entered exhibitions from manual.json into state.

    For shows no scraper can reach: appointment-only spaces, unlisted
    addresses, Instagram-only galleries without a business account.
    Returns the number of newly inserted records.
    """
    if not os.path.exists(MANUAL_FILE):
        return 0

    try:
        with open(MANUAL_FILE) as f:
            entries = json.load(f).get("exhibitions", [])
    except (ValueError, OSError) as e:
        print(f"[manual] Could not read {MANUAL_FILE}: {e}")
        return 0

    added = 0
    for entry in entries:
        title = (entry.get("title") or "").strip()
        venue = (entry.get("venue") or "").strip()
        if not title:
            print("[manual] Skipped an entry with no title")
            continue

        record_id = make_id(title, venue, entry.get("website", ""))
        existing = state.get(record_id)

        if existing:
            for field in MANUAL_FIELDS:
                if field in entry:
                    existing[field] = entry[field]
            continue

        record = {field: entry.get(field, "") for field in MANUAL_FIELDS}
        record["source"] = entry.get("source", "manual")
        record["status"] = entry.get("status", "active")
        set_record(state, record_id, record)
        added += 1

        if record["status"] == "active":
            notify_new_exhibition(record)

    if added:
        print(f"[manual] Added {added} hand-entered exhibitions")
    return added


def run():
    print(f"\n{'='*60}")
    print(f"Art Openings Sydney - {datetime.now(tz=timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    state = load_state()

    # 1. Sweep closed exhibitions
    closed_count = sweep_closed(state)
    if closed_count:
        print(f"[sweep] Marked {closed_count} exhibitions as closed")

    # 2. Fetch from all sources
    raw_results = fetch_all()

    # 3. Fetch Instagram (separate because it needs auth)
    try:
        ig_results = fetch_instagram()
        raw_results.extend(ig_results)
    except Exception as e:
        print(f"[instagram] Skipped: {e}")

    # Reload state after instagram fetch -- fetch_instagram saves the checkpoint
    # internally and we must not overwrite it with the stale pre-fetch state
    state = load_state()

    # 4. Filter and parse
    new_count = 0
    updated_count = 0

    for raw in raw_results:
        # Quick relevance filter (skip for pre-curated sources)
        PREFILTERED_SOURCES = {"art_almanac", "instagram"}
        if raw.get("source") not in PREFILTERED_SOURCES and not is_exhibition(raw):
            continue

        # Parse structured data
        record = parse_result(raw)
        title = record["title"]
        venue = record["venue"]
        url = raw.get("url", "")

        # Skip if no title
        if not title or title == "Untitled":
            continue

        # Skip records with no venue from non-curated sources -- these are
        # listicle pages, SEO articles, and social posts, not exhibition listings
        if not venue and raw.get("source") not in PREFILTERED_SOURCES:
            continue

        # Skip records with no dates at all from serper -- real exhibition
        # listings always have a date; dateless serper results are noise
        if raw.get("source") == "serper":
            if not record.get("start_date") and not record.get("end_date") and not record.get("opening_date"):
                continue

        # Skip old dates (pre-current-year)
        if not is_current(record):
            continue

        # Check dedup
        if is_duplicate(state, title, venue):
            # Could update existing record with new info if useful
            continue

        # Generate ID and store
        record_id = make_id(title, venue, url)
        if record_id in state:
            continue

        # Determine status
        if not record["start_date"] and not record["opening_date"]:
            record["status"] = "needs_review"
        else:
            # Mark already-ended exhibitions as closed immediately
            end = record.get("end_date")
            if end:
                from datetime import date
                try:
                    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
                    if end_dt < datetime.now(tz=timezone.utc).date():
                        record["status"] = "closed"
                except ValueError:
                    pass

        set_record(state, record_id, record)
        new_count += 1

        # Notify Discord (only active records)
        if record["status"] == "active":
            notify_new_exhibition(record)

    print(f"\n[pipeline] {new_count} new exhibitions added")

    # 5. Merge hand-entered exhibitions
    merge_manual(state)

    # 6. Check opening-soon / closing-soon alerts
    check_alerts(state)

    # 7. Save state
    save_state(state)

    # 8. Build frontend data
    build()

    # 9. Update gallery database
    from galleries import update_galleries
    update_galleries(state)

    print(f"\n[done] Pipeline complete")


if __name__ == "__main__":
    run()
