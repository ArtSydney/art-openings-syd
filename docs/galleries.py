"""Gallery database management for art-openings-syd.

Maintains a persistent database of Sydney galleries with location, contact,
and visiting info. Seeded from a curated list, enriched from exhibition data,
and geocoded via Nominatim (free, no API key).

Data model per gallery:
    name            - Gallery name
    type            - commercial | ari | museum | university | project_space
    address         - Full street address
    suburb          - Sydney suburb
    postcode        - Postcode
    latitude        - Decimal degrees (from geocoding)
    longitude       - Decimal degrees (from geocoding)
    website         - Gallery website URL
    instagram       - Instagram handle (@handle)
    email           - Contact email
    phone           - Contact phone
    hours           - Opening hours text (best effort)
    entry           - free | paid | donation | unknown
    accessibility   - Wheelchair access notes
    source          - Where this gallery was first found
    last_verified   - ISO date of last update
"""

import json
import os
import re
import time
import requests
from datetime import datetime, timezone

GALLERIES_FILE = "galleries.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "art-openings-syd/1.0 (github.com/SurlyKM/art-openings-syd)"


# ---------------------------------------------------------------------------
# Curated seed list of known Sydney galleries
# ---------------------------------------------------------------------------

SEED_GALLERIES = [
    # Major institutions
    {"name": "Art Gallery of New South Wales", "type": "museum", "suburb": "Sydney",
     "address": "Art Gallery Rd, The Domain", "website": "https://www.artgallery.nsw.gov.au",
     "instagram": "@artgalleryofnsw", "entry": "free"},
    {"name": "Museum of Contemporary Art Australia", "type": "museum", "suburb": "The Rocks",
     "address": "140 George St", "website": "https://www.mca.com.au",
     "instagram": "@mca_australia", "entry": "free"},
    {"name": "White Rabbit Gallery", "type": "museum", "suburb": "Chippendale",
     "address": "30 Balfour St", "website": "https://www.whiterabbitcollection.org",
     "instagram": "@whiterabbitgallery", "entry": "free"},
    {"name": "Artspace", "type": "museum", "suburb": "Woolloomooloo",
     "address": "43-51 Cowper Wharf Roadway", "website": "https://www.artspace.org.au",
     "instagram": "@artspace_visualarts", "entry": "free"},
    {"name": "Carriageworks", "type": "museum", "suburb": "Eveleigh",
     "address": "245 Wilson St", "website": "https://www.carriageworks.com.au",
     "instagram": "@carriageworks", "entry": "free"},
    {"name": "National Art School Gallery", "type": "university", "suburb": "Darlinghurst",
     "address": "156 Forbes St", "website": "https://www.nas.edu.au",
     "instagram": "@nationalartschool", "entry": "free"},
    {"name": "UNSW Galleries", "type": "university", "suburb": "Paddington",
     "address": "Cnr Oxford St & Greens Rd", "website": "https://www.unsw.edu.au/unsw-galleries",
     "instagram": "@unswgalleries", "entry": "free"},
    {"name": "UTS Gallery", "type": "university", "suburb": "Ultimo",
     "address": "702 Harris St", "website": "https://www.uts.edu.au/uts-art",
     "instagram": "@utsart", "entry": "free"},
    {"name": "Chau Chak Wing Museum", "type": "university", "suburb": "Camperdown",
     "address": "University of Sydney", "website": "https://www.sydney.edu.au/museum",
     "instagram": "@chauchakwingmuseum", "entry": "free"},
    {"name": "S.H. Ervin Gallery", "type": "museum", "suburb": "Millers Point",
     "address": "Watson Rd, Observatory Hill", "website": "https://www.shervingallery.com.au",
     "instagram": "@shervingallery", "entry": "paid"},

    # Commercial galleries
    {"name": "Roslyn Oxley9 Gallery", "type": "commercial", "suburb": "Paddington",
     "address": "8 Soudan Ln", "website": "https://www.roslynoxley9.com.au",
     "instagram": "@roslynoxley9gallery", "entry": "free"},
    {"name": "Sullivan+Strumpf", "type": "commercial", "suburb": "Zetland",
     "address": "799 Elizabeth St", "website": "https://sullivanstrumpf.com",
     "instagram": "@sullivanstrumpf", "entry": "free"},
    {"name": "Martin Browne Contemporary", "type": "commercial", "suburb": "Paddington",
     "address": "15 Hampden St", "website": "https://www.martinbrownecontemporary.com",
     "instagram": "@martinbrownecontemporary", "entry": "free"},
    {"name": "Olsen Gallery", "type": "commercial", "suburb": "Woollahra",
     "address": "63 Jersey Rd", "website": "https://www.olsengallery.com",
     "instagram": "@olsengallery", "entry": "free"},
    {"name": "Sarah Cottier Gallery", "type": "commercial", "suburb": "Alexandria",
     "address": "6 MacDonald St", "website": "https://www.sarahcottiergallery.com",
     "instagram": "@sarahcottiergallery", "entry": "free"},
    {"name": "Darren Knight Gallery", "type": "commercial", "suburb": "Redfern",
     "address": "840 Elizabeth St", "website": "https://www.darrenknightgallery.com",
     "instagram": "@darrenknightgallery", "entry": "free"},
    {"name": "Michael Reid Sydney", "type": "commercial", "suburb": "Chippendale",
     "address": "44 Roylston St", "website": "https://www.michaelreid.com.au",
     "instagram": "@michaelreidgalleries", "entry": "free"},
    {"name": "Sarah Cottier Gallery", "type": "commercial", "suburb": "Alexandria",
     "address": "6 MacDonald St", "website": "https://www.sarahcottiergallery.com",
     "instagram": "@sarahcottiergallery", "entry": "free"},
    {"name": "King Street Gallery on William", "type": "commercial", "suburb": "Darlinghurst",
     "address": "177 William St", "website": "https://www.kingstreetgallery.com.au",
     "instagram": "@kingstreetgallery", "entry": "free"},
    {"name": "Dominik Mersch Gallery", "type": "commercial", "suburb": "Rushcutters Bay",
     "address": "2 Danks St", "website": "https://www.dmgart.com.au",
     "instagram": "@dominikmerschgallery", "entry": "free"},
    {"name": "Nanda\\Hobbs", "type": "commercial", "suburb": "Chippendale",
     "address": "12-14 Meagher St", "website": "https://www.nandahobbs.com",
     "instagram": "@nandahobbs", "entry": "free"},
    {"name": "China Heights Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "16-28 Foster St", "website": "https://chinaheights.com",
     "instagram": "@chinaheights", "entry": "free"},
    {"name": "Ames Yavuz", "type": "commercial", "suburb": "Surry Hills",
     "address": "56-64 Foster St", "website": "https://www.amesyavuz.com",
     "instagram": "@amesyavuz", "entry": "free"},
    {"name": "Curatorial+Co.", "type": "commercial", "suburb": "Woolloomooloo",
     "address": "12/85 McLachlan Ave", "website": "https://www.curatorialandco.com",
     "instagram": "@curatorialandco", "entry": "free"},
    {"name": "Piermarq", "type": "commercial", "suburb": "Woollahra",
     "address": "148 Queen St", "website": "https://www.piermarq.com",
     "instagram": "@piermarq", "entry": "free"},
    {"name": "The Commercial Gallery", "type": "commercial", "suburb": "Marrickville",
     "address": "2/4 Wells St", "website": "https://thecommercialgallery.com",
     "instagram": "@thecommercialgallery", "entry": "free"},
    {"name": "STATION Sydney", "type": "commercial", "suburb": "Alexandria",
     "address": "7 Short St", "website": "https://stationgallery.com",
     "instagram": "@station_gallery", "entry": "free"},
    {"name": "Yavuz Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "56-64 Foster St", "website": "https://www.yavuzgallery.com",
     "instagram": "@yavuzgallery", "entry": "free"},
    {"name": "Schmick Contemporary", "type": "commercial", "suburb": "Haymarket",
     "address": "Level 1/2-16 Quay St", "website": "",
     "instagram": "@schmickcontemporary", "entry": "free"},
    {"name": "N.Smith Gallery", "type": "commercial", "suburb": "Darlinghurst",
     "address": "68 Riley St", "website": "https://www.nsmithgallery.com",
     "instagram": "@nsmithgallery", "entry": "free"},

    # Artist-run initiatives & project spaces
    {"name": "Firstdraft", "type": "ari", "suburb": "Woolloomooloo",
     "address": "13-17 Riley St", "website": "https://firstdraft.org.au",
     "instagram": "@firstdraftgallery", "entry": "free"},
    {"name": "Verge Gallery", "type": "university", "suburb": "Camperdown",
     "address": "Jane Foss Russell Building, City Rd", "website": "https://www.vergegallery.net",
     "instagram": "@vergegallery", "entry": "free"},
    {"name": "4A Centre for Contemporary Asian Art", "type": "museum", "suburb": "Haymarket",
     "address": "181-187 Hay St", "website": "https://www.4a.com.au",
     "instagram": "@4a_aus", "entry": "free"},
    {"name": "Cement Fondu", "type": "project_space", "suburb": "Paddington",
     "address": "36 Gosbell St", "website": "https://cementfondu.org",
     "instagram": "@cementfondu", "entry": "free"},
    {"name": "Airspace Projects", "type": "ari", "suburb": "Marrickville",
     "address": "10 Junction St", "website": "https://www.airspaceprojects.com",
     "instagram": "@airspaceprojects", "entry": "free"},
    {"name": "Articulate Project Space", "type": "ari", "suburb": "Leichhardt",
     "address": "497 Parramatta Rd", "website": "https://articulate497.blogspot.com",
     "instagram": "@articulateprojectspace", "entry": "free"},
    {"name": "Cross Art Projects", "type": "project_space", "suburb": "Kings Cross",
     "address": "8 Llankelly Pl", "website": "https://www.crossart.com.au",
     "instagram": "@thecrossartprojects", "entry": "free"},
    {"name": "Gaffa Gallery", "type": "commercial", "suburb": "Sydney",
     "address": "281 Clarence St", "website": "https://gaffa.com.au",
     "instagram": "@gaffagallery", "entry": "free"},
    {"name": "Tin Sheds Gallery", "type": "university", "suburb": "Darlington",
     "address": "148 City Rd", "website": "https://www.sydney.edu.au/architecture",
     "instagram": "@tinshedsgallery", "entry": "free"},
    {"name": "Woollahra Gallery at Redleaf", "type": "commercial", "suburb": "Double Bay",
     "address": "548 New South Head Rd", "website": "https://www.woollahra.nsw.gov.au",
     "instagram": "@woollahragallery", "entry": "free"},
    {"name": "M2 Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "Shop 4/450 Elizabeth St", "website": "https://m2gallery.com.au",
     "instagram": "@m2gallery", "entry": "free"},
    {"name": "Tap Gallery", "type": "ari", "suburb": "Darlinghurst",
     "address": "259 Riley St", "website": "https://tapgallery.org.au",
     "instagram": "@tapgallerysydney", "entry": "paid"},
]


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def load_galleries():
    """Load galleries.json, return dict keyed by normalized name."""
    if os.path.exists(GALLERIES_FILE):
        with open(GALLERIES_FILE, "r") as f:
            return json.load(f)
    return {}


