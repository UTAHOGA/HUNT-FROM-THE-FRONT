# 2023 Moose Harvest Source Audit

Anchors the 2023 moose harvest CSV sources used for 2024 modeling.

## Source Result

- Harvest CSV files checked: 3
- Byte-identical active copies: 3
- Bull moose harvest codes: 36
- Antlerless moose harvest codes: 3
- Bull moose draw-only codes: ['MB6252']
- Bull moose harvest-only codes: ['MB6200', 'MB6209', 'MB6216', 'MB6217', 'MB6220', 'MB6254', 'MB6258']
- Antlerless moose draw/harvest mismatch count: 0

## Interpretation

- `MB6252` remains draw-only for 2023 harvest-vs-draw because it is not present in the 2023 moose harvest CSVs.
- Antlerless moose reconciles cleanly: all three MA draw codes have harvest rows.
- The seven bull-moose harvest-only codes are source evidence for 2023 harvest but are not in the standalone bull moose draw PDF code set.
- This step does not rewrite harvest truth, draw truth, permit numbers, runtime files, or website feeds.
