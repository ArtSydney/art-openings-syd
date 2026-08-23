"""Build docs/data.json from seen.json for the frontend."""

import json
import os
from datetime import datetime, timezone

from state import load_state
from galleries import load_galleries, fuzzy_match_gallery


def build():
    """Filter active + closed records and write docs/data.json."""
    state = load_state()
    galleries = load_galleries()

    records = []

    for key, rec in state.items():
        if key.startswith("__"):
            continue

        status = rec.get("status", "active")
        if status not in ("active", "closed"):
            continue

        venue = rec.get("venue", "")

        # Resolve venue to canonical gallery name so frontend name-lookup always matches,
        # regardless of whether the scraper wrote "Sullivan + Strumpf" or "Sullivan+Strumpf"
        gallery_key = fuzzy_match_gallery(galleries, venue) if venue else None
        canonical_venue = galleries[gallery_key]["name"] if gallery_key else venue

        records.append({
            "id": key,
            "title": rec.get("title", ""),
            "artist": rec.get("artist", ""),
            "venue": canonical_venue,
            "gallery_key": gallery_key or "",
            "address": rec.get("address", ""),
            "suburb": rec.get("suburb", ""),
            "start_date": rec.get("start_date", ""),
            "end_date": rec.get("end_date", ""),
            "opening_date": rec.get("opening_date", ""),
            "opening_time": rec.get("opening_time", ""),
            "website": rec.get("website", ""),
            "instagram": rec.get("instagram", ""),
            "description": rec.get("description", ""),
            "source": rec.get("source", ""),
            "status": status,
        })

    # Sort: opening_date or start_date, soonest first
    def sort_key(r):
        d = r.get("opening_date") or r.get("start_date") or "9999-12-31"
        return d

    records.sort(key=sort_key)

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    # Split into current (active/upcoming) and full archive
    current = [r for r in records if (
        r["status"] != "closed" or
        (r.get("end_date") and r["end_date"] >= today)
    )]

    output_full = {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(records),
        "exhibitions": records,
    }

    output_current = {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(current),
        "exhibitions": current,
    }

    os.makedirs("docs", exist_ok=True)

    # Full archive (used when "Show closed" is ticked)
    with open("docs/data.json", "w") as f:
        json.dump(output_full, f, indent=2, default=str)

    # Current only (default load -- much smaller)
    with open("docs/data-current.json", "w") as f:
        json.dump(output_current, f, indent=2, default=str)

    print(f"[build] Wrote {len(records)} exhibitions to docs/data.json ({len(current)} current)")


if __name__ == "__main__":
    build()
