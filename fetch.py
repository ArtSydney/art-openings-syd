"""Fetch exhibition data from multiple sources."""

import json
import os
import re
import time
import warnings
import requests
import urllib3
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Suppress SSL warning for art-almanac (their cert is misconfigured)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
HEADERS = {"User-Agent": USER_AGENT}

# ---------------------------------------------------------------------------
# Serper Google Search
# ---------------------------------------------------------------------------

SERPER_QUERIES = [
    "sydney art exhibition opening this week",
    "sydney gallery exhibition opening 2026",
    "art exhibition opening night sydney",
    "new exhibition sydney gallery",
    "sydney contemporary art show opening",
    "art gallery exhibition Sydney NSW",
    "gallery opening reception Sydney",
    "artist run initiative sydney exhibition",
    "Surry Hills Chippendale gallery exhibition",
    "Paddington Woollahra gallery exhibition opening",
    "Marrickville Redfern gallery exhibition",
    "Sydney artist run space exhibition 2026",
]

# Domains that return listicles or aggregator noise rather than exhibition pages
EXCLUDED_DOMAINS = [
    "pinterest.com", "facebook.com", "twitter.com", "x.com",
    "youtube.com", "reddit.com", "tiktok.com",
]


def fetch_serper():
    """Run Serper queries and return raw results."""
    if not SERPER_API_KEY:
        print("[serper] No API key, skipping")
        return []

    all_results = []
    seen_urls = set()

    for query in SERPER_QUERIES:
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "gl": "au", "location": "Sydney, New South Wales", "num": 10},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("organic", []):
                url = item.get("link", "")
                domain = re.sub(r"^www\.", "", item.get("domain", ""))
                if domain in EXCLUDED_DOMAINS:
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                all_results.append({
                    "source": "serper",
                    "url": url,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "domain": domain,
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"[serper] Error on query '{query}': {e}")

    print(f"[serper] Fetched {len(all_results)} results")
    return all_results


# ---------------------------------------------------------------------------
# Art Almanac
# ---------------------------------------------------------------------------

def fetch_art_almanac():
    """Scrape Art Almanac Sydney exhibition listings.

    The page structure is: bold gallery name heading, then address/hours,
    then exhibition lines with date patterns like 'To Aug 16' or
    'Aug 6 to Sept 5'. Exhibition titles are often in <em>/<i> tags.
    We split the page by gallery blocks and extract exhibitions from each.
    """
    url = "https://www.art-almanac.com.au/whats-on/sydney/"
    results = []
    # Date signal patterns in Art Almanac format
    date_signals = re.compile(
        r"(?:To |From |Until )"
        r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}"
        r"|(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))",
        re.IGNORECASE,
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all bold/strong elements that are gallery names (they contain <a> links)
        gallery_headings = []
        for strong in soup.find_all("strong"):
            link = strong.find("a")
            if link and link.get("href"):
                name = strong.get_text(strip=True)
                if len(name) > 2:
                    gallery_headings.append({
                        "name": name,
                        "url": link["href"],
                        "element": strong,
                    })

        # For each gallery, collect text until the next gallery heading
        for i, gallery in enumerate(gallery_headings):
            gallery_name = gallery["name"]
            gallery_url = gallery["url"]
            if not gallery_url.startswith("http"):
                gallery_url = "https://www.art-almanac.com.au" + gallery_url

            # Collect all sibling/following text until next gallery heading
            el = gallery["element"]
            block_parts = []
            current = el.parent if el.parent else el
            for sib in current.next_siblings:
                # Check if this is a Tag (not NavigableString) that contains a gallery link
                if hasattr(sib, "name") and sib.name is not None:
                    inner_strong = sib.find("strong") if hasattr(sib, "find_all") else None
                    if inner_strong and hasattr(inner_strong, "find_all") and inner_strong.find("a"):
                        break
                text = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                if text:
                    block_parts.append(text)

            block_text = " ".join(block_parts)

            # Only process blocks that have date signals (= actual exhibition info)
            if not date_signals.search(block_text):
                continue

            # Split block into individual exhibition entries by date pattern
            # Each exhibition typically starts with a date like "To Aug 16" or "Aug 6 to Sept 5"
            lines = re.split(r"\n+", block_text)
            # Recombine into one text for simpler processing
            full_text = " ".join(lines)

            results.append({
                "source": "art_almanac",
                "url": gallery_url,
                "title": gallery_name,
                "snippet": full_text[:800],
                "domain": "art-almanac.com.au",
                "venue_hint": gallery_name,
            })

    except Exception as e:
        print(f"[art_almanac] Error: {e}")

    print(f"[art_almanac] Fetched {len(results)} results")
    return results


# ---------------------------------------------------------------------------
# Art Guide Australia
# ---------------------------------------------------------------------------

def fetch_city_of_sydney():
    """Scrape City of Sydney What's On exhibitions."""
    url = "https://whatson.cityofsydney.nsw.gov.au/categories/exhibitions"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for card in soup.select("article, .card, .event-card, .listing, .search-result, [class*='event']"):
            title_el = card.select_one("h2, h3, h4, .title, .card-title, .event-title")
            link_el = card.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://whatson.cityofsydney.nsw.gov.au" + link

            text = card.get_text(" ", strip=True)

            # Extract venue: City of Sydney cards follow the pattern
            # "Title VenueName Category Title Description..."
            # The venue appears between the title and a category keyword
            venue_hint = ""
            CATEGORIES = ["exhibitions", "community", "arts", "events",
                          "causes", "festivals", "markets", "sport"]
            stripped = text
            if title and stripped.startswith(title):
                stripped = stripped[len(title):].strip()
            # What's left starts with the venue name, ends at a category word
            import re as _re
            cat_pattern = "|".join(CATEGORIES)
            m = _re.match(rf"^(.+?)\s+(?:{cat_pattern})\b", stripped, _re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                # Reject if it's just a suburb or very short
                if len(candidate) > 5 and not candidate.lower() in [
                    "sydney", "darlinghurst", "surry hills", "newtown",
                    "paddington", "waterloo", "redfern", "woollahra"
                ]:
                    venue_hint = candidate

            results.append({
                "source": "city_of_sydney",
                "url": link,
                "title": title,
                "snippet": text[:500],
                "domain": "whatson.cityofsydney.nsw.gov.au",
                "venue_hint": venue_hint,
            })
    except Exception as e:
        print(f"[city_of_sydney] Error: {e}")

    print(f"[city_of_sydney] Fetched {len(results)} results")
    return results


# ---------------------------------------------------------------------------
# TimeOut Sydney
# ---------------------------------------------------------------------------

def fetch_timeout():
    """Scrape TimeOut Sydney art section."""
    url = "https://www.timeout.com/sydney/art"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for card in soup.select("article, .card, .listing-item, .tile, [class*='card'], [class*='article']"):
            title_el = card.select_one("h2, h3, .title, .card-title, [class*='title']")
            link_el = card.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.timeout.com" + link

            text = card.get_text(" ", strip=True)
            results.append({
                "source": "timeout",
                "url": link,
                "title": title,
                "snippet": text[:500],
                "domain": "timeout.com",
            })
    except Exception as e:
        print(f"[timeout] Error: {e}")

    print(f"[timeout] Fetched {len(results)} results")
    return results


# ---------------------------------------------------------------------------
# Broadsheet Sydney
# ---------------------------------------------------------------------------

def fetch_broadsheet():
    """Scrape Broadsheet Sydney art & design section."""
    url = "https://www.broadsheet.com.au/sydney/art-and-design"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for card in soup.select("article, .card, .listing-item, .tile, .content-card, [class*='card'], [class*='article']"):
            title_el = card.select_one("h2, h3, .title, .card-title, .heading, [class*='title']")
            link_el = card.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.broadsheet.com.au" + link

            text = card.get_text(" ", strip=True)
            results.append({
                "source": "broadsheet",
                "url": link,
                "title": title,
                "snippet": text[:500],
                "domain": "broadsheet.com.au",
            })
    except Exception as e:
        print(f"[broadsheet] Error: {e}")

    print(f"[broadsheet] Fetched {len(results)} results")
    return results


# ---------------------------------------------------------------------------
# Ocula - Sydney Galleries
# ---------------------------------------------------------------------------

def fetch_ocula():
    """Scrape Ocula Sydney gallery exhibitions."""
    url = "https://ocula.com/cities/australia/sydney-art-galleries/exhibitions/"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for card in soup.select("article, .card, [class*='exhibition'], [class*='listing']"):
            title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
            link_el = card.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://ocula.com" + link

            text = card.get_text(" ", strip=True)
            results.append({
                "source": "ocula",
                "url": link,
                "title": title,
                "snippet": text[:500],
                "domain": "ocula.com",
            })
    except Exception as e:
        print(f"[ocula] Error: {e}")

    print(f"[ocula] Fetched {len(results)} results")
    return results


# ---------------------------------------------------------------------------
# Scrape individual exhibition page for details
# ---------------------------------------------------------------------------

def scrape_exhibition_page(url):
    """Fetch an exhibition URL and return raw text for parsing."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove nav, footer, scripts, etc
        for tag in soup.select("nav, footer, script, style, header, .nav, .footer, .sidebar"):
            tag.decompose()

        text = soup.get_text(" ", strip=True)
        # Truncate to avoid huge pages
        return text[:3000]
    except Exception as e:
        print(f"[scrape] Error fetching {url}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Master fetch
# ---------------------------------------------------------------------------

def fetch_all():
    """Run all fetch sources and return combined raw results."""
    results = []
    results.extend(fetch_serper())
    results.extend(fetch_art_almanac())
    results.extend(fetch_city_of_sydney())
    results.extend(fetch_timeout())
    results.extend(fetch_broadsheet())
    # Ocula removed: returns 403
    print(f"[fetch] Total raw results: {len(results)}")
    return results
