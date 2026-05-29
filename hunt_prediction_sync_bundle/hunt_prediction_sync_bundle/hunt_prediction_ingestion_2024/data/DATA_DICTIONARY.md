# Hunt Prediction Engine - 2024 Ingestion Package

## Row counts
- `big_game_draw_point_level`: 37618
- `big_game_draw_hunt_totals`: 1122
- `black_bear_draw_point_level`: 4312
- `black_bear_draw_hunt_totals`: 196
- `black_bear_bonus_point_purchases`: 32
- `sportsman_draw_odds_2025`: 10
- `annual_report_key_metrics`: 13
- `mule_deer_statewide_harvest_history`: 100

## Files created
- `big_game_draw_point_level.csv`
- `big_game_draw_hunt_totals.csv`
- `black_bear_draw_point_level.csv`
- `black_bear_draw_hunt_totals.csv`
- `black_bear_bonus_point_purchases.csv`
- `sportsman_draw_odds_2025.csv`
- `annual_report_key_metrics.csv`
- `mule_deer_statewide_harvest_history.csv`
- `hunt_engine_ingestion_2024.json`
- `raw_text/*.txt` page-layout text for audit and secondary extraction

## Obtainable data parameters
- `draw`: Draw label/year
- `source_file/page`: PDF provenance
- `entity_type`: hunt or species_summary
- `hunt_code`: DWR hunt code
- `hunt_title`: Original DWR hunt title
- `hunt_name`: Parsed hunt class/name
- `unit`: Parsed hunt unit
- `weapon`: Parsed weapon/season type
- `species`: Species/category summary when present
- `residency`: Resident/nonresident applicant pool
- `bonus_points`: Applicant bonus point tier
- `eligible_applicants`: Applicants in pool/tier
- `bonus_permits`: Permits issued in bonus phase
- `regular_permits`: Permits issued in regular/random phase
- `total_permits`: Total permits issued
- `success_odds_1_in`: Numeric odds denominator
- `success_probability`: 1 / odds denominator where odds present
- `resident_applicants/nonresident_applicants`: Bonus point purchase counts
- `quota/success fields`: Sportsman quota and applicant outcomes
- `harvest/mortality/pursuit metrics`: Annual report extracted management indicators
- `mule deer historical harvest`: Statewide time-series fields: buck harvest, antlerless harvest, total harvest, hunters afield

## Ingestion notes
- Primary prediction table: point-level draw odds by hunt, residency, and bonus points.
- Aggregate response table: hunt totals by residency.
- Normalize DWR hunt unit names before joining annual report harvest/population indicators.
- Keep resident and nonresident pools separate.
- Treat `N/A` odds as null/missing, not zero probability.
- Validate long or wrapped names before production use.