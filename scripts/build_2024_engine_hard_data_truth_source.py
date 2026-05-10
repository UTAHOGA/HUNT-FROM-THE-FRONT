from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


DRAW_INPUT = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/comprehensive_2024/2024_DRAW_RESULTS_COMPREHENSIVE_PERMITS_FIXED_WITH_OTC.csv"
)
HARVEST_INPUT = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/comprehensive_harvest_2024/2024_HARVEST_RESULTS_COMPREHENSIVE.csv"
)
OUT_DIR = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/truth_source_2024"
)

DRAW_OUT = OUT_DIR / "2024_DRAW_RESULTS_TRUTH_SOURCE.csv"
HARVEST_OUT = OUT_DIR / "2024_HARVEST_RESULTS_TRUTH_SOURCE.csv"
COVERAGE_OUT = OUT_DIR / "2024_ENGINE_HARD_DATA_TRUTH_SOURCE.csv"
REPORT_OUT = OUT_DIR / "2024_ENGINE_HARD_DATA_TRUTH_SOURCE_report.json"


DRAW_FAMILIES = {"big_game_master", "bear_draw_results", "antlerless_draw_results"}
OTC_FAMILY = "elk_general_season_otc_harvest_2024"


def clean_code(value: str) -> str:
    return (value or "").strip().upper()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def to_num(value: str) -> str:
    s = (value or "").strip().replace(",", "")
    if not s:
        return ""
    try:
        f = float(s)
    except ValueError:
        return ""
    if f.is_integer():
        return str(int(f))
    return str(round(f, 3))


def first_nonempty(row: dict[str, str], keys: list[str]) -> str:
    for k in keys:
        v = clean_text(row.get(k, ""))
        if v:
            return v
    return ""


def infer_species(row: dict[str, str], source_file: str) -> str:
    direct = first_nonempty(row, ["species", "Species", "species_or_category"])
    if direct:
        return direct
    path = source_file.lower()
    if "elk" in path:
        return "Elk"
    if "deer" in path:
        return "Deer"
    if "bear" in path:
        return "Black Bear"
    if "bison" in path:
        return "Bison"
    if "moose" in path:
        return "Moose"
    if "pronghorn" in path:
        return "Pronghorn"
    if "sheep" in path:
        return "Bighorn Sheep"
    if "goat" in path:
        return "Mountain Goat"
    if "turkey" in path:
        return "Turkey"
    return ""


