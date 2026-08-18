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

# TLDs that indicate a scraped handle is actually an email domain, not Instagram
_DOMAIN_TLD_RE = re.compile(
    r"\.(com|com\.au|net|net\.au|org|org\.au|gov|gov\.au|edu|edu\.au|au|id|io|co)$",
    re.IGNORECASE,
)


def _looks_like_domain(handle):
    return bool(_DOMAIN_TLD_RE.search(handle))


# ---------------------------------------------------------------------------
# Curated seed list of known Sydney galleries
# Handles verified against gallery websites Aug 2026
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
     "instagram": "@artspacesydney", "entry": "free"},
    {"name": "Carriageworks", "type": "museum", "suburb": "Eveleigh",
     "address": "245 Wilson St", "website": "https://www.carriageworks.com.au",
     "instagram": "@carriageworks", "entry": "free"},
    {"name": "National Art School Gallery", "type": "university", "suburb": "Darlinghurst",
     "address": "156 Forbes St", "website": "https://www.nas.edu.au",
     "instagram": "@nas_au", "entry": "free"},
    {"name": "UNSW Galleries", "type": "university", "suburb": "Paddington",
     "address": "Cnr Oxford St & Greens Rd", "website": "https://www.galleries.unsw.edu.au",
     "instagram": "@unswgalleries", "entry": "free"},
    {"name": "UTS Gallery", "type": "university", "suburb": "Ultimo",
     "address": "Level 4, 702 Harris St", "website": "https://www.uts.edu.au/uts-gallery-art-collection",
     "instagram": "@utsengage", "entry": "free"},
    {"name": "Chau Chak Wing Museum", "type": "university", "suburb": "Camperdown",
     "address": "University of Sydney, University Place", "website": "https://www.sydney.edu.au/museum",
     "instagram": "@chauchakwingmuseum", "entry": "free"},
    {"name": "S.H. Ervin Gallery", "type": "museum", "suburb": "Millers Point",
     "address": "Watson Rd, Observatory Hill", "website": "https://www.shervingallery.com.au",
     "instagram": "@shervingallery", "entry": "paid"},
    {"name": "Brett Whiteley Studio", "type": "museum", "suburb": "Surry Hills",
     "address": "2 Raper St", "website": "https://www.artgallery.nsw.gov.au/visit/brett-whiteley-studio/",
     "instagram": "@brettwhiteleystudio", "entry": "free"},
    {"name": "Museum of Sydney", "type": "museum", "suburb": "Sydney",
     "address": "Cnr Phillip and Bridge streets", "website": "https://mhnsw.au/visit-us/museum-of-sydney/",
     "instagram": "", "entry": "free"},
    {"name": "Sydney Observatory", "type": "museum", "suburb": "Millers Point",
     "address": "1003 Upper Fort Street", "website": "https://powerhouse.com.au/visit/sydney-observatory",
     "instagram": "", "entry": "paid"},
    {"name": "Sydney Jewish Museum", "type": "museum", "suburb": "Darlinghurst",
     "address": "148 Darlinghurst Road", "website": "https://sydneyjewishmuseum.com.au/",
     "instagram": "", "entry": "paid"},

    # Commercial galleries — Paddington / Woollahra
    {"name": "Roslyn Oxley9 Gallery", "type": "commercial", "suburb": "Paddington",
     "address": "8 Soudan Ln", "website": "https://www.roslynoxley9.com.au",
     "instagram": "@roslynoxley9", "entry": "free"},
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
    {"name": "Darren Knight Gallery", "type": "commercial", "suburb": "Waterloo",
     "address": "840 Elizabeth St", "website": "https://www.darrenknightgallery.com",
     "instagram": "@darrenknightgallery", "entry": "free"},
    {"name": "Michael Reid Sydney", "type": "commercial", "suburb": "Chippendale",
     "address": "109 Shepherd St", "website": "https://www.michaelreid.com.au",
     "instagram": "@michaelreidsydney", "entry": "free"},
    {"name": "King Street Gallery on William", "type": "commercial", "suburb": "Darlinghurst",
     "address": "177-185 William St", "website": "https://www.kingstreetgallery.com.au",
     "instagram": "@kingstreetgallery", "entry": "free"},
    {"name": "Dominik Mersch Gallery", "type": "commercial", "suburb": "Rushcutters Bay",
     "address": "1/75 McLachlan Ave", "website": "https://www.dominikmerschgallery.com",
     "instagram": "@dominikmerschgallery", "entry": "free"},
    {"name": "Nanda\\Hobbs", "type": "commercial", "suburb": "Chippendale",
     "address": "12-14 Meagher St", "website": "https://www.nandahobbs.com",
     "instagram": "@nandahobbs", "entry": "free"},
    {"name": "China Heights Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "Level 3, 16-28 Foster St", "website": "https://chinaheights.com",
     "instagram": "@chinaheights", "entry": "free"},
    {"name": "Ames Yavuz", "type": "commercial", "suburb": "Surry Hills",
     "address": "114 Commonwealth St", "website": "https://www.amesyavuz.com",
     "instagram": "@amesyavuz", "entry": "free"},
    {"name": "Curatorial+Co.", "type": "commercial", "suburb": "Woolloomooloo",
     "address": "Shop G01/02, 80 William St", "website": "https://www.curatorialandco.com",
     "instagram": "@curatorialandco", "entry": "free"},
    {"name": "Piermarq", "type": "commercial", "suburb": "Surry Hills",
     "address": "23 Foster St", "website": "https://www.piermarq.com.au/",
     "instagram": "@piermarqart", "entry": "free"},
    {"name": "The Commercial Gallery", "type": "commercial", "suburb": "Marrickville",
     "address": "5/4 Jabez St", "website": "https://thecommercialgallery.com",
     "instagram": "@thecommercialgallery", "entry": "free"},
    {"name": "STATION Sydney", "type": "commercial", "suburb": "Surry Hills",
     "address": "91 Campbell St", "website": "https://stationgallery.com",
     "instagram": "@stationgalleryaustralia", "entry": "free"},
    {"name": "Schmick Contemporary", "type": "commercial", "suburb": "Haymarket",
     "address": "Level 1/2-16 Quay St", "website": "",
     "instagram": "@schmickcontemporary", "entry": "free"},
    {"name": "N.Smith Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "15 Foster St", "website": "https://www.nsmithgallery.com",
     "instagram": "@n.smithgallery", "entry": "free"},
    {"name": "Gaffa Gallery", "type": "commercial", "suburb": "Sydney",
     "address": "281 Clarence St", "website": "https://gaffa.com.au",
     "instagram": "@gaffagallery", "entry": "free"},
    {"name": "Woollahra Gallery at Redleaf", "type": "museum", "suburb": "Double Bay",
     "address": "548 New South Head Rd", "website": "https://www.woollahragallery.com.au/Home",
     "instagram": "@woollahragallery", "entry": "free"},
    {"name": "M2 Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "Shop 4/450 Elizabeth St", "website": "https://m2gallery.com.au",
     "instagram": "@m2gallery", "entry": "free"},

    # Commercial — East Sydney / Inner East
    {"name": "Arthouse Gallery", "type": "commercial", "suburb": "Rushcutters Bay",
     "address": "66 McLachlan Ave", "website": "https://arthousegallery.com.au",
     "instagram": "@arthousegallery", "entry": "free"},
    {"name": "Australian Galleries", "type": "commercial", "suburb": "Paddington",
     "address": "15 Roylston St", "website": "https://australiangalleries.com.au",
     "instagram": "@australiangalleries", "entry": "free"},
    {"name": "Defiance Gallery", "type": "commercial", "suburb": "Paddington",
     "address": "12 Mary Place", "website": "https://www.defiancegallery.com",
     "instagram": "@defiancegallery", "entry": "free"},
    {"name": "Fellia Melas Gallery", "type": "commercial", "suburb": "Woollahra",
     "address": "2 Moncur St", "website": "https://www.felliamelasgallery.com.au",
     "instagram": "@fellia_melas_gallery", "entry": "free"},
    {"name": "Liverpool Street Gallery", "type": "commercial", "suburb": "Darlinghurst",
     "address": "243a Liverpool St", "website": "https://www.liverpoolstgallery.com.au",
     "instagram": "@liverpoolstreetgallery", "entry": "free"},
    {"name": "Stanley Street Gallery", "type": "commercial", "suburb": "Darlinghurst",
     "address": "1/52-54 Stanley St", "website": "https://stanleystreetgallery.com.au",
     "instagram": "@stanley_street_gallery", "entry": "free"},
    {"name": "Annette Larkin Fine Art", "type": "commercial", "suburb": "Paddington",
     "address": "Suite 4, 8 Soudan Lane", "website": "https://annettelarkin.com/",
     "instagram": "", "entry": "free"},
    {"name": ".M Contemporary", "type": "commercial", "suburb": "Darlinghurst",
     "address": "8/15-19 Boundary St", "website": "https://mcontemp.com/",
     "instagram": "@.mcontemporary", "entry": "free"},
    {"name": "Chalk Horse", "type": "commercial", "suburb": "Darlinghurst",
     "address": "167 William St", "website": "https://www.chalkhorse.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Cassandra Bird", "type": "commercial", "suburb": "Potts Point",
     "address": "54 Kellett St", "website": "https://www.cassandrabird.com/",
     "instagram": "", "entry": "free"},
    {"name": "Robin Gibson Gallery", "type": "commercial", "suburb": "Darlinghurst",
     "address": "278 Liverpool St", "website": "https://robingibson.net/",
     "instagram": "", "entry": "free"},
    {"name": "Gallery Sally Dan-Cuthbert", "type": "commercial", "suburb": "Rushcutters Bay",
     "address": "20 McLachlan Ave", "website": "https://gallerysallydancuthbert.com/",
     "instagram": "", "entry": "free"},
    {"name": "Freeman Gallery", "type": "commercial", "suburb": "Potts Point",
     "address": "03/46a Macleay St", "website": "https://www.free-man.gallery/",
     "instagram": "", "entry": "free"},
    {"name": "Becker Minty", "type": "commercial", "suburb": "Potts Point",
     "address": "Shop 7, 81 Macleay St", "website": "https://www.beckerminty.com/",
     "instagram": "", "entry": "free"},
    {"name": "Art+ Gallery", "type": "commercial", "suburb": "Potts Point",
     "address": "Shop 5, 81 Macleay St", "website": "https://artplusgallery.co/",
     "instagram": "", "entry": "free"},
    {"name": "Art2Muse Gallery", "type": "commercial", "suburb": "Woollahra",
     "address": "234 Jersey Rd", "website": "https://art2muse.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "day01.", "type": "commercial", "suburb": "Darlinghurst",
     "address": "189 Crown St", "website": "https://day01.gallery/",
     "instagram": "", "entry": "free"},
    {"name": "Scieppan Gallery", "type": "commercial", "suburb": "Darlinghurst",
     "address": "Shop 2/1 Francis St", "website": "https://scieppan.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Utopia Art Sydney", "type": "commercial", "suburb": "Waterloo",
     "address": "983 Bourke St", "website": "https://utopiaartsydney.com.au",
     "instagram": "@utopiaartsydney", "entry": "free"},
    {"name": "VELVET LOBSTER", "type": "commercial", "suburb": "Surry Hills",
     "address": "Level 1/45 Hutchinson St", "website": "https://www.velvetlobster.com.au/",
     "instagram": "@velvet.lobster", "entry": "free"},
    {"name": "Blender Gallery", "type": "commercial", "suburb": "Redfern",
     "address": "Shop 2, 682 Bourke St", "website": "https://blendergallery.com/en-au",
     "instagram": "", "entry": "free"},
    {"name": "Brenda Colahan Fine Art", "type": "commercial", "suburb": "Redfern",
     "address": "G04/59 Great Buckingham St", "website": "https://bcfa.au/",
     "instagram": "", "entry": "free"},
    {"name": "Damien Minton Presents", "type": "commercial", "suburb": "Surry Hills",
     "address": "50 Buckingham St", "website": "https://damienmintonpresents.com/",
     "instagram": "", "entry": "free"},
    {"name": "Eloise Cato Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "Lower Ground, 67 Fitzroy St", "website": "https://catogallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "Flinders Street Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "61 Flinders St", "website": "https://www.flindersstreetgallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "Fox Jensen Gallery", "type": "commercial", "suburb": "Alexandria",
     "address": "68-70 Burrows Rd", "website": "https://www.jensengallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "Minerva", "type": "commercial", "suburb": "Redfern",
     "address": "14 Vine St", "website": "https://minervasydney.com/",
     "instagram": "", "entry": "free"},
    {"name": "Palangi Gallery", "type": "commercial", "suburb": "Surry Hills",
     "address": "Level 1, 59 Flinders St", "website": "https://gallery.palangi.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "PALAS", "type": "commercial", "suburb": "Zetland",
     "address": "42 Hansard St", "website": "https://palas.sydney/",
     "instagram": "", "entry": "free"},
    {"name": "Revolve Gallery & Studios", "type": "ari", "suburb": "Redfern",
     "address": "138 Little Eveleigh St", "website": "https://revolve.gallery/",
     "instagram": "", "entry": "free"},
    {"name": "Rogue Pop-up Gallery", "type": "commercial", "suburb": "Redfern",
     "address": "130 Regent St", "website": "https://roguepopup.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Sabbia Gallery", "type": "commercial", "suburb": "Redfern",
     "address": "609 Elizabeth St", "website": "https://sabbiagallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "Stella Downer Fine Art", "type": "commercial", "suburb": "Waterloo",
     "address": "1/24 Wellington St", "website": "https://www.stelladownerfineart.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "The Renshaws, Sydney", "type": "commercial", "suburb": "Alexandria",
     "address": "111-117 McEvoy St", "website": "https://therenshaws.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Tom Bass Clara Street Gallery", "type": "commercial", "suburb": "Erskineville",
     "address": "1A Clara St", "website": "https://www.clarastreetgallery.com/current-upcoming",
     "instagram": "", "entry": "free"},
    {"name": "Gallery 144", "type": "commercial", "suburb": "Surry Hills",
     "address": "144 Redfern St", "website": "https://www.gallery144.com.au/",
     "instagram": "@gallery144_", "entry": "free"},
    {"name": "Redfern Art Gallery", "type": "commercial", "suburb": "Redfern",
     "address": "80 Redfern St", "website": "https://www.redfernartgallery.com.au/",
     "instagram": "@redfern_art_gallery", "entry": "free"},
    {"name": "APY Gallery Sydney", "type": "commercial", "suburb": "Redfern",
     "address": "143 Redfern St", "website": "https://www.apygallery.com/pages/apy-gallery-sydney",
     "instagram": "", "entry": "free"},
    {"name": "Aboriginal & Pacific Art", "type": "commercial", "suburb": "Waterloo",
     "address": "1/24 Wellington St", "website": "https://www.aboriginalpacificart.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "aMBUSH Gallery", "type": "commercial", "suburb": "Waterloo",
     "address": "4a James St", "website": "https://ambushgallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "Artbank Sydney", "type": "museum", "suburb": "Waterloo",
     "address": "222 Young St", "website": "https://www.artbank.gov.au/",
     "instagram": "", "entry": "free"},
    {"name": "Art Atrium", "type": "commercial", "suburb": "Botany",
     "address": "12 Daniel St", "website": "https://artatrium.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Art Leven", "type": "commercial", "suburb": "Woolloomooloo",
     "address": "104 Cathedral St", "website": "https://artleven.com/",
     "instagram": "", "entry": "free"},
    {"name": "Art Moment Gallery", "type": "commercial", "suburb": "Bondi Beach",
     "address": "99 Curlewis St", "website": "https://www.artmoment.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Audrey Fine Art Gallery", "type": "commercial", "suburb": "Sydney",
     "address": "50 Bridge St", "website": "https://audreyfineart.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "CBD Gallery", "type": "commercial", "suburb": "Sydney",
     "address": "72 Erskine St", "website": "https://cbdgallery.com.au/",
     "instagram": "@cbdgallerysyd", "entry": "free"},
    {"name": "China Cultural Centre in Sydney", "type": "museum", "suburb": "Sydney",
     "address": "Level 1, 151 Castlereagh St", "website": "https://cccsydney.org/",
     "instagram": "", "entry": "free"},
    {"name": "D Lan Contemporary", "type": "commercial", "suburb": "Woollahra",
     "address": "97-99 Queen St", "website": "https://dlangalleries.com/",
     "instagram": "", "entry": "free"},
    {"name": "Fine Arts, Sydney", "type": "commercial", "suburb": "Paddington",
     "address": "23 Hampden St", "website": "https://www.finearts.sydney/",
     "instagram": "", "entry": "free"},
    {"name": "Korean Cultural Centre Australia Gallery", "type": "museum", "suburb": "Sydney",
     "address": "Ground Floor, 255 Elizabeth St", "website": "https://au.korean-culture.org/en",
     "instagram": "", "entry": "free"},
    {"name": "Maunsell Wickes Gallery", "type": "commercial", "suburb": "Paddington",
     "address": "19 Glenmore Rd", "website": "https://maunsellwickes.com/",
     "instagram": "", "entry": "free"},
    {"name": "Saint Cloche", "type": "commercial", "suburb": "Paddington",
     "address": "37 MacDonald St", "website": "https://saintcloche.com/",
     "instagram": "", "entry": "free"},
    {"name": "SOHO Galleries Sydney", "type": "commercial", "suburb": "Woollahra",
     "address": "150 Edgecliff Rd", "website": "https://www.sohogalleries.net/",
     "instagram": "", "entry": "free"},
    {"name": "Wagner Contemporary", "type": "commercial", "suburb": "Paddington",
     "address": "2 Hampden St", "website": "https://wagnercontemporary.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "BAROMETER Gallery", "type": "commercial", "suburb": "Paddington",
     "address": "13 Gurner St", "website": "https://barometer.net.au/",
     "instagram": "", "entry": "free"},
    {"name": "Comber Street Studios", "type": "commercial", "suburb": "Paddington",
     "address": "5 Comber St", "website": "https://www.comberstreetstudios.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Vermilion Art", "type": "commercial", "suburb": "Walsh Bay",
     "address": "16 Hickson Rd", "website": "https://vermilionart.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Passage Gallery", "type": "commercial", "suburb": "Haymarket",
     "address": "Level 1, 102/8 Quay St", "website": "https://www.passagegallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "La Perouse Museum", "type": "museum", "suburb": "La Perouse",
     "address": "1542 Anzac Parade", "website": "https://www.laperousemuseum.com.au/",
     "instagram": "", "entry": "free"},

    # Artist-run initiatives & project spaces
    {"name": "Firstdraft", "type": "ari", "suburb": "Woolloomooloo",
     "address": "13-17 Riley St", "website": "https://firstdraft.org.au",
     "instagram": "@firstdraft_", "entry": "free"},
    {"name": "Verge Gallery", "type": "university", "suburb": "Darlington",
     "address": "Jane Foss Russell Plaza, City Rd", "website": "https://www.verge-gallery.net",
     "instagram": "@vergegallery", "entry": "free"},
    {"name": "4A Centre for Contemporary Asian Art", "type": "museum", "suburb": "Haymarket",
     "address": "181-187 Hay St", "website": "https://www.4a.com.au",
     "instagram": "@4a_aus", "entry": "free"},
    {"name": "Cement Fondu", "type": "project_space", "suburb": "Paddington",
     "address": "36 Gosbell St", "website": "https://cementfondu.org",
     "instagram": "@cementfondu", "entry": "free"},
    {"name": "Airspace Projects", "type": "ari", "suburb": "Marrickville",
     "address": "10 Junction St", "website": "https://www.airspaceprojects.com.au",
     "instagram": "@airspaceprojects", "entry": "free"},
    {"name": "Articulate Project Space", "type": "ari", "suburb": "Leichhardt",
     "address": "497 Parramatta Rd", "website": "https://www.articulateprojectspace.org",
     "instagram": "@articulateprojectspace", "entry": "free"},
    {"name": "Cross Art Projects", "type": "project_space", "suburb": "Kings Cross",
     "address": "8 Llankelly Lane", "website": "https://www.crossart.com.au",
     "instagram": "@thecrossartprojects", "entry": "free"},
    {"name": "Tap Gallery", "type": "ari", "suburb": "Darlinghurst",
     "address": "259 Riley St", "website": "https://tapgallery.org.au",
     "instagram": "@tapgallery", "entry": "paid"},
    {"name": "Tin Sheds Gallery", "type": "university", "suburb": "Darlington",
     "address": "148 City Rd", "website": "https://www.sydney.edu.au/architecture/about/tin-sheds-gallery.html",
     "instagram": "@tinshedsgallery", "entry": "free"},
    {"name": "SCA Gallery", "type": "university", "suburb": "Camperdown",
     "address": "Manning Road, University of Sydney", "website": "https://www.sydney.edu.au/arts/schools/sydney-college-of-the-arts/galleries-and-exhibitions.html",
     "instagram": "", "entry": "free"},
    {"name": "Sheffer Gallery", "type": "ari", "suburb": "Darlington",
     "address": "38 Lander St", "website": "https://www.facebook.com/sheffergallery/",
     "instagram": "", "entry": "free"},
    {"name": "Boomalli Aboriginal Artists Co-operative", "type": "ari", "suburb": "Leichhardt",
     "address": "55-59 Flood St", "website": "https://boomalli.com.au",
     "instagram": "", "entry": "free"},
    {"name": "Annandale Galleries", "type": "commercial", "suburb": "Annandale",
     "address": "110 Trafalgar St", "website": "https://www.annandalegalleries.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "The Balmain Watch House", "type": "ari", "suburb": "Balmain",
     "address": "179 Darling St", "website": "https://balmainassociation.org.au/exhibitions/#schedule",
     "instagram": "", "entry": "free"},
    {"name": "Chrissie Cotter Gallery", "type": "ari", "suburb": "Camperdown",
     "address": "31A Pidcock St", "website": "https://www.innerwest.nsw.gov.au/exhibitions-and-public-art/chrissie-cotter-gallery",
     "instagram": "", "entry": "free"},
    {"name": "COMA", "type": "ari", "suburb": "Marrickville",
     "address": "37 Chapel St", "website": "https://www.comagallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "The Corner Gallery Stanmore", "type": "commercial", "suburb": "Stanmore",
     "address": "1/88 Percival Rd", "website": "https://thecornergallerystanmore.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Delmar Gallery", "type": "university", "suburb": "Ashfield",
     "address": "144 Victoria St", "website": "https://www.trinity.nsw.edu.au/community/delmar-gallery/",
     "instagram": "", "entry": "free"},
    {"name": "44", "type": "ari", "suburb": "Rozelle",
     "address": "44 Callan St", "website": "https://linktr.ee/44_rozelle",
     "instagram": "", "entry": "free"},
    {"name": "Gallery 371", "type": "commercial", "suburb": "Marrickville",
     "address": "371 Enmore Rd", "website": "https://www.gallery371.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Gallery LNL", "type": "commercial", "suburb": "Newtown",
     "address": "49-51 King St", "website": "https://gallerylnl.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Glass Artists' Gallery", "type": "commercial", "suburb": "Glebe",
     "address": "Level 2, 68 Glebe Point Rd", "website": "https://glassartistsgallery.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "LAILA", "type": "ari", "suburb": "Marrickville",
     "address": "Level 1, 158 Edinburgh Rd", "website": "https://www.laila.sydney/",
     "instagram": "@laila__sydney", "entry": "free"},
    {"name": "McGlade Gallery, Australian Catholic University", "type": "university", "suburb": "Strathfield",
     "address": "25a Barker Rd", "website": "https://www.acu.edu.au/about-acu/faculties-directorates-and-staff/faculty-of-education-and-arts/acu-galleries/acu-mcglade-gallery-at-strathfield",
     "instagram": "", "entry": "free"},
    {"name": "16albermarle Project Space", "type": "ari", "suburb": "Newtown",
     "address": "16 Albermarle St", "website": "https://www.16albermarle.com/",
     "instagram": "", "entry": "free"},
    {"name": "Studio 551", "type": "commercial", "suburb": "Newtown",
     "address": "551 King St", "website": "https://studio551.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Syrup", "type": "ari", "suburb": "Marrickville",
     "address": "20 Farr St", "website": "https://www.syrupcontemporary.com/",
     "instagram": "", "entry": "free"},
    {"name": "Tiliqua Tiliqua", "type": "ari", "suburb": "Enmore",
     "address": "257 Enmore Rd", "website": "https://www.tiliquastudio.com/",
     "instagram": "@tiliquatiliqua", "entry": "free"},
    {"name": "UPSpace Gallery + Studio", "type": "ari", "suburb": "Marrickville",
     "address": "Building 24, 142 Addison Rd", "website": "https://www.upspacegallery.com/",
     "instagram": "", "entry": "free"},
    {"name": "Adelaide Perry Gallery", "type": "university", "suburb": "Croydon",
     "address": "Cnr Hennessy and College streets", "website": "https://apg.plc.nsw.edu.au/",
     "instagram": "", "entry": "free"},

    # North Sydney / Northern Beaches
    {"name": "Art Space Gallery – The Concourse", "type": "museum", "suburb": "Chatswood",
     "address": "409 Victoria Ave", "website": "https://www.willoughby.nsw.gov.au/Community/Arts-and-culture/Visual-arts/Art-Space-Gallery-%E2%80%93-The-Concourse",
     "instagram": "", "entry": "free"},
    {"name": "Manly Art Gallery & Museum", "type": "museum", "suburb": "Manly",
     "address": "West Esplanade Reserve", "website": "https://www.northernbeaches.nsw.gov.au/things-to-do/arts-and-culture/manly-art-gallery-museum",
     "instagram": "@beachescouncil", "entry": "free"},
    {"name": "Mosman Art Gallery", "type": "museum", "suburb": "Mosman",
     "address": "1 Art Gallery Way", "website": "https://mosmanartgallery.org.au/",
     "instagram": "", "entry": "free"},
    {"name": "Art Atrium 48", "type": "commercial", "suburb": "Milsons Point",
     "address": "Level 1, 48 Alfred St South", "website": "https://artatrium.com.au/48-",
     "instagram": "", "entry": "free"},
    {"name": "Art Bau", "type": "commercial", "suburb": "Brookvale",
     "address": "1 Mitchell Rd", "website": "https://www.artbau.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "depart Art Gallery", "type": "commercial", "suburb": "Lindfield",
     "address": "350 Pacific Highway", "website": "https://mayflower-reindeer-by2b.squarespace.com/",
     "instagram": "", "entry": "free"},
    {"name": "Gallery Lane Cove + Creative Studios", "type": "commercial", "suburb": "Lane Cove",
     "address": "164 Longueville Rd", "website": "https://www.gallerylanecove.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Harvey Galleries Seaforth", "type": "commercial", "suburb": "Seaforth",
     "address": "515 Sydney Rd", "website": "https://harveygalleries.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "M.C. & SHELLY Gallery", "type": "commercial", "suburb": "Mosman",
     "address": "Shop 1, 934-936 Military Rd", "website": "https://www.instagram.com/mcshelly.gallery/",
     "instagram": "@mcshelly.gallery", "entry": "free"},
    {"name": "Michael Reid Northern Beaches", "type": "commercial", "suburb": "Newport",
     "address": "Shop 2/358 Barrenjoey Rd", "website": "https://michaelreidnorthernbeaches.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Rochfort Gallery", "type": "commercial", "suburb": "North Sydney",
     "address": "317 Pacific Highway", "website": "https://rochfortgallery.com/",
     "instagram": "", "entry": "free"},

    # Greater Sydney
    {"name": "Grace Cossington Smith Gallery", "type": "university", "suburb": "Wahroonga",
     "address": "Gate 7, 1666 Pacific Highway", "website": "https://www.abbotsleigh.nsw.edu.au/grace-cossington-smith-gallery/",
     "instagram": "@gcsgallery", "entry": "free"},
    {"name": "Hazelhurst Arts Centre", "type": "museum", "suburb": "Gymea",
     "address": "782 Kingsway", "website": "https://hazelhurst.sutherlandshire.nsw.gov.au/",
     "instagram": "@hazelhurstartscentre", "entry": "free"},
    {"name": "Macquarie University Art Gallery", "type": "university", "suburb": "North Ryde",
     "address": "19 Eastern Rd, Macquarie University", "website": "https://www.mq.edu.au/about/facilities/museums-collections/macquarie-university-art-gallery",
     "instagram": "@macquarieuni", "entry": "free"},
    {"name": "The Garden Gallery, Royal Botanic Garden Sydney", "type": "commercial", "suburb": "Sydney",
     "address": "Mrs Macquaries Rd", "website": "https://franceskeevil.com.au/",
     "instagram": "@franceskeevil", "entry": "free"},
    {"name": "The Ken Done Gallery", "type": "commercial", "suburb": "The Rocks",
     "address": "1 Hickson Rd", "website": "https://kendone.com.au/",
     "instagram": "@kendonegallery", "entry": "free"},
    {"name": "Bankstown Arts Centre", "type": "museum", "suburb": "Bankstown",
     "address": "5 Olympic Parade", "website": "https://www.bankstownartscentre.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Campbelltown Arts Centre", "type": "museum", "suburb": "Campbelltown",
     "address": "1 Art Gallery Rd", "website": "https://www.campbelltownartscentre.com.au/Home",
     "instagram": "", "entry": "free"},
    {"name": "Fairfield City Museum & Gallery", "type": "museum", "suburb": "Smithfield",
     "address": "634 The Horsley Drive", "website": "https://www.fcmg.nsw.gov.au/Home",
     "instagram": "", "entry": "free"},
    {"name": "Granville Centre Art Gallery", "type": "museum", "suburb": "Granville",
     "address": "1 Memorial Drive", "website": "https://www.cumberland.nsw.gov.au/granville-centre-art-gallery",
     "instagram": "", "entry": "free"},
    {"name": "Hawkesbury Regional Gallery", "type": "museum", "suburb": "Windsor",
     "address": "300 George St", "website": "https://www.hawkesbury.nsw.gov.au/gallery",
     "instagram": "", "entry": "free"},
    {"name": "Hurstville Museum & Gallery", "type": "museum", "suburb": "Hurstville",
     "address": "14 MacMahon St", "website": "https://www.georgesriver.nsw.gov.au/Community/Art-and-Culture/Hurstville-Museum-Gallery/Exhibitions",
     "instagram": "", "entry": "free"},
    {"name": "Liverpool Powerhouse", "type": "museum", "suburb": "Casula",
     "address": "1 Powerhouse Rd", "website": "https://www.liverpoolpowerhouse.com.au/whats-on/galleries/current-exhibitions",
     "instagram": "", "entry": "free"},
    {"name": "Penrith Regional Gallery", "type": "museum", "suburb": "Emu Plains",
     "address": "86 River Rd", "website": "https://www.penrithregionalgallery.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Powerhouse Castle Hill", "type": "museum", "suburb": "Castle Hill",
     "address": "2 Green Rd", "website": "https://powerhouse.com.au/visit/castle-hill",
     "instagram": "", "entry": "free"},
    {"name": "SI Space Ideation Projects", "type": "commercial", "suburb": "Liverpool",
     "address": "Upper Level, 3/81 Scott St", "website": "https://www.siprojects.com.au/",
     "instagram": "", "entry": "free"},
    {"name": "Boom Gate Gallery", "type": "museum", "suburb": "Malabar",
     "address": "1300 Anzac Parade", "website": "https://www.nsw.gov.au/arts-and-culture/boom-gate-gallery",
     "instagram": "", "entry": "free"},

    # Greater North Shore
    {"name": "Ku-ring-gai Art Centre", "type": "museum", "suburb": "Roseville",
     "address": "3 Recreation Ave", "website": "https://www.krg.nsw.gov.au/Things-to-do/Ku-ring-gai-Art-Centre/Exhibitions",
     "instagram": "", "entry": "free"},
    {"name": "Wallarobba Arts and Cultural Centre", "type": "museum", "suburb": "Hornsby",
     "address": "25 Edgeworth David Ave", "website": "https://www.hornsby.nsw.gov.au/Community/Arts-and-culture/Wallarobba-Arts-and-Cultural-Centre",
     "instagram": "", "entry": "free"},

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
    """Normalize a gallery name to a stable key."""
    key = name.lower().strip()
    key = key.replace("\\", "/").replace("|", "/")
    key = re.sub(r"\s*[+&]\s*", "_and_", key)
    key = re.sub(r"co\.\s*$", "co", key)
    key = re.sub(r"co\.,", "co", key)
    key = re.sub(r"[^\w\s/]", "", key)
    key = re.sub(r"\s+", "_", key.strip())
    key = key.strip("_")
    return key


