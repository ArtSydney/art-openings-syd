"""Rule-based parser for exhibition details from raw text/snippets."""

import re
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Date patterns
# ---------------------------------------------------------------------------

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

MONTH_PATTERN = "|".join(MONTHS.keys())

# "12 August 2026" or "12 Aug 2026" or "August 12, 2026"
DATE_RE = re.compile(
    rf"(\d{{1,2}})\s*(?:st|nd|rd|th)?\s+({MONTH_PATTERN})\s+(\d{{4}})"
    rf"|({MONTH_PATTERN})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})",
    re.IGNORECASE,
)

# Date range: "12 Aug - 30 Sep 2026" or "12 August to 30 September 2026"
DATE_RANGE_RE = re.compile(
    rf"(\d{{1,2}})\s*(?:st|nd|rd|th)?\s+({MONTH_PATTERN})"
    rf"\s*[-\u2013to]+\s*"
    rf"(\d{{1,2}})\s*(?:st|nd|rd|th)?\s+({MONTH_PATTERN})\s+(\d{{4}})",
    re.IGNORECASE,
)

# Time pattern for openings: "6pm", "6:30pm", "5:30 PM"
TIME_RE = re.compile(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))", re.IGNORECASE)

# Opening night signals
OPENING_SIGNALS = [
    r"opening\s+(?:night|reception|event|drinks?)",
    r"opening\s+\d",
    r"preview\s+(?:night|evening)",
    r"private\s+view",
    r"launch\s+(?:night|event|party)",
    r"vernissage",
]
OPENING_RE = re.compile("|".join(OPENING_SIGNALS), re.IGNORECASE)


def parse_date(text):
    """Extract first date from text, return YYYY-MM-DD or None."""
    m = DATE_RE.search(text)
    if not m:
        return None
    if m.group(1):  # "12 August 2026" form
        day, month_str, year = m.group(1), m.group(2), m.group(3)
    else:  # "August 12, 2026" form
        month_str, day, year = m.group(4), m.group(5), m.group(6)
    month = MONTHS.get(month_str.lower())
    if not month:
        return None
    try:
        dt = datetime(int(year), month, int(day))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_date_range(text):
    """Extract date range, return (start_date, end_date) or (None, None)."""
    m = DATE_RANGE_RE.search(text)
    if not m:
        # Fall back to finding two individual dates
        dates = []
        for dm in DATE_RE.finditer(text):
            if dm.group(1):
                day, month_str, year = dm.group(1), dm.group(2), dm.group(3)
            else:
                month_str, day, year = dm.group(4), dm.group(5), dm.group(6)
            month = MONTHS.get(month_str.lower())
            if month:
                try:
                    dt = datetime(int(year), month, int(day))
                    dates.append(dt.strftime("%Y-%m-%d"))
                except ValueError:
                    pass
        if len(dates) >= 2:
            return dates[0], dates[1]
        elif len(dates) == 1:
            return dates[0], None
        return None, None

    start_day = int(m.group(1))
    start_month = MONTHS.get(m.group(2).lower())
    end_day = int(m.group(3))
    end_month = MONTHS.get(m.group(4).lower())
    year = int(m.group(5))

    try:
        start = datetime(year, start_month, start_day).strftime("%Y-%m-%d")
        end = datetime(year, end_month, end_day).strftime("%Y-%m-%d")
        return start, end
    except ValueError:
        return None, None


def parse_opening_date(text):
    """Try to find a specific opening night date."""
    m = OPENING_RE.search(text)
    if not m:
        return None, None
    # Look for a date near the opening signal
    context = text[max(0, m.start() - 100):m.end() + 200]
    date = parse_date(context)
    time_m = TIME_RE.search(context)
    time_str = time_m.group(1).strip() if time_m else None
    return date, time_str


# ---------------------------------------------------------------------------
# Venue / address extraction
# ---------------------------------------------------------------------------

# Common Sydney gallery names for recognition
KNOWN_GALLERIES = [
    "White Rabbit Gallery", "MCA", "Museum of Contemporary Art",
    "Art Gallery of NSW", "AGNSW", "Artspace", "Carriageworks",
    "National Art School", "SH Ervin Gallery", "Brett Whiteley Studio",
    "Object Gallery", "Roslyn Oxley9 Gallery", "Sullivan+Strumpf",
    "Sarah Cottier Gallery", "Darren Knight Gallery", "Michael Reid",
    "Martin Browne Contemporary", "Olsen Gallery", "King Street Gallery",
    "Tim Olsen Gallery", "Dominik Mersch Gallery", "Station Gallery",
    "4A Centre for Contemporary Asian Art", "Verge Gallery",
    "UTS Gallery", "UNSW Galleries", "Firstdraft", "ALASKA Projects",
    "China Heights Gallery", "Cement Fondu", "The Commercial",
    "Piermarq*", "Depot Gallery", "Flinders Street Gallery",
    "The Cross Art Projects", "Grantpirrie", "Liverpool Street Gallery",
    "Wentworth Galleries", "Stanley Street Gallery",
    "Powerhouse Museum", "Australian Museum",
]

