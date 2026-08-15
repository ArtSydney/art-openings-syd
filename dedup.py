"""Deduplication for art-openings-syd pipeline."""

import re

# Words too generic to be distinctive in exhibition titles
GENERIC_WORDS = {
    "exhibition", "show", "gallery", "art", "artist", "artists",
    "opening", "group", "solo", "new", "works", "work", "the",
    "and", "of", "in", "at", "for", "a", "an", "to", "by",
    "from", "with", "on", "sydney", "nsw", "australia",
    "painting", "paintings", "sculpture", "sculptures",
    "photography", "drawing", "drawings", "prints", "print",
    "contemporary", "modern", "abstract", "figurative",
    "mixed", "media", "installation", "performance",
}


def canonical_key(title, venue=""):
    """Generate canonical dedup key from title + venue."""
    if not title:
        return ""
    text = f"{title} @ {venue}" if venue else title
    text = text.lower()
    text = re.sub(r"20\d{2}", "", text)  # strip years
    text = re.sub(r"[^\w\s]", "", text)  # strip punctuation
    words = text.split()
    distinctive = sorted(w for w in words if w not in GENERIC_WORDS and len(w) > 1)
    return " ".join(distinctive) if distinctive else ""


def is_duplicate(state, title, venue=""):
    """Check if a title+venue combo already exists in state."""
    ckey = canonical_key(title, venue)
    if not ckey:
        return False
    return ckey in state.get("__dedup_index__", {})


def find_existing_id(state, title, venue=""):
    """Return existing record ID if duplicate, else None."""
    ckey = canonical_key(title, venue)
    if not ckey:
        return None
    return state.get("__dedup_index__", {}).get(ckey)
