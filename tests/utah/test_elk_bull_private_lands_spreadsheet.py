import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_CSV = REPO_ROOT / "processed_data" / "elk_bull_private_lands_hunt_planner_reference.csv"
OUTPUT_XLSX = REPO_ROOT / "processed_data" / "elk_bull_private_lands_hunt_planner_reference.xlsx"
OUTPUT_REPORT = REPO_ROOT / "processed_data" / "elk_bull_private_lands_hunt_planner_reference_report.json"


REQUIRED_HEADERS = [
    "Hunt Name",
    "Hunt Code",
    "Sex",
    "Species",
    "Weapon",
    "Hunt Type",
    "Season",
    "Non Res",
    "Res",
    "Total",
    "Source Authority",
    "Permit Status",
    "Data Status",
    "Notes",
]


def read_rows():
    with OUTPUT_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_elk_bull_private_lands_outputs_exist():
    assert OUTPUT_CSV.exists()
    assert OUTPUT_XLSX.exists()
    assert OUTPUT_REPORT.exists()


def test_elk_bull_private_lands_headers_and_counts():
    rows = read_rows()

    assert rows
    assert list(rows[0].keys()) == REQUIRED_HEADERS
    assert len(rows) == 131
    assert sum(row["Hunt Code"].startswith("EL") for row in rows) == 126
    assert sum(row["Hunt Code"].startswith("LO") for row in rows) == 5
    assert len({row["Hunt Code"] for row in rows}) == 131


def test_elk_bull_private_lands_quota_columns_are_blank():
    rows = read_rows()

    assert all(row["Non Res"] == "" for row in rows)
    assert all(row["Res"] == "" for row in rows)
    assert all(row["Total"] == "" for row in rows)
    assert all(row["Source Authority"] == "Utah DWR Hunt Planner" for row in rows)
    assert all(row["Permit Status"] == "NO_QUOTA_PUBLISHED" for row in rows)