def normalize_venue(name):
    """Normalize a scraped venue name for matching against gallery keys.

    More aggressive than normalize_name — strips trailing city/state
    qualifiers, gallery suffix, and parentheticals that scrapers add
    but which don't appear in the canonical gallery name.
    """
    key = name.lower().strip()
    key = key.replace("\\", "/").replace("|", "/")
    key = re.sub(r"\s*[+&]\s*", "_and_", key)
    # Strip trailing scraped qualifiers
    key = re.sub(r"\s+(in\s+)?sydney\s*$", "", key)
    key = re.sub(r"\s+australia\s*$", "", key)
    key = re.sub(r"\s+(gallery|galleries|art\s+gallery)\s*$", "", key)
    # Strip parentheticals like "(formerly outsider)"
    key = re.sub(r"\s*\(.*?\)\s*$", "", key)
    key = re.sub(r"co\.\s*$", "co", key)
    key = re.sub(r"[^\w\s/]", "", key)
    key = re.sub(r"\s+", "_", key.strip())
    key = key.strip("_")
    return key


def fuzzy_match_gallery(galleries, name, threshold=0.85):
    """Find an existing gallery key that fuzzy-matches the given name."""
    from difflib import SequenceMatcher

    # Explicit aliases — known scraped variants that should map to canonical keys
    ALIASES = {
        # AGNSW variants
        "art gallery of nsw":                       "art_gallery_of_new_south_wales",
        "agnsw":                                    "art_gallery_of_new_south_wales",
        # MCA variants
        "mca":                                      "museum_of_contemporary_art_australia",
        "mca australia":                            "museum_of_contemporary_art_australia",
        "museum of contemporary art":               "museum_of_contemporary_art_australia",
        "museum of contemporary art australia":     "museum_of_contemporary_art_australia",
        # Other common truncations
        "redfern art gallery in sydney":            "redfern_art_gallery",
        "woollahra gallery":                        "woollahra_gallery_at_redleaf",
        "gallery 144 (formerly outsider)":          "gallery_144",
        "gallery 144 formerly outsider":            "gallery_144",
        "outsider gallery":                         "gallery_144",
        "michael reid":                             "michael_reid_sydney",
        "sally dan cuthbert":                       "gallery_sally_dancuthbert",
        "king street gallery":                      "king_street_gallery_on_william",
        "nas gallery":                              "national_art_school_gallery",
        "national art school":                      "national_art_school_gallery",
        "artbank":                                  "artbank_sydney",
        "annandale":                                "annandale_galleries",
        "sca":                                      "sca_gallery",
        "passage":                                  "passage_gallery",
        "cato gallery":                             "eloise_cato",
        "laila gallery":                            "laila",
        "velvet lobster":                           "velvet_lobster",
        "arthouse":                                 "arthouse_gallery",
        "olsen annexe":                             "olsen_gallery",
    }

    # Use normalize_venue (strips city/gallery suffixes) for matching
    # but normalize_name for key lookup (stable, no stripping)
    norm = normalize_name(name)
    venue_norm = normalize_venue(name)
    alias_key = name.lower().strip()

    # Check explicit alias first
    if alias_key in ALIASES:
        canonical = ALIASES[alias_key]
        if canonical in galleries:
            return canonical

    # Exact key match
    if norm in galleries:
        return norm

    # Venue-normalized key match (strips city/gallery suffix)
    if venue_norm in galleries:
        return venue_norm

    best_key = None
    best_ratio = 0
    for existing_key in galleries:
        ratio = max(
            SequenceMatcher(None, norm, existing_key).ratio(),
            SequenceMatcher(None, venue_norm, existing_key).ratio(),
        )
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
# Instagram enrichment from gallery websites
# ---------------------------------------------------------------------------

