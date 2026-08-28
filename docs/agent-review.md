# openings review -- 2026-08-28 05:25 UTC

`galleries.json` -- **251 proposed changes**

## Errors

- geocode: unexpected failure (AttributeError: 'Geocoder' object has no attribute 'delay')

## Summary

| Change | Confidence | Count |
|---|---|---|
| flag_record | high | 26 |
| flag_record | medium | 17 |
| merge | high | 2 |
| set_field | high | 202 |
| set_field | medium | 4 |

## Field updates (206)

### high confidence (202)

- **china_heights.hours: (empty) -> '12-5pm Wed-Sat'**
  - extracted from art gallery website
  - source: https://chinaheights.com
  - evidence: _Continues 12-5pm Wed-Sat until 13.09.2026_
- **the_commercial.hours: (empty) -> 'Thursday–Saturday, 11–4. Outside these hours, we are available online, by phone and for visits by appointment.'**
  - extracted from art gallery website
  - source: https://thecommercialgallery.com
  - evidence: _Thursday–Saturday, 11–4. Outside these hours, we are available online, by phone and for visits by appointment._
- **the_commercial.phone: (empty) -> '+61 2 8096 3292'**
  - extracted from art gallery website
  - source: https://thecommercialgallery.com
  - evidence: _+61 2 8096 3292_
- **the_commercial.postcode: (empty) -> '2024'**
  - extracted from art gallery website
  - source: https://thecommercialgallery.com
  - evidence: _Marrickville, Sydney New South Wales, 2024_
- **station_sydney.hours: (empty) -> 'Tuesday–Saturday 10.00am–5.00pm'**
  - extracted from art gallery website
  - source: https://stationgallery.com
  - evidence: _Tuesday–Saturday 10.00am–5.00pm_
- **station_sydney.phone: (empty) -> '+61 2 9055 4688'**
  - extracted from art gallery website
  - source: https://stationgallery.com
  - evidence: _+61 2 9055 4688_
- **station_sydney.email: (empty) -> 'post@stationgallery.com'**
  - extracted from art gallery website
  - source: https://stationgallery.com
  - evidence: _post@stationgallery.com_
- **station_sydney.postcode: (empty) -> '2010'**
  - extracted from art gallery website
  - source: https://stationgallery.com
  - evidence: _Surry Hills, New South Wales 2010_
- **nsmith.hours: (empty) -> '10am – 5pm Tues – Fri, 10am – 4pm Sat, Or by appointment'**
  - extracted from art gallery website
  - source: https://www.nsmithgallery.com
  - evidence: _10am – 5pm Tues – Fri  10am – 4pm Sat  Or by appointment_
- **nsmith.phone: (empty) -> '02 8356 9256'**
  - extracted from art gallery website
  - source: https://www.nsmithgallery.com
  - evidence: _p: 02 8356 9256_
- **nsmith.email: (empty) -> 'art@nsmithgallery.com'**
  - extracted from art gallery website
  - source: https://www.nsmithgallery.com
  - evidence: _e:  art@nsmithgallery.com_
- **4a_centre_for_contemporary_asian_art.hours: (empty) -> 'Wednesday to Sunday, 11am – 5pm'**
  - extracted from art gallery website
  - source: https://4a.com.au/
  - evidence: _Wednesday to Sunday, 11am – 5pm_
- **4a_centre_for_contemporary_asian_art.email: (empty) -> 'hello@4a.com.au'**
  - extracted from art gallery website
  - source: https://4a.com.au/
  - evidence: _please contact email hello@4A.com.au_
- **cement_fondu.phone: (empty) -> '02 9331 7775'**
  - extracted from art gallery website
  - source: https://cementfondu.org
  - evidence: _P. 02 9331 7775_
- **cement_fondu.email: (empty) -> 'hello@cementfondu.com'**
  - extracted from art gallery website
  - source: https://cementfondu.org
  - evidence: _hello@cementfondu.com_
- **cross_art_projects.hours: (empty) -> '11am to 5pm Thursday to Saturday (Saturday close at 4pm) Closed public holidays.'**
  - extracted from art gallery website
  - source: https://crossart.com.au/
  - evidence: _11am to 5pm Thursday to Saturday (Saturday close at 4pm) Closed public holidays._
- **cross_art_projects.phone: (empty) -> '0406 537 933'**
  - extracted from art gallery website
  - source: https://crossart.com.au/
  - evidence: _Contact Jo Holder, 0406 537 933_
- **cross_art_projects.email: (empty) -> 'info@crossart.com.au'**
  - extracted from art gallery website
  - source: https://crossart.com.au/
  - evidence: _info@crossart.com.au_
