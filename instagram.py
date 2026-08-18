"""Instagram scraper for @sydneyartfinder using Meta Graph API (Business Discovery).

Uses the official Business Discovery endpoint to read sydneyartfinder's
public posts. Carousel images are downloaded and OCR'd with Tesseract
to extract the full weekly exhibition listings.

Required env vars:
    IG_USER_ID       - Your Instagram Business Account ID
    IG_ACCESS_TOKEN  - Long-lived Graph API access token (60 days)
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

IG_USER_ID = os.environ.get("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
TARGET_USERNAME = "sydneyartfinder"
GRAPH_API_VERSION = "v26.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
MONTH_PAT = "|".join(MONTHS.keys())

# Date patterns
RANGE_DIFF_RE = re.compile(
    rf"(\d{{1,2}})\s+({MONTH_PAT})\s*[–\-—]+\s*(\d{{1,2}})\s+({MONTH_PAT})",
    re.IGNORECASE,
)
RANGE_SAME_RE = re.compile(
    rf"(\d{{1,2}})\s*[–\-—]+\s*(\d{{1,2}})\s+({MONTH_PAT})",
    re.IGNORECASE,
)
OPENING_RE = re.compile(
    rf"Opening\s+\w+\s+(\d{{1,2}})\s+({MONTH_PAT})\s+([\d:]+\s*[–\-]\s*[\d:]+\s*[AP]M|[\d:]+\s*[AP]M)",
    re.IGNORECASE,
)
DAY_HEADER_RE = re.compile(
    rf"(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s*[–\-—]+\s*\d{{1,2}}\s+(?:{MONTH_PAT})",
    re.IGNORECASE,
)
SUBURB_RE = re.compile(r"^[A-Z][A-Z\s]{2,}$")


def make_date(day, month_str, year=None):
    m = MONTHS.get(month_str.lower().strip())
    if not m:
        return None
    if year is None:
        year = datetime.now(tz=timezone.utc).year
    try:
        return datetime(int(year), m, int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_ocr_text(text, post_url=""):
    """Parse OCR text from one slide into exhibition records."""
    results = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    current_year = datetime.now(tz=timezone.utc).year

    i = 0
    while i < len(lines):
        line = lines[i]

        if DAY_HEADER_RE.match(line):
            i += 1
            continue

        if len(line) < 3:
            i += 1
            continue

        if (i + 1 < len(lines)
            and not SUBURB_RE.match(line)
            and not RANGE_DIFF_RE.search(line)
            and not RANGE_SAME_RE.search(line)
            and not line.lower().startswith("opening")
            and not DAY_HEADER_RE.match(line)):

            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if SUBURB_RE.match(next_line):
                gallery = line.strip()
                suburb = next_line.strip().title()
                i += 2

                title = ""
                artist = ""
                start_date = None
                end_date = None
                opening_date = None
                opening_time = None

                while i < len(lines):
                    cl = lines[i]

                    if (i + 1 < len(lines) and SUBURB_RE.match(lines[i + 1])
                        and not RANGE_DIFF_RE.search(cl)
                        and not RANGE_SAME_RE.search(cl)
                        and not cl.lower().startswith("opening")):
                        break
                    if DAY_HEADER_RE.match(cl):
                        break

                    dm = RANGE_DIFF_RE.search(cl)
                    if dm:
                        start_date = make_date(dm.group(1), dm.group(2), current_year)
                        end_date = make_date(dm.group(3), dm.group(4), current_year)
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

                    om = OPENING_RE.search(cl)
                    if om:
                        opening_date = make_date(om.group(1), om.group(2), current_year)
                        opening_time = om.group(3).strip()
                        i += 1
                        continue

                    if cl.lower().startswith("opening") and not om:
                        od_match = re.search(rf"(\d{{1,2}})\s+({MONTH_PAT})", cl, re.IGNORECASE)
                        if od_match:
                            opening_date = make_date(od_match.group(1), od_match.group(2), current_year)
                        i += 1
                        continue

                    if not title:
                        title = cl.strip()
                        if ":" in title and not title.endswith(":"):
                            parts = title.split(":", 1)
                            if len(parts[0].split()) <= 4:
                                artist = parts[0].strip()
                        i += 1
                        continue

                    i += 1

                if gallery and (start_date or opening_date):
                    if not title:
                        title = gallery

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


def parse_caption(caption, post_url=""):
    """Parse the featured exhibition from a post caption."""
    lines = [l.strip() for l in caption.split("\n") if l.strip()]

    title = ""
    venue_line = ""
    artist = ""
    start_date = None
    end_date = None

    found_featured = False
    title_found = False
    dates_found = False

    for line in lines:
        lower = line.lower()
        if lower.startswith("#") or lower.startswith("image courtesy"):
            continue
        if lower.startswith("courtesy of") or lower.startswith("courtesy the"):
            continue

        if "featured" in lower and (":" in line or not title):
            found_featured = True
            after = re.sub(r"(?i).*featured:?\s*", "", line).strip()
            if after and len(after) > 3:
                title = after
                title_found = True
            continue

        if found_featured and not title_found:
            if len(re.sub(r"[^\w\s]", "", line).strip()) < 3:
                continue
            title = line
            title_found = True
            continue

        if title_found and not dates_found:
            sd, ed = None, None
            dm = RANGE_DIFF_RE.search(line)
            if dm:
                sd = make_date(dm.group(1), dm.group(2))
                ed = make_date(dm.group(3), dm.group(4))
            else:
                sm = RANGE_SAME_RE.search(line)
                if sm:
                    sd = make_date(sm.group(1), sm.group(3))
                    ed = make_date(sm.group(2), sm.group(3))
            if sd:
                start_date = sd
                end_date = ed
                dates_found = True
                continue

        if dates_found and not venue_line:
            if line.startswith("📸") or lower.startswith("artwork:"):
                break
            venue_line = line
            continue

        if dates_found and venue_line:
            break

    if not title:
        return None

    if ":" in title and not title.endswith(":"):
        parts = title.split(":", 1)
        if len(parts[0].split()) <= 4:
            artist = parts[0].strip()

    venue_name = re.sub(r"\s*@?\w+$", "", venue_line).strip() if venue_line else ""
    suburb = ""
    if "," in venue_name:
        parts = venue_name.rsplit(",", 1)
        venue_name = parts[0].strip()
        suburb = parts[1].strip()

    if not start_date:
        return None

    return {
        "source": "instagram",
        "url": post_url,
        "title": title,
        "snippet": "",
        "domain": "instagram.com",
        "venue_hint": venue_name,
        "suburb_hint": suburb,
        "start_date_hint": start_date,
        "end_date_hint": end_date,
        "artist_hint": artist,
    }


def ocr_image(url):
    """Download an image and run OCR."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"[instagram] OCR error: {e}")
        return ""