def include_harvest_row(row: dict[str, str], source_file: str) -> bool:
    skip_tokens = [
        "crosscheck",
        "manifest",
        "cleanup",
        "match_report",
        "fill_20260510",
        "moves.csv",
        "extract_summary",
        "formatted_tables_cleanup",
    ]
    lower = source_file.lower()
    if any(t in lower for t in skip_tokens):
        return False

    harvest_signal_fields = [
        "Bull harvest",
        "buck_harvest",
        "Cow harvest",
        "Calf harvest",
        "Antlerless harvest",
        "antlerless_harvest",
        "Total harvest",
        "total_harvest",
        "Hunters afield",
        "hunters_afield",
        "Mean days hunted",
        "Success rate (%)",
    ]
    return any(clean_text(row.get(k, "")) for k in harvest_signal_fields)


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    draw_rows_raw = list(csv.DictReader(DRAW_INPUT.open("r", encoding="utf-8-sig", newline="")))
    harvest_rows_raw = list(csv.DictReader(HARVEST_INPUT.open("r", encoding="utf-8-sig", newline="")))

    draw_rows: list[dict[str, str]] = []
    harvest_rows: list[dict[str, str]] = []

    for row in draw_rows_raw:
        hunt_code = clean_code(row.get("hunt_code", ""))
        if not hunt_code:
            continue
        family = clean_text(row.get("dataset_family", ""))
        if family not in DRAW_FAMILIES and family != OTC_FAMILY:
            continue
        draw_rows.append(
            {
                "data_year": "2024",
                "record_type": "draw_results",
                "dataset_family": family,
                "hunt_code": hunt_code,
                "hunt_name": clean_text(row.get("hunt_name", "")),
                "species": clean_text(row.get("species_or_category", "")),
                "res_total_permits": to_num(row.get("res_total_permits", "")),
                "nr_total_permits": to_num(row.get("nr_total_permits", "")),
                "total_permits": to_num(row.get("total_permits", "")),
                "source_file": clean_text(row.get("source_file", "")),
                "source_page": clean_text(row.get("source_page", "")),
                "source_dataset": clean_text(row.get("source_dataset", "")),
                "parse_style": clean_text(row.get("parse_style", "")),
                "permit_semantics": "OTC_NO_DRAW_CAP" if family == OTC_FAMILY else "DRAW_PERMIT_TOTALS",
            }
        )

    for row in harvest_rows_raw:
        hunt_code = clean_code(first_nonempty(row, ["hunt_code", "hunt number", "Hunt number", "hunt_number"]))
        if not hunt_code:
            continue
        source_file = clean_text(row.get("source_file", ""))
        if not include_harvest_row(row, source_file):
            continue
        harvest_rows.append(
            {
                "data_year": "2024",
                "record_type": "harvest_results",
                "dataset_family": clean_text(row.get("source_dataset_group", "")),
                "hunt_code": hunt_code,
                "hunt_name": first_nonempty(row, ["hunt_name", "Hunt name", "Hunt name", "unit_name", "Unit name"]),
                "species": infer_species(row, source_file),
                "sex_type": first_nonempty(row, ["sex_type", "Sex_type", "Sex type"]),
                "weapon": first_nonempty(row, ["weapon", "Weapon"]),
                "hunt_type": first_nonempty(row, ["hunt_type", "Hunt_type", "Hunt type"]),
                "season": first_nonempty(row, ["season", "Season"]),
                "permits_reported": to_num(first_nonempty(row, ["Permits"])),
                "bull_harvest": to_num(first_nonempty(row, ["Bull harvest", "buck_harvest"])),
                "cow_harvest": to_num(first_nonempty(row, ["Cow harvest"])),
                "calf_harvest": to_num(first_nonempty(row, ["Calf harvest"])),
                "antlerless_harvest": to_num(first_nonempty(row, ["Antlerless harvest", "antlerless_harvest"])),
                "total_harvest": to_num(first_nonempty(row, ["Total harvest", "total_harvest"])),
                "hunters_afield": to_num(first_nonempty(row, ["Hunters afield", "hunters_afield"])),
                "mean_days_hunted": to_num(first_nonempty(row, ["Mean days hunted"])),
                "success_rate_percent": to_num(first_nonempty(row, ["Success rate (%)"])),
                "source_file": source_file,
                "source_page": first_nonempty(row, ["source_page", "Source page", "adobe_page"]),
                "source_row": clean_text(row.get("source_row", "")),
                "table_title": first_nonempty(row, ["table_title", "Page title"]),
            }
        )

    draw_fields = list(draw_rows[0].keys()) if draw_rows else []
    with DRAW_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=draw_fields)
        writer.writeheader()
        writer.writerows(draw_rows)

    harvest_fields = list(harvest_rows[0].keys()) if harvest_rows else []
    with HARVEST_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=harvest_fields)
        writer.writeheader()
        writer.writerows(harvest_rows)

    draw_by_code = defaultdict(list)
    for r in draw_rows:
        draw_by_code[r["hunt_code"]].append(r)
    harvest_by_code = defaultdict(list)
    for r in harvest_rows:
        harvest_by_code[r["hunt_code"]].append(r)

    all_codes = sorted(set(draw_by_code.keys()) | set(harvest_by_code.keys()))
    coverage_rows: list[dict[str, str]] = []
    for code in all_codes:
        d = draw_by_code.get(code, [])
        h = harvest_by_code.get(code, [])

        draw_permit_rows = [x for x in d if x["permit_semantics"] == "DRAW_PERMIT_TOTALS"]
        draw_otc_rows = [x for x in d if x["permit_semantics"] == "OTC_NO_DRAW_CAP"]
        draw_primary = draw_permit_rows[0] if draw_permit_rows else (d[0] if d else {})
        harvest_primary = h[0] if h else {}

        coverage_rows.append(
            {
                "data_year": "2024",
                "hunt_code": code,
                "has_draw_results": "1" if d else "0",
                "has_harvest_results": "1" if h else "0",
                "draw_rows": str(len(d)),
                "draw_permit_rows": str(len(draw_permit_rows)),
                "draw_otc_rows": str(len(draw_otc_rows)),
                "harvest_rows": str(len(h)),
                "draw_hunt_name_example": draw_primary.get("hunt_name", ""),
                "harvest_hunt_name_example": harvest_primary.get("hunt_name", ""),
                "species_example": draw_primary.get("species", "") or harvest_primary.get("species", ""),
                "res_total_permits_example": draw_primary.get("res_total_permits", ""),
                "nr_total_permits_example": draw_primary.get("nr_total_permits", ""),
                "total_permits_example": draw_primary.get("total_permits", ""),
                "total_harvest_example": harvest_primary.get("total_harvest", ""),
                "hunters_afield_example": harvest_primary.get("hunters_afield", ""),
                "success_rate_percent_example": harvest_primary.get("success_rate_percent", ""),
                "engine_join_status": (
                    "DRAW_AND_HARVEST"
                    if d and h
                    else ("DRAW_ONLY" if d else "HARVEST_ONLY")
                ),
            }
        )

    coverage_fields = list(coverage_rows[0].keys()) if coverage_rows else []
    with COVERAGE_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=coverage_fields)
        writer.writeheader()
        writer.writerows(coverage_rows)

    species_counter = Counter(r["species"] for r in harvest_rows if r.get("species"))
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "draw": str(DRAW_INPUT).replace("\\", "/"),
            "harvest": str(HARVEST_INPUT).replace("\\", "/"),
        },
        "outputs": {
            "draw_truth_source": str(DRAW_OUT).replace("\\", "/"),
            "harvest_truth_source": str(HARVEST_OUT).replace("\\", "/"),
            "engine_hard_data_truth_source": str(COVERAGE_OUT).replace("\\", "/"),
        },
        "counts": {
            "draw_rows_kept": len(draw_rows),
            "draw_unique_hunt_codes": len(draw_by_code),
            "harvest_rows_kept": len(harvest_rows),
            "harvest_unique_hunt_codes": len(harvest_by_code),
            "coverage_unique_hunt_codes": len(all_codes),
            "coverage_draw_and_harvest": sum(1 for r in coverage_rows if r["engine_join_status"] == "DRAW_AND_HARVEST"),
            "coverage_draw_only": sum(1 for r in coverage_rows if r["engine_join_status"] == "DRAW_ONLY"),
            "coverage_harvest_only": sum(1 for r in coverage_rows if r["engine_join_status"] == "HARVEST_ONLY"),
        },
        "harvest_species_counts": dict(species_counter),
    }
    REPORT_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {DRAW_OUT}")
    print(f"Wrote {HARVEST_OUT}")
    print(f"Wrote {COVERAGE_OUT}")
    print(f"Wrote {REPORT_OUT}")
    print(json.dumps(report["counts"], indent=2))


if __name__ == "__main__":
    build()
