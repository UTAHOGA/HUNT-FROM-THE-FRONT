# 2023 Draw CSV Source Parity For 2024 Modeling

Compares two large 2023-for-2024 draw-result CSV exports from `HUNTS` to active `HUNT-BUILDER` copies.

## Source Result

- Expected CSVs: 2
- Byte-identical active copies: 2
- Missing legacy CSVs: 0
- Missing active CSVs: 0

## File Shape

- Standard long rows / codes: 35960 / 580
- Uploaded combined rows / codes: 38682 / 593
- Standard source files represented: 1
- Uploaded combined source files represented: 6
- Source row-key overlap between the two CSVs: 11718
- Standard-only row keys: 24242
- Uploaded-combined-only row keys: 26964

## Normalized Draw Truth Comparison

- Current normalized model-year/draw-year 2024 rows / codes: 37128 / 580
- Standard long vs normalized 2024 hunt-code overlap: 558
- Uploaded combined vs normalized 2024 hunt-code overlap: 181
- Standard long vs normalized 2024 row-key overlap: 21416
- Uploaded combined vs normalized 2024 row-key overlap: 8011

## Interpretation

- Both source CSVs are already present in the active repo as exact byte matches.
- The standard file is a single-source bonus-style export; the uploaded combined file includes multiple source classes and preference-style rows.
- These files are source evidence and are not being promoted into normalized draw truth in this step.
- The overlap report shows that the current normalized 2024 draw truth is not a simple byte/row-key copy of either CSV, so any future promotion needs an explicit reconciliation step.
