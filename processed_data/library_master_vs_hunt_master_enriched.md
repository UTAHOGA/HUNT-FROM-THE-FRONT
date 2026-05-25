# Library Master vs Hunt Master Enriched

- Status: `REVIEW_REQUIRED`
- Library rows: `328`
- Library reconciled hunt codes: `147`
- Hunt master rows: `54357`
- Hunt master unique hunt codes: `1471`
- Library codes found in hunt master: `147`
- Library codes missing from hunt master: `0`
- Field mismatch rows: `191`

## Compare Status Counts

- `DOCUMENT_ROW_NOT_HUNT_CODED`: `10`
- `FOUND_ALIGNED`: `31`
- `FOUND_FIELD_MISMATCH`: `191`
- `FOUND_PRIOR_REVIEW_REQUIRED`: `96`

## Field Mismatch Counts

- `database_hunt_name->hunt_name`: `25`
- `database_permit_allotment_2026_nr->permit_allotment_2026_nr`: `12`
- `database_permit_allotment_2026_res->permit_allotment_2026_res`: `12`
- `database_permit_allotment_2026_source->permit_allotment_2026_source`: `23`
- `database_permit_allotment_2026_source_file->permit_allotment_2026_source_file`: `23`
- `database_permit_allotment_2026_status->permit_allotment_2026_status`: `23`
- `database_permit_allotment_2026_total->permit_allotment_2026_total`: `13`
- `database_permits_2026_nr->permits_2026_nr`: `12`
- `database_permits_2026_res->permits_2026_res`: `12`
- `database_permits_2026_source->permits_2026_source`: `191`
- `database_permits_2026_total->permits_2026_total`: `13`
- `database_weapon->weapon`: `1`

The detailed row-level comparison is in `processed_data/library_master_vs_hunt_master_enriched.csv`.
