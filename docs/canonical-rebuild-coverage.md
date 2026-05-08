# Canonical Rebuild Coverage

Generated: 2026-05-08T07:47:18.215Z

## Scope

- Hunt Planner
- Hunt Research
- Hard Copies
- Outfitter Verification

## Source Files Scanned

| File | Kind | Rows/Bytes | Fields |
| --- | --- | --- | --- |
| index.html | html | 24545 |  |
| research.html | html | 39855 |  |
| hard-copy.html | html | 22390 |  |
| verify.html | html | 19165 |  |
| config.js | js | 21281 |  |
| app.js | js | 221425 |  |
| data.js | js | 20854 |  |
| boundary-resolver.js | js | 13300 |  |
| hunt-research.js | js | 48484 |  |
| ui.js | js | 31335 |  |
| header-layout.js | js | 28147 |  |
| google-basemap.js | js | 7106 |  |
| map-engine.js | js | 10290 |  |
| style.css | css | 36718 |  |
| data/hunt-master-canonical-2026-foundation.json | json | 1288 | access_type, avg_days_2025, avg_points_2025, boundaryId, boundary_id, boundary_id_numeric, boundary_token, code, data_status, draw_2025_bg_pdf_page, draw_2025_bg_report_page, draw_2025_species_section, draw_2025_type, draw_family, eligibility_class, harvest_2025, has_antlerless_draw, has_bonus_draw, has_harvest, huntCode, hunt_class, hunt_code, hunt_name, hunt_type |
| data/hunt-master-canonical-2026-database-candidate.json | json | 1394 | NOTES, access_type, avg_days_2025, avg_points_2025, boundaryId, boundary_id, boundary_id_numeric, boundary_token, code, data_status, draw_2025_bg_pdf_page, draw_2025_bg_report_page, draw_2025_species_section, draw_2025_type, draw_family, eligibility_class, harvest_2025, has_antlerless_draw, has_bonus_draw, has_harvest, huntCode, hunt_class, hunt_code, hunt_name |
| data/hunt-master-canonical-2026-source-of-truth.json | json | 1288 | access_type, avg_days_2025, avg_points_2025, boundary_id, data_status, draw_2025_bg_pdf_page, draw_2025_bg_report_page, draw_2025_species_section, draw_2025_type, draw_family, eligibility_class, harvest_2025, has_antlerless_draw, has_bonus_draw, has_harvest, hunt_class, hunt_code, hunt_name, hunt_type, hunters_2025, permit_allocation_type, permit_note, permit_overlay_source, permit_source_authority |
| processed_data/draw_reality_engine.csv | csv | 73174 | hunt_code, residency, points, public_permits_2025, public_permits_2026, public_permits_2026_source, max_point_permits_2025, max_point_permits_2026, random_permits_2025, random_permits_2026, guaranteed_at_2025, guaranteed_at_2026, permit_delta_2025_to_2026, projected_applicants_2026_source, guaranteed_delta_2025_to_2026, applicants_above, applicants_at_level, random_draw_odds_2026, gap, delta_gap, status, trend, draw_outlook, permits_2026_res |
| processed_data/point_ladder_view.csv | csv | 73174 | hunt_code, residency, points, odds_2025_actual, odds_2026_projected, guaranteed_marker, user_point_marker, permits_2026_res, permits_2026_nr, permits_2026_total, permits_2026_source |
| processed_data/hunt_master_enriched.csv | csv | 53782 | hunt_code, species, hunt_name, weapon, hunt_type, access_type, residency, points, public_permits_2025, public_permits_2026, public_permits_2026_source, applicants_2025, projected_applicants_2026, projected_applicants_2026_source, odds_2025, odds_2026_projected, max_point_permits_2026, random_permits_2026, success_hunters, success_harvest, success_percent, missing_draw_data, missing_projection, missing_permits |
| processed_data/hunt_unit_reference_linked.csv | csv | 2668 | hunt_code, residency, hunt_name, species, weapon, hunt_type, access_type, public_permits_2025, public_permits_2026, permits_2025_res, permits_2025_nr, permits_2025_total, permits_2026_res, permits_2026_nr, permits_2026_total, applicants_2025, projected_applicants_2026, max_point_permits_2026, random_permits_2026, guaranteed_at_2026, delta_gap, trend, coverage_status, coverage_reason |
| processed_data/display-boundary-index-2026.json | json | 1288 | boundary_geojson_path, boundary_geometry_type, boundary_kml_path, boundary_kmz_path, display_boundary_id, dwr_boundary_id, dwr_boundary_link, dwr_member_boundary_ids, geometry_status, hunt_code, member_boundary_count, merged_boundary_id |
| processed_data/boundary-manifest-2026.json | json | 26 | boundary_geojson_path, boundary_geometry_type, boundary_id, boundary_kml_path, boundary_kmz_path, geometry_status, hunt_code, member_boundary_count, member_boundary_ids, merged_boundary_id, notes, placemark_count, sha256, source_filename |
| processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json | json | 351 | group, href, subtitle, title, type, year |
| data/outfitters-public.json | json | 0 |  |
| data/outfitters.json | json | 11 | blmDistricts, certLevel, city, email, listingName, listingType, logoUrl, notes, ownerName, phone, region, speciesServed, unitsServed, usfsForests, verificationStatus, website |
| processed_data/outfitter-federal-unit-coverage-review.json | json | 761 | BlmAuthoritySource, BlmPermitMatchedOutfitterCount, BlmPermitMatchedOutfitters, ExampleHuntCodes, ExclusionReason, FederalCoverageEligible, FederalPermitMatchedOutfitterCount, FederalPermitMatchedOutfitters, HuntCount, Notes, PrimaryBlmDistrictId, PrimaryBlmDistrictName, PrimaryUsfsForestId, PrimaryUsfsForestName, Species, UnitCode, UnitName, UsfsAuthoritySource, UsfsPermitMatchedOutfitterCount, UsfsPermitMatchedOutfitters |

## Fields Discovered

- Total discovered field entries: 432
- Mapped: 432
- Intentionally unmapped: 0
- Deprecated: 0

## Fields Mapped

See [canonical-field-usage-map.md](./canonical-field-usage-map.md) and [canonical/canonical-field-usage-map.json](../canonical/canonical-field-usage-map.json).

## Fields Intentionally Unmapped

None.

## Deprecated Fields

None.

## Owner Questions

| ID | Question | Status |
| --- | --- | --- |
| owner-hard-copy-categories | Confirm whether Hard Copies should remain PDF-only or include CSV/XLSX downloads later. | needs_owner_input |
| owner-outfitter-cpo-threshold | Confirm the owner-approved threshold for C.P.O. designation before automating verification labels. | needs_owner_input |

## Source-Needed Regulation/Legal Items

| ID | Item | URL | Status |
| --- | --- | --- | --- |
| source-utah-dwr-outfitter-registration | Utah DWR outfitter registration floor and public-resource language. | https://wildlife.utah.gov/guide/outfitter.html | source_needed |
| source-regulatory-disclaimer | Verification disclaimer: not a license, permit grant, land-access guarantee, agency authorization, or legal determination. |  | source_needed |

## Generated Page Data

- generated/pages/hunt-planner.json
- generated/pages/hunt-research.json
- generated/pages/hard-copies.json
- generated/pages/outfitter-verification.json

## Validation Commands

- npm run generate:page-data
- npm run validate:canonical
- npm run compare:runtime-contracts
- npm run promotion:safety
- npm run test
- npm run build

## Test Results

Pending until validation commands are run after generation.
