# 2023 Draw PDF Source Parity For 2024 Modeling

Compares the user-supplied 2023 draw-odds PDFs in `HUNTS` to the active `HUNT-BUILDER` copies.

## Source Result

- Expected/source PDFs: 17
- Byte-identical active copies: 17
- Missing legacy PDFs: 0
- Missing active PDFs: 0
- Active-only PDFs: 0
- Active duplicate hash groups: 0

## CSV Linkage

- Expected PDF labels represented by the two 2023-for-2024 CSV exports: 7 / 17
- CSV source labels not in expected PDF set: 0
- Expected PDF labels not represented by either CSV: 10

## Normalized Draw Truth Linkage

- Normalized draw-year/model-year 2024 rows: 37128
- Normalized draw-year/model-year 2024 hunt codes: 580
- Normalized source labels matching this expected PDF set: 0
- Normalized source label status: SOURCE_LABEL_LINEAGE_REVIEW

## Interpretation

- The full 17-PDF 2023 source package is byte-anchored in the active repo.
- The uploaded CSV exports use only part of that PDF set as direct `source_file` labels.
- Current normalized 2024 draw truth uses different `24_*` source labels, so lineage needs reconciliation before promotion.
- This audit does not extract PDF values, rewrite normalized draw truth, or publish runtime data.
