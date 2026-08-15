"""Instagram scraper for @sydneyartfinder using REST API + OCR.

Each post is a carousel. Slide 1 is the cover image (skip).
Slides 2+ contain structured exhibition listings:

    THURSDAY - 13 AUGUST

    Arthouse
    DARLINGHURST
    Belinda Fox: Abundance
    13 August – 8 September
    Opening Thu 13 August 5:30-7:30 PM

We OCR each slide and parse the text into exhibition records.
"""

import io
import json
import os
import re
import time
import requests
from datetime import datetime, timezone
from PIL import Image
import pytesseract

INSTAGRAM_SESSION_ID = os.environ.get("INSTAGRAM_SESSION_ID", "")
TARGET_ACCOUNT = "sydneyartfinder"

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
MONTH_PAT = "|".join(MONTHS.keys())

# Date range: "13 August – 8 September" or "13 August - 8 September"
RANGE_DIFF_RE = re.compile(
    rf"(\d{{1,2}})\s+({MONTH_PAT})\s*[–\-—]+\s*(\d{{1,2}})\s+({MONTH_PAT})",
    re.IGNORECASE,
)
# Same month range: "6–22 August"
RANGE_SAME_RE = re.compile(
    rf"(\d{{1,2}})\s*[–\-—]+\s*(\d{{1,2}})\s+({MONTH_PAT})",
    re.IGNORECASE,
)
# Opening line: "Opening Thu 13 August 5:30-7:30 PM"
OPENING_RE = re.compile(
    rf"Opening\s+\w+\s+(\d{{1,2}})\s+({MONTH_PAT})\s+([\d:]+\s*[–\-]\s*[\d:]+\s*[AP]M|[\d:]+\s*[AP]M)",
    re.IGNORECASE,
)
# Day header: "THURSDAY - 13 AUGUST"
DAY_HEADER_RE = re.compile(
    rf"(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s*[–\-—]+\s*\d{{1,2}}\s+(?:{MONTH_PAT})",
    re.IGNORECASE,
)
# All-caps line = suburb
SUBURB_RE = re.compile(r"^[A-Z][A-Z\s]{2,}$")


def make_date(day, month_str, year=None):
    """Convert day/month to YYYY-MM-DD. Infer year from current date."""
    m = MONTHS.get(month_str.lower().strip())
    if not m:
        return None
    if year is None:
        now = datetime.now(tz=timezone.utc)
        year = now.year
        # If month is in the past, could still be this year
    try:
        return datetime(int(year), m, int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_ocr_text(text, post_url=""):
    """Parse OCR text from one slide into exhibition records.

    Format per exhibition block:
        Gallery Name
        SUBURB
        Artist: Title (or just Title)
        13 August – 8 September
        Opening Thu 13 August 5:30-7:30 PM (optional)
    """
    results = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Current year for date inference
    current_year = datetime.now(tz=timezone.utc).year

    # State machine to parse exhibition blocks
    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip day headers like "THURSDAY - 13 AUGUST"
        if DAY_HEADER_RE.match(line):
            i += 1
            continue

        # Skip very short or noisy lines
        if len(line) < 3:
            i += 1
            continue

        # Detect start of exhibition block:
        # Gallery name is typically a non-caps, non-date line
        # followed by a SUBURB line in all caps
        if (i + 1 < len(lines)
            and not SUBURB_RE.match(line)
            and not RANGE_DIFF_RE.search(line)
            and not RANGE_SAME_RE.search(line)
            and not line.lower().startswith("opening")
            and not DAY_HEADER_RE.match(line)):

            # Check if next line is a suburb (ALL CAPS)
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if SUBURB_RE.match(next_line):
                gallery = line.strip()
                suburb = next_line.strip().title()  # Convert "DARLINGHURST" to "Darlinghurst"
                i += 2

                # Next lines: title/artist, dates, opening
                title = ""
                artist = ""
                start_date = None
                end_date = None
                opening_date = None
                opening_time = None

                # Collect remaining lines of this block
                while i < len(lines):
                    cl = lines[i]

                    # Hit next gallery block or day header = stop
                    if (i + 1 < len(lines) and SUBURB_RE.match(lines[i + 1])
                        and not RANGE_DIFF_RE.search(cl)
                        and not RANGE_SAME_RE.search(cl)
                        and not cl.lower().startswith("opening")):
                        break
                    if DAY_HEADER_RE.match(cl):
                        break

                    # Date range
                    dm = RANGE_DIFF_RE.search(cl)
                    if dm:
                        start_date = make_date(dm.group(1), dm.group(2), current_year)
                        end_date = make_date(dm.group(3), dm.group(4), current_year)
                        # Handle year rollover (start in Nov, end in Feb)
                        if end_date and start_date and end_date < start_date:
                            end_date = make_date(dm.group(3), dm.group(4), current_year + 1)
                        i += 1
                        continue

                    sm = RANGE_SAME_RE.search(cl)
                    if sm:
                        start_date = make_date(sm.group(1), sm.group(3), current_year)
                        end_date = make_date(sm.group(2), sm.group(3), current_year)
                        i += 1
                        continue

                    # Opening line
                    om = OPENING_RE.search(cl)
                    if om:
                        opening_date = make_date(om.group(1), om.group(2), current_year)
                        opening_time = om.group(3).strip()
                        i += 1
                        continue

                    # Check for "Opening [date]" without time
                    if cl.lower().startswith("opening") and not om:
                        # Try to extract just a date
                        od_match = re.search(rf"(\d{{1,2}})\s+({MONTH_PAT})", cl, re.IGNORECASE)
                        if od_match:
                            opening_date = make_date(od_match.group(1), od_match.group(2), current_year)
                        i += 1
                        continue

                    # Title/artist line (anything else before dates)
                    if not title:
                        title = cl.strip()
                        # Parse "Artist: Title" or "Artist | Title"
                        if ":" in title and not title.endswith(":"):
                            parts = title.split(":", 1)
                            if len(parts[0].split()) <= 4:
                                artist = parts[0].strip()
                        elif "|" in title:
                            parts = title.split("|")
                            # Could be "Artist | Title" or "Artist1 | Artist2: Title1 | Title2"
                            # Keep full title for display
                        i += 1
                        continue

                    i += 1

                # Must have at least gallery and some date
                if gallery and (start_date or opening_date):
                    if not title:
                        title = gallery  # fallback

                    results.append({
                        "source": "instagram",
                        "url": post_url,
                        "title": title,
                        "snippet": "",
                        "domain": "instagram.com",
                        "venue_hint": gallery,
                        "suburb_hint": suburb,
                        "start_date_hint": start_date,
                        "end_date_hint": end_date,
                        "opening_date_hint": opening_date,
                        "opening_time_hint": opening_time,
                        "artist_hint": artist,
                    })
                continue

        i += 1

    return results


def ocr_image(url):
    """Download an image and run OCR on it."""
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"[instagram] OCR error: {e}")
        return ""


