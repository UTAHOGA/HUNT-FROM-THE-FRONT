# Historical LE -> EB Normalization (2024)

Current public limited-entry family is **EB**. Historical **LE** rows are preserved and cross-mapped to EB candidates for audit and migration.

- Source rows: 17
- AUTO_MATCH_BOUNDARY_WEAPON: 2
- MULTI_BOUNDARY_WEAPON: 9
- NO_EB_CANDIDATE: 6

Files:
- C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\historical_le_to_eb_crosswalk_2024.csv
- C:\Users\tyler\Desktop\GitHub\HUNTS\processed_data\historical_le_to_eb_crosswalk_2024.json
- C:\Users\tyler\Desktop\GitHub\HUNTS\data\hunt-master-canonical-2026-historical-le-to-eb-crosswalk.csv
- C:\Users\tyler\Desktop\GitHub\HUNTS\data\hunt-master-canonical-2026-historical-le-to-eb-crosswalk.json

## Code-family verification (from 2026 DATABASE.csv)

- **EB**: current public elk codes (includes public limited-entry elk)
- **EL**: limited-entry private-land-only elk family
- **LO**: landowner/private-land code family (mixed species, includes some elk/deer private-land-only rows)

This normalization keeps historical source `LE` values intact for audit and adds `EB` candidates as crosswalk guidance only.

## Private-land normalization note

For historical 2024 `LE` private-land rows, owner-reviewed mappings may normalize to the current `EL` private-land family (not `EB`) when that is the correct live code family match.
