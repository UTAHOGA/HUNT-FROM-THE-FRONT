# 2023 Big Game Draw Odds Page Map

Anchors `23_bg-odds.pdf` for 2024 modeling and 2023 harvest-result comparison.

## Source Result

- PDF page count: 588
- Legacy/active PDF byte match: True
- Extracted rows from `23_bg-odds.pdf`: 35960
- Unique hunt codes in this source: 580
- Extracted PDF page coverage: 2-588

## Observed Extraction Map

| Section | PDF Pages | Rows | Codes | Species | Status |
|---|---:|---:|---:|---|---|
| Observed master species page | 1-1 | 0 | 0 | {} | NO_HUNT_CODE_ROWS_EXPECTED |
| Observed deer block | 2-191 | 11718 | 189 | {"Deer": 11718} | OBSERVED_CLEAN |
| Observed limited-entry elk block | 192-333 | 8804 | 142 | {"Elk": 8804} | OBSERVED_CLEAN |
| Observed any bull/CWMU elk block | 334-403 | 4278 | 69 | {"Elk": 4278} | OBSERVED_CLEAN |
| Observed buck pronghorn block | 404-490 | 5332 | 86 | {"Pronghorn": 5332} | OBSERVED_CLEAN |
| Observed O.I.L. block | 491-588 | 5828 | 94 | {"Bison": 1054, "Desert Bighorn Sheep": 992, "Moose": 1860, "Mountain Goat": 1054, "Rocky Mountain Bighorn Sheep": 868} | MIXED_EXTRACTION_ROWS |

## Harvest Comparison Linkage

- Source hunt codes matched to comparison: 580 / 580
- Comparison buckets: {'both': 579, 'draw_only': 1}
- Current 2026 active-database flags: {'NO': 39, 'YES': 541}
- Draw-only source codes: MB6252

## Interpretation

- The user-supplied page map is preserved in the CSV audit as source context.
- The observed physical PDF extraction map is the safer machine-validation layer because every extracted row carries `source_pdf_page`.
- This step does not rewrite draw truth, harvest truth, permit numbers, runtime files, or website feeds.