def save_galleries(galleries):
    """Save galleries.json."""
    with open(GALLERIES_FILE, "w") as f:
        json.dump(galleries, f, indent=2, default=str)


def normalize_name(name):
    """Normalize a gallery name to a stable key.
    
    Handles OCR variations, spacing around +/&, suffixes like 'Gallery',
    and punctuation differences.
    """
    key = name.lower().strip()
    # Apply common aliases first
    key = GALLERY_ALIASES.get(key, key)
    # Normalize slashes and backslashes
    key = key.replace("\\", "/").replace("|", "/")
    # Normalize spacing around + and &
    key = re.sub(r"\s*[+&]\s*", "_and_", key)
    # Normalize Co./Co
    key = re.sub(r"co\.\s*$", "co", key)
    key = re.sub(r"co\.,", "co", key)
    # Strip trailing "gallery", "galleries", "space", "projects"
    key = re.sub(r"\s+(gallery|galleries|art\s+gallery)\s*$", "", key)
    # Strip punctuation except /
    key = re.sub(r"[^\w\s/]", "", key)
    # Collapse whitespace
    key = re.sub(r"\s+", "_", key.strip())
    # Strip leading/trailing underscores
    key = key.strip("_")
    return key


# Common abbreviations and alternate names that should map to the same gallery
GALLERY_ALIASES = {
    "art gallery of nsw": "art gallery of new south wales",
    "agnsw": "art gallery of new south wales",
    "mca": "museum of contemporary art australia",
    "museum of contemporary art": "museum of contemporary art australia",
    "nas": "national art school",
    "national art school gallery": "national art school",
    "s. h. ervin gallery": "s.h. ervin gallery",
    "sh ervin gallery": "s.h. ervin gallery",
}