def check_token_expiry():
    """Check how many days remain on the Instagram access token and warn if under 14.

    Uses the Graph API token debug endpoint. Sends a Discord webhook warning
    if the token expires within 14 days so there's time to refresh it before
    the pipeline breaks.
    """
    if not IG_ACCESS_TOKEN:
        return

    try:
        resp = requests.get(
            f"https://graph.facebook.com/debug_token",
            params={"input_token": IG_ACCESS_TOKEN, "access_token": IG_ACCESS_TOKEN},
            timeout=15,
        )
        if resp.status_code != 200:
            return

        data = resp.json().get("data", {})
        expires_at = data.get("data_access_expires_at") or data.get("expires_at")
        if not expires_at:
            return

        expiry = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        days_left = (expiry - datetime.now(tz=timezone.utc)).days

        if days_left <= 14:
            msg = (
                f":warning: **Instagram token expires in {days_left} day{'s' if days_left != 1 else ''}** "
                f"({expiry.strftime('%d %b %Y')}). "
                f"Refresh at https://developers.facebook.com/tools/explorer/"
            )
            print(f"[instagram] TOKEN WARNING: {days_left} days remaining")

            webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")
            if webhook:
                try:
                    requests.post(webhook, json={"content": msg}, timeout=10)
                except Exception:
                    pass
        else:
            print(f"[instagram] Token valid for {days_left} days")

    except Exception as e:
        print(f"[instagram] Token expiry check failed: {e}")


