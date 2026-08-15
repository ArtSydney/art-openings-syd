"""Build docs/data.json from seen.json for the frontend."""

import json
import os
from datetime import datetime, timezone

from state import load_state


def build():
    """Filter active + closed records and write docs/data.json."""
    state = load_state()
    records = []

    for key, rec in state.items():
        if key.startswith("__"):
            continue
        status = rec.get("status", "active")
        if status not in ("active", "closed"):
            continue

        records.append({
            "id": key,
            "title": rec.get("title", ""),
            "artist": rec.get("artist", ""),
            "venue": rec.get("venue", ""),
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

    output = {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(records),
        "exhibitions": records,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[build] Wrote {len(records)} exhibitions to docs/data.json")


if __name__ == "__main__":
    build()