def fuzzy_match_gallery(galleries, name, threshold=0.85):
    """Find an existing gallery key that fuzzy-matches the given name."""
    from difflib import SequenceMatcher
    norm = normalize_name(name)
    
    # Exact match first
    if norm in galleries:
        return norm
    
    # Fuzzy match against existing keys
    best_key = None
    best_ratio = 0
    for existing_key in galleries:
        ratio = SequenceMatcher(None, norm, existing_key).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_key = existing_key
    
    return best_key


# ---------------------------------------------------------------------------
# Geocoding via Nominatim
# ---------------------------------------------------------------------------

def geocode(address, suburb):
    """Geocode an address to lat/lng using Nominatim. Returns (lat, lng, postcode)."""
    query_parts = []
    if address:
        query_parts.append(address)
    if suburb:
        query_parts.append(suburb)
    query_parts.append("NSW")
    query_parts.append("Australia")
    query = ", ".join(query_parts)

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            r = results[0]
            lat = float(r["lat"])
            lng = float(r["lon"])
            postcode = r.get("address", {}).get("postcode", "")
            return lat, lng, postcode
    except Exception as e:
        print(f"[galleries] Geocode error for '{query}': {e}")

    return None, None, ""


# ---------------------------------------------------------------------------
# Seed + enrich
# ---------------------------------------------------------------------------