# Sydney suburb list for address extraction
SYDNEY_SUBURBS = [
    "Surry Hills", "Paddington", "Chippendale", "Darlinghurst",
    "Redfern", "Waterloo", "Newtown", "Marrickville", "Glebe",
    "Rozelle", "Balmain", "Pyrmont", "Ultimo", "The Rocks",
    "Circular Quay", "Potts Point", "Woolloomooloo", "Alexandria",
    "Erskineville", "Enmore", "Leichhardt", "Annandale",
    "Barangaroo", "Haymarket", "CBD", "Sydney CBD",
    "Woollahra", "Double Bay", "Rose Bay", "Mosman",
    "Neutral Bay", "Camperdown", "St Peters", "Mascot",
    "Randwick", "Coogee", "Bondi", "Manly", "Parramatta",
    "Liverpool", "Penrith", "Blacktown", "Chatswood",
    "North Sydney", "McMahons Point", "Millers Point",
]


def extract_venue(text, title=""):
    """Try to identify gallery/venue name from text."""
    for gallery in KNOWN_GALLERIES:
        if gallery.lower() in text.lower():
            return gallery
    # Try "at [Venue]" pattern
    m = re.search(r"at\s+(?:the\s+)?([A-Z][A-Za-z\s&'+*]+?)(?:\s*[,.\n]|\s+on\s|\s+from\s|\s+\d)", text)
    if m:
        venue = m.group(1).strip()
        if len(venue) > 3 and len(venue) < 80:
            return venue
    return ""


def extract_suburb(text):
    """Find a Sydney suburb mention in text."""
    for suburb in SYDNEY_SUBURBS:
        if suburb.lower() in text.lower():
            return suburb
    return ""


def extract_address(text):
    """Try to extract a street address."""
    m = re.search(r"(\d+[A-Za-z]?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:St(?:reet)?|Rd|Road|Ave(?:nue)?|Dr(?:ive)?|Ln|Lane|Pl(?:ace)?|Cres(?:cent)?|Pde|Parade|Blvd|Terrace|Tce|Way|Circuit|Ct|Court))", text)
    if m:
        return m.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Artist extraction
# ---------------------------------------------------------------------------

