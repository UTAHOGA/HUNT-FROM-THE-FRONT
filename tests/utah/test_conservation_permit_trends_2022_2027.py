import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = REPO_ROOT / "data_truth" / "permit_overlay_truth" / "normalized"
DETAIL_CSV = NORMALIZED_DIR / "conservation_permit_cycle_rows_2022_2027.csv"
SPECIES_TREND_CSV = NORMALIZED_DIR / "conservation_permit_trends_by_species_2022_2027.csv"
GROUP_TREND_CSV = NORMALIZED_DIR / "conservation_permit_trends_by_group_2022_2027.csv"
SUMMARY_JSON = NORMALIZED_DIR / "conservation_permit_trends_2022_2027_summary.json"
REPORT_MD = REPO_ROOT / "processed_data" / "conservation_permit_trends_2022_2027.md"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_conservation_permit_trend_outputs_exist():
    assert DETAIL_CSV.exists()
    assert SPECIES_TREND_CSV.exists()
    assert GROUP_TREND_CSV.exists()
    assert SUMMARY_JSON.exists()
    assert REPORT_MD.exists()


def test_conservation_permit_trend_summary_reconciles():
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))

    assert summary["classification"] == "CONSERVATION_PERMIT_TREND_MODEL_2022_2027"
    assert summary["guardrail"] == "TREND_MODEL_ONLY_DO_NOT_USE_AS_DRAW_ODDS_OR_HARVEST_RESULTS"
    assert summary["validation"]["status"] == "PASS"
    assert summary["cycle_totals"]["2022_2024"] == 318
    assert summary["cycle_totals"]["2025_2027"] == 336
    assert summary["cycle_totals"]["cycle_change"] == 18
    assert summary["cycle_totals"]["pct_change"] == 5.66


def test_conservation_permit_detail_rows_reconcile_to_cycles():
    rows = read_csv(DETAIL_CSV)

    assert len(rows) == 589
    assert sum(int(row["permit_count"]) for row in rows if row["cycle"] == "2022-2024") == 318
    assert sum(int(row["permit_count"]) for row in rows if row["cycle"] == "2025-2027") == 336
    assert sum(row["discontinued_flag"] == "True" for row in rows if row["cycle"] == "2022-2024") == 6


def test_conservation_permit_dimension_trends_reconcile():
    species = read_csv(SPECIES_TREND_CSV)
    groups = read_csv(GROUP_TREND_CSV)

    assert sum(int(row["permits_2022_2024"]) for row in species) == 318
    assert sum(int(row["permits_2025_2027"]) for row in species) == 336
    assert sum(int(row["permits_2022_2024"]) for row in groups) == 318
    assert sum(int(row["permits_2025_2027"]) for row in groups) == 336

    elk = next(row for row in species if row["key"] == "Elk")
    assert int(elk["permits_2022_2024"]) == 100
    assert int(elk["permits_2025_2027"]) == 111
    assert int(elk["cycle_change"]) == 11
