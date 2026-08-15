"""State management for art-openings-syd pipeline."""

import json
import os
from datetime import datetime, timezone

STATE_FILE = "seen.json"


def load_state():
    """Load state from seen.json, return dict."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"__dedup_index__": {}, "__meta__": {"last_run": None}}


def save_state(state):
    """Save state to seen.json."""
    state["__meta__"]["last_run"] = datetime.now(tz=timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def get_record(state, record_id):
    """Get a record by ID."""
    return state.get(record_id)


def set_record(state, record_id, record):
    """Set a record, updating dedup index."""
    from dedup import canonical_key

    state[record_id] = record
    ckey = canonical_key(record.get("title", ""), record.get("venue", ""))
    if ckey:
        state["__dedup_index__"][ckey] = record_id


def sweep_closed(state):
    """Mark past-end-date active records as closed."""
    today = datetime.now(tz=timezone.utc).date()
    count = 0
    for key, rec in state.items():
        if key.startswith("__"):
            continue
        if rec.get("status") != "active":
            continue
        end = rec.get("end_date")
        if end:
            try:
                end_dt = datetime.strptime(end, "%Y-%m-%d").date()
                if end_dt < today:
                    rec["status"] = "closed"
                    count += 1
            except ValueError:
                pass
    return count