def extract_artist(text, title=""):
    """Try to extract artist name(s)."""
    # "by [Artist]" pattern
    m = re.search(r"by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", text)
    if m:
        return m.group(1).strip()
    # "[Title] by [Artist]" in title
    m = re.search(r"by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", title)
    if m:
        return m.group(1).strip()
    # "Artist: [Name]"
    m = re.search(r"(?:artist|artists?):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Website / social extraction
# ---------------------------------------------------------------------------

def extract_website(text, url=""):
    """Extract or derive website URL."""
    # If the result URL is a gallery website, use it
    if url and not any(d in url for d in ["timeout.com", "broadsheet.com", "artalmanac.com",
                                           "artguide.com", "instagram.com", "google.com"]):
        return url
    # Look for URLs in text
    m = re.search(r"(https?://[^\s<>\"']+)", text)
    if m:
        return m.group(1).rstrip(".,;)")
    return ""


def extract_instagram(text):
    """Extract Instagram handle from text.

    Rejects handles that look like email domains (contain a dot followed by
    a known TLD suffix), which arise when scraped page text contains email
    addresses formatted as name@domain.com.
    """
    DOMAIN_TLDS = re.compile(
        r"\.(com|com\.au|net|net\.au|org|org\.au|gov|gov\.au|edu|edu\.au|au|id|io|co)$",
        re.IGNORECASE,
    )

    def _is_domain(handle):
        return bool(DOMAIN_TLDS.search(handle))

    # Prefer an explicit instagram.com URL — most reliable
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", text)
    if m:
        handle = m.group(1)
        if handle.lower() not in ("", "p", "explore", "accounts", "reel", "reels"):
            return f"@{handle}"

    # Fall back to @mention, but reject anything that looks like a domain
    m = re.search(r"@([A-Za-z0-9_.]+)", text)
    if m:
        handle = m.group(1)
        if len(handle) > 2 and not _is_domain(handle) and handle.lower() != "gmail":
            return f"@{handle}"

    return ""


# ---------------------------------------------------------------------------
# Master parser
# ---------------------------------------------------------------------------

def parse_result(raw):
    """Parse a raw fetch result into a structured exhibition record."""
    title = raw.get("title", "").strip()
    snippet = raw.get("snippet", "")
    url = raw.get("url", "")
    source = raw.get("source", "unknown")
    combined_text = f"{title} {snippet}"

    # Clean title: remove site suffixes
    title = re.sub(r"\s*[-|]\s*(TimeOut|Broadsheet|Art Almanac|Art Guide).*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*[-|]\s*Sydney\s*$", "", title, flags=re.IGNORECASE)
    title = title.strip().rstrip("|").strip()

    if not title:
        # Try to get title from snippet first line
        lines = snippet.split("\n")
        title = lines[0][:120] if lines else "Untitled"

    # Extract dates
    start_date, end_date = parse_date_range(combined_text)
    if not start_date:
        start_date = parse_date(combined_text)

    opening_date, opening_time = parse_opening_date(combined_text)

    # Extract location info
    venue = raw.get("venue_hint", "") or extract_venue(combined_text, title)
    suburb = raw.get("suburb_hint", "") or extract_suburb(combined_text)
    address = extract_address(combined_text)

    # Use date hints from Instagram OCR if available
    if raw.get("start_date_hint"):
        start_date = raw["start_date_hint"]
    if raw.get("end_date_hint"):
        end_date = raw["end_date_hint"]
    if raw.get("opening_date_hint"):
        opening_date = raw["opening_date_hint"]
    if raw.get("opening_time_hint"):
        opening_time = raw["opening_time_hint"]

    # Disambiguate generic titles by appending venue
    GENERIC_TITLES = {"group exhibition", "group exhibitions", "group show",
                      "solo exhibition", "solo show", "new works", "exhibition",
                      "winter survey", "summer survey", "mixed exhibition"}
    if title.lower() in GENERIC_TITLES and venue:
        title = f"{title} at {venue}"

    # Extract people and links
    artist = raw.get("artist_hint", "") or extract_artist(combined_text, title)
    website = extract_website(combined_text, url)
    instagram = extract_instagram(combined_text)

    # Build description from snippet, cleaned up
    description = snippet[:300].strip()
    description = re.sub(r"\s+", " ", description)

    record = {
        "title": title,
        "artist": artist,
        "venue": venue,
        "address": address,
        "suburb": suburb,
        "start_date": start_date,
        "end_date": end_date,
        "opening_date": opening_date,
        "opening_time": opening_time,
        "website": website,
        "instagram": instagram,
        "description": description,
        "source": source,
        "source_url": url,
        "status": "active",
        "first_seen": datetime.now(tz=timezone.utc).isoformat(),
    }

    return record


def is_exhibition(raw):
    """Quick filter: does this result look like an actual exhibition listing?"""
    text = f"{raw.get('title', '')} {raw.get('snippet', '')}".lower()
    title = raw.get("title", "").lower()

    # Positive signals
    pos_signals = [
        "exhibition", "exhibit", "opening", "gallery", "show",
        "solo show", "group show", "art show", "display",
        "on view", "on display", "now showing", "current exhibition",
        "upcoming exhibition", "new works", "presents",
        "painting", "sculpture", "photography", "installation",
        "portrait", "illustration", "printmaking", "ceramics",
        "mixed media", "watercolour", "watercolor", "oil on canvas",
        "contemporary art", "visual art", "fine art",
    ]
    has_positive = any(sig in text for sig in pos_signals)

    # Negative signals (job ads, real estate, non-art events, etc)
    neg_signals = [
        "job", "career", "hiring", "salary", "apply now",
        "for sale", "real estate", "property", "rent",
        "restaurant", "cafe", "hotel", "accommodation",
        "tripadvisor", "booking.com",
        "cat lovers", "dog lovers", "pet", "wedding expo",
        "food festival", "wine festival", "beer festival",
        "comedy", "stand-up", "standup", "trivia night",
        "yoga", "pilates", "wellness retreat", "meditation",
        "cooking class", "dance class", "fitness",
        "music festival", "concert", "live music", "dj set",
        "film festival", "movie screening", "cinema",
        "market day", "flea market", "farmers market",
        "tea expo", "trade show", "consumer expo", "visual impact expo",
        "conference", "summit", "hackathon",
        "workshop", "course", "masterclass", "class",
        "art class", "painting course", "drawing course",
        "watercolour course", "watercolor course",
        "oil painting course", "life drawing",
    ]
    has_negative = any(sig in text for sig in neg_signals)

    # Title-only negative: very short titles that are just gallery names
    # (Art Almanac scrapes gallery headings as separate entries)
    if len(title.split()) <= 5 and not any(sig in title for sig in [
        "exhibition", "show", "exhibit", "presents", "opening",
        "works", "paintings", "sculpture", "portrait",
    ]):
        # Check if it looks like just a venue/gallery name
        gallery_words = ["gallery", "museum", "centre", "center", "studio",
                         "space", "institute", "foundation", "art+"]
        if any(gw in title for gw in gallery_words):
            return False

    return has_positive and not has_negative


# Date floor: reject anything with dates before the current year.
# Recomputed at import time so it rolls over automatically each January.
DATE_FLOOR = str(datetime.now().year)


def is_current(record):
    """Check that extracted dates aren't stale (pre-current-year)."""
    for field in ["start_date", "end_date", "opening_date"]:
        d = record.get(field, "")
        if d and d < DATE_FLOOR:
            return False
    return True