- **cross_art_projects.postcode: (empty) -> '2011'**
  - extracted from art gallery website
  - source: https://crossart.com.au/
  - evidence: _Kings Cross, Sydney 2011_
- **gaffa.hours: (empty) -> 'Monday By Appointment Only, Tuesday-Friday 10am-6pm, Saturday 10am-5pm, Sunday and Public Holidays closed'**
  - extracted from art gallery website
  - source: https://www.gaffa.com.au/
  - evidence: _Monday By Appointment Only Tuesday-Friday 10am-6pm Saturday 10am-5pm  Sunday and Public Holidays closed_
- **gaffa.phone: (empty) -> '(+61) 02 9283 4273'**
  - extracted from art gallery website
  - source: https://www.gaffa.com.au/
  - evidence: _(+61) 02 9283 4273_
- **gaffa.email: (empty) -> 'gallery@gaffa.com.au'**
  - extracted from art gallery website
  - source: https://www.gaffa.com.au/
  - evidence: _Alternatively, you can email gallery@gaffa.com.au_
- **tap.hours: (empty) -> 'open daily from 12 – 6pm'**
  - extracted from art gallery website
  - source: https://www.tapgallery.org.au/
  - evidence: _TAP is open daily from 12 – 6pm._
- **tap.phone: (empty) -> '0400610440'**
  - extracted from art gallery website
  - source: https://www.tapgallery.org.au/
  - evidence: _Tel: 0400610440_
- **tap.email: (empty) -> 'info@tapgallery.org.au'**
  - extracted from art gallery website
  - source: https://www.tapgallery.org.au/
  - evidence: _Email: info@tapgallery.org.au_
- **audrey_fine.hours: (empty) -> 'Monday to Friday, 9am to 6pm. Weekends by appointment.'**
  - extracted from art gallery website
  - source: https://audreyfineart.com.au/
  - evidence: _Open Monday to Friday, 9am to 6pm. Weekends by appointment._
- **the_ken_done.hours: (empty) -> '10am - 5:30pm, 7 days'**
  - extracted from art gallery website
  - source: https://kendone.com.au/
  - evidence: _Opening Hours  10am - 5:30pm, 7 days_
- **the_ken_done.email: (empty) -> 'gallery@done.com.au'**
  - extracted from art gallery website
  - source: https://kendone.com.au/
  - evidence: _please email: gallery@done.com.au_
- **arthouse.hours: (empty) -> 'Tuesday to Friday 9.30am - 6pm, Saturday 10am - 5pm'**
  - extracted from art gallery website
  - source: https://arthousegallery.com.au/
  - evidence: _Opening Hours Tuesday to Friday 9.30am - 6pm  Saturday 10am - 5pm_
- **arthouse.phone: (empty) -> '+61 2 9332 1019'**
  - extracted from art gallery website
  - source: https://arthousegallery.com.au/
  - evidence: _+61 2 9332 1019_
- **liverpool_street.hours: (empty) -> 'Tuesday - Saturday 10am - 6pm'**
  - extracted from art gallery website
  - source: https://www.liverpoolstgallery.com.au/
  - evidence: _Tuesday - Saturday 10am - 6pm_
- **liverpool_street.phone: (empty) -> '+61 2 8353 7799'**
  - extracted from art gallery website
  - source: https://www.liverpoolstgallery.com.au/
  - evidence: _T +61 2 8353 7799_
- **liverpool_street.email: (empty) -> 'info@liverpoolstgallery.com.au'**
  - extracted from art gallery website
  - source: https://www.liverpoolstgallery.com.au/
  - evidence: _E info@liverpoolstgallery.com.au_
- **stanley_street.hours: (empty) -> 'Thursday – Saturday 11am – 5pm during exhibition dates. Closed on public holidays. We welcome private viewings by appointment outside of gallery hours.'**
  - extracted from art gallery website
  - source: https://stanleystreetgallery.com.au/
  - evidence: _Thursday – Saturday 11am – 5pm during exhibition dates  Closed on public holidays  We welcome private viewings by appointment outside of gallery hours._
- **stanley_street.phone: (empty) -> '+61 (02) 9368 1142'**
  - extracted from art gallery website
  - source: https://stanleystreetgallery.com.au/
  - evidence: _+61 (02) 9368 1142_
- **brett_whiteley_studio.hours: (empty) -> 'Open Thursday to Sunday 10am – 4pm'**
  - extracted from art gallery website
  - source: https://www.artgallery.nsw.gov.au/visit/brett-whiteley-studio/
  - evidence: _Open Thursday to Sunday 10am – 4pm_
