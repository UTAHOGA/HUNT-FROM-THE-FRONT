# 2026 Big Game Hunt Code Reconciliation

This checks hunt-code presence from the corrected 2026 Big Game Application Guidebook against the core source/database/runtime reference surfaces.

## Result

- Guidebook hunt codes checked: `728`
- Required-surface blocker count: `0`
- Codes present in every required surface: `728`
- Optional predictive rows missing: `44`
- Extra DATABASE codes not in guidebook: `683`

Required surfaces: `DATABASE.csv`, `hunt_master_enriched.csv`, `hunt_unit_reference_linked.csv`, `point_ladder_view.csv`, `draw_reality_engine.csv`.

Optional predictive surface: `draw_reality_engine_predictive_v2.csv`. Missing optional rows are coverage notes, not source-code reconciliation blockers.

## Required Blockers

None. All guidebook hunt codes are present in every required surface.

## Optional Predictive Coverage Notes

| hunt_code | guidebook hunt name | missing optional surfaces |
|---|---|---|
| BI6539 | Henry Mtns (new) | draw_reality_engine_predictive_v2 |
| DB0008 | Deer extended archery only | draw_reality_engine_predictive_v2 |
| DB1109 | Thousand Lakes | draw_reality_engine_predictive_v2 |
| DB1121 | Antelope Island (any legal weapon) (new) | draw_reality_engine_predictive_v2 |
| DB1599 | Chalk Creek | draw_reality_engine_predictive_v2 |
| DB1600 | Chalk Creek | draw_reality_engine_predictive_v2 |
| DB1601 | Chalk Creek | draw_reality_engine_predictive_v2 |
| DB1602 | Chalk Creek | draw_reality_engine_predictive_v2 |
| DB1603 | East Canyon | draw_reality_engine_predictive_v2 |
| DB1604 | East Canyon | draw_reality_engine_predictive_v2 |
| DB1605 | East Canyon | draw_reality_engine_predictive_v2 |
| DB1606 | East Canyon | draw_reality_engine_predictive_v2 |
| DB1607 | Morgan-South Rich | draw_reality_engine_predictive_v2 |
| DB1608 | Morgan-South Rich | draw_reality_engine_predictive_v2 |
| DB1609 | Morgan-South Rich | draw_reality_engine_predictive_v2 |
| DB1610 | Morgan-South Rich | draw_reality_engine_predictive_v2 |
| DB1611 | Beaver, East | draw_reality_engine_predictive_v2 |
| DB1612 | Beaver, East | draw_reality_engine_predictive_v2 |
| DB1613 | Beaver, East | draw_reality_engine_predictive_v2 |
| DB1614 | Beaver, West | draw_reality_engine_predictive_v2 |
| DB1615 | Beaver, West | draw_reality_engine_predictive_v2 |
| DB1616 | Beaver, West | draw_reality_engine_predictive_v2 |
| DB1617 | West Desert, Swasey | draw_reality_engine_predictive_v2 |
| DB1618 | West Desert, Swasey | draw_reality_engine_predictive_v2 |
| DB1619 | West Desert, Swasey | draw_reality_engine_predictive_v2 |
| DB1620 | Oquirrh/Tintic | draw_reality_engine_predictive_v2 |
| DB1621 | Oquirrh/Tintic | draw_reality_engine_predictive_v2 |
| DB1622 | Oquirrh/Tintic | draw_reality_engine_predictive_v2 |
| DB1623 | Cedar/Stansbury | draw_reality_engine_predictive_v2 |
| DB1624 | Cedar/Stansbury | draw_reality_engine_predictive_v2 |
| DB1625 | Cedar/Stansbury | draw_reality_engine_predictive_v2 |
| DB1627 | Cache | draw_reality_engine_predictive_v2 |
| DB1628 | Cache | draw_reality_engine_predictive_v2 |
| DB1629 | Boulder/Kaiparowits | draw_reality_engine_predictive_v2 |
| DB1630 | Boulder/Kaiparowits | draw_reality_engine_predictive_v2 |
| DB1631 | Box Elder | draw_reality_engine_predictive_v2 |
| DB1799 | Chalk Creek | draw_reality_engine_predictive_v2 |
| DB1800 | East Canyon | draw_reality_engine_predictive_v2 |
| DB1801 | Morgan-South Rich | draw_reality_engine_predictive_v2 |
| DB1802 | Beaver, East | draw_reality_engine_predictive_v2 |
| DB1803 | Beaver, West | draw_reality_engine_predictive_v2 |
| DB1804 | Cedar/Stansbury | draw_reality_engine_predictive_v2 |
| DB1805 | Oquirrh/Tintic | draw_reality_engine_predictive_v2 |
| DB1806 | West Desert, Swasey | draw_reality_engine_predictive_v2 |

Full row-level output: `processed_data/2026_big_game_hunt_code_reconciliation.csv`