def _fetch_instagram_from_website(url):
    """Fetch a gallery's own website and extract its Instagram handle.

    Looks for instagram.com href links in the HTML — the same pattern
    galleries use in their nav/footer social icons.
    Returns '@handle' or '' if not found.
    """
    if not url or not url.startswith("http"):
        return ""

    # Skip known non-gallery domains
    SKIP_DOMAINS = ("instagram.com", "facebook.com", "linktr.ee", "google.com",
                    "nsw.gov.au", "sydney.edu.au", "uts.edu.au", "acu.edu.au",
                    "mq.edu.au", "powerhouse.com.au")
    if any(d in url for d in SKIP_DOMAINS):
        return ""

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; art-openings-syd/1.0)"},
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return ""

        html = resp.text

        # Look for instagram.com/handle in href attributes
        m = re.search(
            r'href=["\']https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)/?["\']',
            html,
        )
        if m:
            handle = m.group(1)
            # Reject nav/explore/account paths
            if handle.lower() not in ("", "p", "explore", "accounts", "reel", "reels",
                                       "stories", "ar", "tv", "web", "legal"):
                return f"@{handle}"

    except Exception as e:
        print(f"[galleries] Website fetch error for {url}: {e}")

    return ""


def enrich_gallery_instagram(galleries, max_fetches=10):
    """For galleries with a website but no instagram handle, fetch their site
    and extract the Instagram link from the HTML.

    Runs daily but only fetches galleries missing a handle — won't re-fetch
    ones already set. Capped at max_fetches per run to stay within cron time.
    """
    fetched = 0
    updated = 0

    for key, g in galleries.items():
        if fetched >= max_fetches:
            break
        if g.get("instagram"):
            continue
        website = g.get("website", "")
        if not website:
            continue

        handle = _fetch_instagram_from_website(website)
        fetched += 1

        if handle:
            g["instagram"] = handle
            g["last_verified"] = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            updated += 1
            print(f"[galleries] Found Instagram {handle} for {g['name']}")
        else:
            print(f"[galleries] No Instagram found on website for {g['name']}")

        time.sleep(1.0)  # be polite

    if fetched:
        print(f"[galleries] Website IG enrichment: fetched {fetched}, updated {updated}")
    return updated


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
            # Update address and website from seed if missing, but do NOT
            # overwrite instagram — seed is authoritative for handles we've
            # verified; enrich_gallery_instagram handles the rest
            for field in ("address", "website", "entry", "type"):
                if seed.get(field) and not galleries[matched].get(field):
                    galleries[matched][field] = seed[field]
            # Always apply seed instagram if seed has one (seed is verified)
            if seed.get("instagram"):
                galleries[matched]["instagram"] = seed["instagram"]
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
    """Extract gallery address/suburb from exhibition records in state.

    Deliberately does NOT write instagram handles — those come only from
    seed data (verified) or enrich_gallery_instagram (scraped from the
    gallery's own website). This prevents scraped exhibition text from
    polluting instagram fields with email domains and wrong handles.
    """
    # Venue names that are scraped garbage and must never become gallery entries
    VENUE_BLOCKLIST = {
        # Redleaf junk
        "redleaf opening hours free admission wednesday",
        "redleaf's", "redleafs",
        "redleaf exhibition call out is open until",
        # Short/ambiguous names that are aliases, not real entries
        "woollahra gallery", "mca", "agnsw", "gallery", "olsen annexe",
        # Art fairs and events (not permanent galleries)
        "melbourne art fair 2026", "melbourne art fair", "art fair",
        "sydney contemporary", "biennale of sydney",
        "25th biennale of sydney",
        # Generic scraped page text
        "opening hours", "free admission", "what's on", "whats on",
        "exhibition listing", "related posts", "acknowledgement of country",
        "terms and conditions", "privacy policy",
    }

    # Also block any venue name containing these substrings
    VENUE_BLOCK_SUBSTRINGS = [
        "opening hours", "free admission", "call out is open",
        "acknowledgement", "terms and conditions", "privacy policy",
        "newsletter", "subscribe", "follow us", "click here",
    ]

    added = 0
    for key, rec in state.items():
        if key.startswith("__"):
            continue

        venue = rec.get("venue", "").strip()
        if not venue or len(venue) < 3:
            continue

        # Block junk venue names
        vl = venue.lower()
        if vl in VENUE_BLOCKLIST:
            continue
        if any(s in vl for s in VENUE_BLOCK_SUBSTRINGS):
            continue
        # Block suspiciously long venue names (likely scraped paragraph text)
        if len(venue) > 80:
            continue

        matched_key = fuzzy_match_gallery(galleries, venue)

        if matched_key:
            g = galleries[matched_key]
            if not g.get("suburb") and rec.get("suburb"):
                g["suburb"] = rec["suburb"]
            if not g.get("address") and rec.get("address"):
                g["address"] = rec["address"]
            # Only fill website if it's a real gallery site (not aggregator)
            if not g.get("website") and rec.get("website"):
                web = rec["website"]
                if not any(d in web for d in ["timeout", "broadsheet", "artalmanac",
                                               "cityofsydney", "instagram", "facebook",
                                               "google", "artguide"]):
                    g["website"] = web
            # instagram intentionally not written here
            continue

        # New gallery discovered from exhibition data
        record = {
            "name": venue,
            "type": "commercial",
            "address": rec.get("address", ""),
            "suburb": rec.get("suburb", ""),
            "postcode": "",
            "latitude": None,
            "longitude": None,
            "website": "",
            "instagram": "",  # will be filled by enrich_gallery_instagram
            "email": "",
            "phone": "",
            "hours": "",
            "entry": "unknown",
            "accessibility": "",
            "source": f"exhibition:{rec.get('source', 'unknown')}",
            "last_verified": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        }
        web = rec.get("website", "")
        if web and not any(d in web for d in ["timeout", "broadsheet", "artalmanac",
                                               "cityofsydney", "instagram", "facebook",
                                               "google", "artguide"]):
            record["website"] = web

        gkey = normalize_name(venue)
        galleries[gkey] = record
        added += 1

    print(f"[galleries] Enriched {added} new galleries from exhibitions")
    return added


def geocode_missing(galleries, max_geocodes=20):
    """Geocode galleries that have an address/suburb but no coordinates."""
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

        time.sleep(1.1)

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
    """Main entry: seed, enrich from exhibitions, enrich IG from websites,
    geocode, build output."""
    galleries = load_galleries()
    seed_galleries(galleries)
    enrich_from_exhibitions(galleries, state)
    enrich_gallery_instagram(galleries, max_fetches=10)
    geocode_missing(galleries)
    save_galleries(galleries)
    build_galleries_json(galleries)
    return galleries