- **brett_whiteley_studio.phone: (empty) -> '02 9225 1881'**
  - extracted from art gallery website
  - source: https://www.artgallery.nsw.gov.au/visit/brett-whiteley-studio/
  - evidence: _phone 02 9225 1881_
- **brett_whiteley_studio.email: (empty) -> 'brettwhiteleystudio@ag.nsw.gov.au'**
  - extracted from art gallery website
  - source: https://www.artgallery.nsw.gov.au/visit/brett-whiteley-studio/
  - evidence: _email brettwhiteleystudio@ag.nsw.gov.au_
- **brett_whiteley_studio.accessibility: (empty) -> 'There is a step 100mm at the entry door to the Brett Whiteley Studio. During the interim period, wheelchair users can access the studio via a portable ramp. Assistance animals are welcome to the Brett Whiteley Studio. An internal lift provides access between public levels of the Brett Whiteley Studio.'**
  - extracted from art gallery website
  - source: https://www.artgallery.nsw.gov.au/visit/brett-whiteley-studio/
  - evidence: _There is a step 100mm at the entry door to the Brett Whiteley Studio.  During the interim period, wheelchair users can access the studio via a portable ramp. If possible, please contact us via email b_
- **utopia_art_sydney.hours: (empty) -> 'Tuesday - Saturday, 10:00 am - 5:00 pm'**
  - extracted from art gallery website
  - source: https://utopiaartsydney.com.au/
  - evidence: _Hours : Tuesday - Saturday, 10:00 am - 5:00 pm_
- _...and 162 more_

### medium confidence (4)

- **passage.postcode: (empty) -> '2000'**
  - extracted from art gallery website
  - source: https://www.passagegallery.com/
  - evidence: _NSW 2000_
- **eloise_cato.postcode: (empty) -> '2010'**
  - extracted from art gallery website
  - source: https://catogallery.com/
  - evidence: _NSW, 2010_
- **freeman.postcode: (empty) -> '2011'**
  - extracted from art gallery website
  - source: https://www.free-man.gallery/
  - evidence: _NSW 2011_
- **palangi.postcode: (empty) -> '2010'**
  - extracted from art gallery website
  - source: https://gallery.palangi.com.au/
  - evidence: _NSW 2010_

## Possible duplicates (2)

### high confidence (2)

- **merge tom_bass_clara_street into clara_street_gallery**
  - identical normalised name: 'clara street gallery'
- **merge tom_bass_clara_street into clara_street_gallery**
  - Identical details with renamed venue

## Flagged for review (43)

### high confidence (26)

- **flag audrey_fine: missing required field(s): suburb**
- **flag macquarie_university: missing required field(s): suburb**
- **flag grace_cossington_smith: missing required field(s): suburb**
- **flag state_library_of_nsw: missing required field(s): suburb**
- **flag ngununggula: coordinates (-34.4816626, 150.4177868) fall outside Greater Sydney**
- **flag carriageworks: website is dead (HTTP 403): https://www.carriageworks.com.au**
  - source: https://www.carriageworks.com.au
- **flag uts: website is dead (HTTP 404): https://www.uts.edu.au/uts-art**
  - source: https://www.uts.edu.au/uts-art
- **flag sullivan_and_strumpf: website is dead (HTTP 429): https://sullivanstrumpf.com**
  - source: https://sullivanstrumpf.com
- **flag unsw: website is dead (HTTP 404): https://www.unsw.edu.au/unsw-galleries**
  - source: https://www.unsw.edu.au/unsw-galleries
- **flag dominik_mersch: website is dead (unreachable): https://www.dmgart.com.au**
  - source: https://www.dmgart.com.au
- **flag piermarq: website is dead (unreachable): https://www.piermarq.com**
  - source: https://www.piermarq.com
- **flag ames_yavuz: website is dead (unreachable): https://www.amesyavuz.com**
  - source: https://www.amesyavuz.com
- **flag hazelhurst_arts_centre: website is dead (HTTP 403): https://hazelhurst.sutherlandshire.nsw.gov.au/**
  - source: https://hazelhurst.sutherlandshire.nsw.gov.au/
- **flag macquarie_university: website is dead (HTTP 403): https://www.mq.edu.au/about/facilities/museums-collections/macquarie-university-art-gallery**
  - source: https://www.mq.edu.au/about/facilities/museums-collections/macquarie-university-art-gallery
- **flag verge: website is dead (HTTP 403): https://www.vergegallery.net**
  - source: https://www.vergegallery.net
- **flag china_cultural_centre_in_sydney: website is dead (unreachable): https://cccsydney.org/**
  - source: https://cccsydney.org/