def fetch_instagram():
    """Fetch posts via Business Discovery API, OCR carousel slides.

    Only processes posts newer than the last processed timestamp,
    stored in seen.json under __meta__.instagram_latest.
    On first run (no marker), processes all posts.
    """
    check_token_expiry()
    results = []

    if not IG_USER_ID or not IG_ACCESS_TOKEN:
        print("[instagram] No IG_USER_ID or IG_ACCESS_TOKEN set, skipping")
        return results

    # Load last processed timestamp from state
    from state import load_state, save_state
    state = load_state()
    last_processed = state.get("__meta__", {}).get("instagram_latest", "")
    is_first_run = not last_processed

    try:
        # Fetch posts with pagination
        all_posts = []
        fields = f"business_discovery.username({TARGET_USERNAME}){{media.limit(10){{caption,permalink,timestamp,media_type,children{{media_url,media_type}}}}}}"
        url = f"{GRAPH_BASE}/{IG_USER_ID}?fields={fields}&access_token={IG_ACCESS_TOKEN}"

        # First run: get everything (8 pages). Subsequent: just 2 pages (20 posts)
        MAX_PAGES = 8 if is_first_run else 2
        stop_early = False

        for page in range(MAX_PAGES):
            resp = requests.get(url, timeout=30)

            if resp.status_code == 190 or "Invalid OAuth" in resp.text:
                print("[instagram] Access token expired. Generate a new long-lived token.")
                return results

            if resp.status_code != 200:
                print(f"[instagram] API error: {resp.status_code} {resp.text[:200]}")
                return results

            data = resp.json()
            media = data.get("business_discovery", {}).get("media", {})
            posts = media.get("data", [])

            for post in posts:
                ts = post.get("timestamp", "")
                # Skip posts we've already processed
                if last_processed and ts <= last_processed:
                    stop_early = True
                    break
                all_posts.append(post)

            if stop_early:
                break

            # Check for next page
            paging = media.get("paging", {})
            next_cursor = paging.get("cursors", {}).get("after", "")
            if not next_cursor:
                break

            fields_paged = f"business_discovery.username({TARGET_USERNAME}){{media.limit(10).after({next_cursor}){{caption,permalink,timestamp,media_type,children{{media_url,media_type}}}}}}"
            url = f"{GRAPH_BASE}/{IG_USER_ID}?fields={fields_paged}&access_token={IG_ACCESS_TOKEN}"

            if page > 0:
                time.sleep(1)

        if not all_posts:
            print("[instagram] No new posts since last run")
            return results

        print(f"[instagram] {len(all_posts)} new posts to process, running OCR...")

        # Process each post
        total_slides = 0
        caption_results = 0
        newest_timestamp = last_processed

        for post in all_posts:
            permalink = post.get("permalink", "")
            caption = post.get("caption", "")
            media_type = post.get("media_type", "")
            children = post.get("children", {}).get("data", [])
            ts = post.get("timestamp", "")

            # Track newest timestamp
            if ts > newest_timestamp:
                newest_timestamp = ts

            # Parse caption for the featured exhibition
            if caption:
                cap_record = parse_caption(caption, permalink)
                if cap_record:
                    results.append(cap_record)
                    caption_results += 1

            # OCR carousel slides (skip first = cover image)
            if media_type == "CAROUSEL_ALBUM" and len(children) > 1:
                for child in children[1:]:
                    if child.get("media_type") != "IMAGE":
                        continue
                    img_url = child.get("media_url", "")
                    if not img_url:
                        continue

                    text = ocr_image(img_url)
                    if not text or len(text) < 20:
                        continue

                    total_slides += 1
                    exhibitions = parse_ocr_text(text, permalink)
                    results.extend(exhibitions)

        # Save newest timestamp for next run
        if newest_timestamp and newest_timestamp > last_processed:
            state["__meta__"]["instagram_latest"] = newest_timestamp
            save_state(state)

        print(f"[instagram] Parsed {caption_results} captions, OCR'd {total_slides} slides, extracted {len(results)} total exhibitions")

    except Exception as e:
        print(f"[instagram] Error: {e}")

    return results
