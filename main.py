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

        # Skip old dates (pre-2026)
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

    # 5. Check opening-soon / closing-soon alerts
    check_alerts(state)

    # 6. Save state
    save_state(state)

    # 7. Build frontend data
    build()

    # 8. Update gallery database
    from galleries import update_galleries
    update_galleries(state)

    print(f"\n[done] Pipeline complete")


if __name__ == "__main__":
    run()