def fetch_instagram():
    """Fetch posts from @sydneyartfinder, OCR carousel slides, extract exhibitions."""
    results = []

    if not INSTAGRAM_SESSION_ID:
        print("[instagram] No INSTAGRAM_SESSION_ID set, skipping")
        return results

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Cookie": f"sessionid={INSTAGRAM_SESSION_ID}",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Referer": f"https://www.instagram.com/{TARGET_ACCOUNT}/",
    }

    try:
        # Get profile info (also contains first 12 posts)
        profile_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={TARGET_ACCOUNT}"
        resp = requests.get(profile_url, headers=headers, timeout=20)
        resp.raise_for_status()
        profile_data = resp.json()
        user = profile_data["data"]["user"]
        user_id = user["id"]

        # Try paginated feed endpoint first
        all_items = []
        max_id = ""
        MAX_PAGES = 4
        feed_worked = False

        for page in range(MAX_PAGES):
            if page > 0:
                time.sleep(1.5)

            url = f"https://www.instagram.com/api/v1/feed/user/{user_id}/?count=50"
            if max_id:
                url += f"&max_id={max_id}"

            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code != 200:
                print(f"[instagram] Feed page {page + 1}: HTTP {r.status_code}, stopping pagination")
                break

            feed_worked = True
            data = r.json()
            items = data.get("items", [])
            all_items.extend(items)

            if not data.get("more_available", False):
                break
            max_id = data.get("next_max_id", "")
            if not max_id:
                break

        # Fallback: use the 12 posts from profile API if feed failed
        if not feed_worked:
            print("[instagram] Feed API unavailable, falling back to profile API (12 posts)")
            edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                # Convert GraphQL format to feed format for unified processing
                sidecar = node.get("edge_sidecar_to_children", {}).get("edges", [])
                carousel = []
                for s in sidecar:
                    snode = s.get("node", {})
                    carousel.append({
                        "image_versions2": {
                            "candidates": [{"url": snode.get("display_url", "")}]
                        }
                    })
                all_items.append({
                    "code": node.get("shortcode", ""),
                    "carousel_media": carousel,
                })

        print(f"[instagram] Fetched {len(all_items)} posts, running OCR...")

        # Process each post
        total_slides = 0
        for item in all_items:
            shortcode = item.get("code", "")
            post_url = f"https://www.instagram.com/p/{shortcode}/" if shortcode else ""

            # Get carousel slides
            carousel = item.get("carousel_media", [])
            if not carousel:
                # Single image post, skip (cover only)
                continue

            # Skip slide 0 (cover image), OCR slides 1+
            for slide in carousel[1:]:
                img_candidates = slide.get("image_versions2", {}).get("candidates", [])
                if not img_candidates:
                    continue

                # Use largest image
                img_url = img_candidates[0].get("url", "")
                if not img_url:
                    continue

                text = ocr_image(img_url)
                if not text:
                    continue

                total_slides += 1
                exhibitions = parse_ocr_text(text, post_url)
                results.extend(exhibitions)

        print(f"[instagram] OCR'd {total_slides} slides, extracted {len(results)} exhibitions")

    except Exception as e:
        print(f"[instagram] Error: {e}")

    return results