def seed_galleries(galleries):
    """Add curated seed galleries that aren't already present."""
    added = 0
    for seed in SEED_GALLERIES:
        key = normalize_name(seed["name"])
        matched = fuzzy_match_gallery(galleries, seed["name"])
        
        if matched:
            # Update missing fields only
            for field, val in seed.items():
                if val and not galleries[matched].get(field):
                    galleries[matched][field] = val
            continue

        record = {
            "name": seed["name"],
            "type": seed.get("type", "commercial"),
            "address": seed.get("address", ""),
            "suburb": seed.get("suburb", ""),
            "postcode": "",
            "latitude": None,
            "longitude": None,
            "website": seed.get("website", ""),
            "instagram": seed.get("instagram", ""),
            "email": "",
            "phone": "",
            "hours": "",
            "entry": seed.get("entry", "unknown"),
            "accessibility": "",
            "source": "seed",
            "last_verified": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        }
        galleries[key] = record
        added += 1

    print(f"[galleries] Seeded {added} new galleries")
    return added


def enrich_from_exhibitions(galleries, state):
    """Extract gallery info from exhibition records in state."""
    added = 0
    for key, rec in state.items():
        if key.startswith("__"):
            continue

        venue = rec.get("venue", "").strip()
        if not venue or len(venue) < 3:
            continue

        gkey = normalize_name(venue)
        
        # Check for exact or fuzzy match
        matched_key = fuzzy_match_gallery(galleries, venue)
        
        if matched_key:
            # Enrich existing with any new info
            g = galleries[matched_key]
            if not g.get("suburb") and rec.get("suburb"):
                g["suburb"] = rec["suburb"]
            if not g.get("address") and rec.get("address"):
                g["address"] = rec["address"]
            if not g.get("website") and rec.get("website"):
                web = rec["website"]
                if not any(d in web for d in ["timeout", "broadsheet", "artalmanac",
                                               "cityofsydney", "instagram", "facebook",
                                               "google", "artguide"]):
                    g["website"] = web
            if not g.get("instagram") and rec.get("instagram"):
                g["instagram"] = rec["instagram"]
            continue

        # New gallery discovered from exhibition
        record = {
            "name": venue,
            "type": "commercial",  # default guess
            "address": rec.get("address", ""),
            "suburb": rec.get("suburb", ""),
            "postcode": "",
            "latitude": None,
            "longitude": None,
            "website": "",
            "instagram": rec.get("instagram", ""),
            "email": "",
            "phone": "",
            "hours": "",
            "entry": "unknown",
            "accessibility": "",
            "source": f"exhibition:{rec.get('source', 'unknown')}",
            "last_verified": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        }
        # Only add website if it's a real gallery site
        web = rec.get("website", "")
        if web and not any(d in web for d in ["timeout", "broadsheet", "artalmanac",
                                               "cityofsydney", "instagram", "facebook",
                                               "google", "artguide"]):
            record["website"] = web

        galleries[gkey] = record
        added += 1

    print(f"[galleries] Enriched {added} new galleries from exhibitions")
    return added