- **flag la_perouse_museum: website is dead (HTTP 403): https://www.laperousemuseum.com.au/**
  - source: https://www.laperousemuseum.com.au/
- **flag 44: website is dead (HTTP 403): https://linktr.ee/44_rozelle**
  - source: https://linktr.ee/44_rozelle
- **flag mcglade_gallery_australian_catholic_university: website is dead (HTTP 403): https://www.acu.edu.au/about-acu/faculties-directorates-and-staff/faculty-of-education-and-arts/acu-galleries/acu-mcglade-gallery-at-strathfield**
  - source: https://www.acu.edu.au/about-acu/faculties-directorates-and-staff/faculty-of-education-and-arts/acu-galleries/acu-mcglade-gallery-at-strathfield
- **flag harvey_galleries_seaforth: website is dead (HTTP 403): https://harveygalleries.com.au/**
  - source: https://harveygalleries.com.au/
- **flag hawkesbury_regional: website is dead (HTTP 403): https://www.hawkesbury.nsw.gov.au/gallery**
  - source: https://www.hawkesbury.nsw.gov.au/gallery
- **flag liverpool_powerhouse: website is dead (HTTP 403): https://www.liverpoolpowerhouse.com.au/whats-on/galleries/current-exhibitions**
  - source: https://www.liverpoolpowerhouse.com.au/whats-on/galleries/current-exhibitions
- **flag depart: website is dead (HTTP 404): https://mayflower-reindeer-by2b.squarespace.com/**
  - source: https://mayflower-reindeer-by2b.squarespace.com/
- **flag tramsheds_harold_park: website is dead (unreachable): https://tramshedsharoldpark.com.au/**
  - source: https://tramshedsharoldpark.com.au/
- **flag artbank_sydney: website is dead (unreachable): https://www.artbank.gov.au/**
  - source: https://www.artbank.gov.au/
- **flag yavuz: website is dead (unreachable): https://www.yavuzgallery.com**
  - source: https://www.yavuzgallery.com

### medium confidence (17)

- **flag white_rabbit: website redirects to https://whiterabbitcollection.org/**
  - source: https://www.whiterabbitcollection.org
- **flag national_art_school: website redirects to https://nas.edu.au/**
  - source: https://www.nas.edu.au
- **flag darren_knight: website redirects to https://darrenknightgallery.com/**
  - source: https://www.darrenknightgallery.com
- **flag sarah_cottier: website redirects to https://sarahcottiergallery.com/**
  - source: https://www.sarahcottiergallery.com
- **flag king_street_gallery_on_william: website redirects to https://kingstreetgallery.com.au/**
  - source: https://www.kingstreetgallery.com.au
- **flag curatorial_and_co: website redirects to https://curatorialandco.com/**
  - source: https://www.curatorialandco.com
- **flag nanda/hobbs: website redirects to https://nandahobbs.com/**
  - source: https://www.nandahobbs.com
- **flag 4a_centre_for_contemporary_asian_art: website redirects to https://4a.com.au/**
  - source: https://www.4a.com.au
- **flag cross_art_projects: website redirects to https://crossart.com.au/**
  - source: https://www.crossart.com.au
- **flag airspace_projects: website redirects to https://airspaceprojects.com/**
  - source: https://www.airspaceprojects.com
- **flag gaffa: website redirects to https://www.gaffa.com.au/**
  - source: https://gaffa.com.au
- **flag woollahra_gallery_at_redleaf: website redirects to https://www.woollahra.nsw.gov.au/Home**
  - source: https://www.woollahra.nsw.gov.au
- **flag martin_browne_contemporary: website redirects to https://martinbrownecontemporary.com/**
  - source: https://www.martinbrownecontemporary.com
- **flag tap: website redirects to https://www.tapgallery.org.au/**
  - source: https://tapgallery.org.au
- **flag gallery_144: website redirects to https://gallery144.com.au/**
  - source: https://www.gallery144.com.au/
- **flag michael_reid_sydney: website redirects to https://michaelreid.com.au/**
  - source: https://www.michaelreid.com.au
- **flag revolve_gallery_and_studios: website redirects to https://www.revolve.gallery**
  - source: https://revolve.gallery/

## Notes

- link check: 156 checked, 21 dead (0 blocked by robots.txt)
- review scanned 187 records
- enrich: 155 records visited, 206 field values proposed, 26 sites unreachable
- dedup: 5 pairs adjudicated, 1 duplicates proposed
- research: 43 search results, 18 already in the dataset
- research: 0 new art gallery records proposed
- fetcher: fetched=391, cached=6, blocked=6, failed=3
