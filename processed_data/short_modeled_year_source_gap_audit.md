# Short Modeled Year Source Gap Audit

Read-only search of local and official DWR source availability for modeled years 2021 and 2024.

## Result

- Source evidence rows: 26
- Local extraction-ready rows: 20
- Local harvest re-normalization rows: 3
- Runtime/database changes made: NO

## Modeled Year 2021

- Draw: normalized truth currently has one source label (`21_bg-odds.pdf`) and bonus-only rows, while local files include general deer, lifetime deer, dedicated hunter, antlerless, youth, sportsman, black bear, cougar, and turkey draw sources.
- Harvest: the value-bearing `harvest_results_2021_for_2022_all_long.csv` exists locally, but the current best-by-code 2021 normalized file has blank numeric metrics.

## Modeled Year 2024

- Draw: local 2023-for-2024 PDF/CSV packages include preference/youth/dedicated/turkey/cougar/sportsman families that are not fully represented in normalized 2024 draw truth.
- Harvest: 2024 harvest metrics are mostly populated, but local supplement files can fill richer features such as elk average age and black bear objectives.

## Official DWR Source Pages

- Big game draw odds: https://wildlife.utah.gov/biggame/odds
- Other species draw odds: https://wildlife.utah.gov/odds
- Harvest and survey reports: https://wildlife.utah.gov/biggame/reports
- Annual reports: https://wildlife.utah.gov/hunting/reports

## Same-Year Alignment 2021

- Status counts: {'HARVEST_ONLY_SAME_YEAR': 447, 'DRAW_ONLY_SAME_YEAR': 23}
- Harvest-only top species: [{'species': 'Antlerless Elk', 'count': 186}, {'species': 'Deer', 'count': 131}, {'species': 'Black Bear', 'count': 91}, {'species': 'Antlerless Deer', 'count': 27}, {'species': 'Rocky Mountain Bighorn Sheep', 'count': 5}, {'species': 'Desert Bighorn Sheep', 'count': 4}, {'species': 'Bison', 'count': 1}, {'species': 'Elk', 'count': 1}]
- Draw-only top species: [{'species': '', 'count': 23}]

## Same-Year Alignment 2024

- Status counts: {'HARVEST_ONLY_SAME_YEAR': 471, 'DRAW_ONLY_SAME_YEAR': 3}
- Harvest-only top species: [{'species': 'Antlerless Elk', 'count': 184}, {'species': 'Mule Deer', 'count': 148}, {'species': 'Black Bear', 'count': 87}, {'species': 'Antlerless Deer', 'count': 21}, {'species': 'Turkey', 'count': 7}, {'species': 'Elk', 'count': 6}, {'species': 'Rocky Mountain Bighorn Sheep', 'count': 6}, {'species': 'Desert Bighorn Sheep', 'count': 5}]
- Draw-only top species: [{'species': '', 'count': 3}]