def geocode_missing(galleries, max_geocodes=20):
    """Geocode galleries that have an address/suburb but no coordinates.

    Respects Nominatim's 1 req/sec limit. Caps per run to avoid long runtimes.
    """
    geocoded = 0
    for key, g in galleries.items():
        if geocoded >= max_geocodes:
            break
        if g.get("latitude") is not None:
            continue
        if not g.get("address") and not g.get("suburb"):
            continue

        lat, lng, postcode = geocode(g.get("address", ""), g.get("suburb", ""))
        if lat is not None:
            g["latitude"] = lat
            g["longitude"] = lng
            if postcode and not g.get("postcode"):
                g["postcode"] = postcode
            geocoded += 1

        time.sleep(1.1)  # Nominatim rate limit: max 1 req/sec

    if geocoded:
        print(f"[galleries] Geocoded {geocoded} galleries")
    return geocoded


# ---------------------------------------------------------------------------
# Build galleries output for frontend
# ---------------------------------------------------------------------------

def build_galleries_json(galleries):
    """Write docs/galleries.json for the frontend directory."""
    gallery_list = []
    for key, g in galleries.items():
        gallery_list.append({
            "id": key,
            "name": g.get("name", ""),
            "type": g.get("type", ""),
            "address": g.get("address", ""),
            "suburb": g.get("suburb", ""),
            "postcode": g.get("postcode", ""),
            "latitude": g.get("latitude"),
            "longitude": g.get("longitude"),
            "website": g.get("website", ""),
            "instagram": g.get("instagram", ""),
            "email": g.get("email", ""),
            "phone": g.get("phone", ""),
            "hours": g.get("hours", ""),
            "entry": g.get("entry", "unknown"),
            "accessibility": g.get("accessibility", ""),
        })

    # Sort by name
    gallery_list.sort(key=lambda x: x["name"].lower())

    output = {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(gallery_list),
        "galleries": gallery_list,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/galleries.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[galleries] Wrote {len(gallery_list)} galleries to docs/galleries.json")


def update_galleries(state):
    """Main entry: seed, enrich from exhibitions, geocode, build output."""
    galleries = load_galleries()
    seed_galleries(galleries)
    enrich_from_exhibitions(galleries, state)
    geocode_missing(galleries)
    save_galleries(galleries)
    build_galleries_json(galleries)
    return galleries
