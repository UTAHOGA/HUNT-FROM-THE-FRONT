"""Build a cumulative 2026 RAC permit table and compare it to DATABASE.csv."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRUTH_ROOT = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv"
PROCESSED_ROOT = ROOT / "processed_data"
DATABASE_PATH = TRUTH_ROOT / "DATABASE.csv"

CUMULATIVE_CSV = PROCESSED_ROOT / "all_rac_2026_permits_cumulative.csv"
CUMULATIVE_JSON = PROCESSED_ROOT / "all_rac_2026_permits_cumulative.json"
COMPARE_CSV = PROCESSED_ROOT / "all_rac_2026_permits_vs_DATABASE.csv"
COMPARE_JSON = PROCESSED_ROOT / "all_rac_2026_permits_vs_DATABASE.json"
COMPARE_MD = PROCESSED_ROOT / "all_rac_2026_permits_vs_DATABASE.md"

EXCLUDED_RAC_FILE_TOKENS = (
    "metadata",
    "comparison",
    "verification",
    "supplemental",
    "control_units",
    "permit_rows_from_pdf",
)

OUTPUT_FIELDS = [
    "source_file",
    "source_row_number",
    "rac_family",
    "allocation_scope",
    "hunt_code",
    "hunt_codes_raw",
    "hunt_name",
    "permit_group",
    "category",
    "species",
    "weapon",
    "sex_type",
    "season_dates_2026",
    "permits_2025_res",
    "permits_2025_nr",
    "permits_2025_total",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permits_2025_text",
    "permits_2026_text",
    "source_document",
    "source_note",
]

COMPARE_FIELDS = OUTPUT_FIELDS + [
    "db_hunt_name",
    "db_species",
    "db_weapon",
    "db_hunt_type",
    "db_season",
    "db_permits_2026_res",
    "db_permits_2026_nr",
    "db_permits_2026_total",
    "db_permits_year_res",
    "db_permits_year_nr",
    "db_permits_year_total",
    "comparison_status",
    "comparison_detail",
    "delta_res",
    "delta_nr",
    "delta_total",
    "significant_difference",
]


FAMILY_SPECIES = {
    "antlerless_deer": "Deer",
    "antlerless_elk": "Elk",
    "antlerless_moose": "Moose",
    "buck_deer": "Deer",
    "doe_pronghorn": "Pronghorn",
    "ewe_rocky_mountain_bighorn_sheep": "Rocky Mountain Bighorn Sheep",
    "general_season_bull_elk": "Elk",
    "limited_entry_buck_pronghorn": "Pronghorn",
    "limited_entry_bull_elk": "Elk",
    "oial_bison": "Bison",
    "oial_bull_moose": "Moose",
    "oial_desert_bighorn_sheep": "Desert Bighorn Sheep",
    "oial_mountain_goat": "Mountain Goat",
    "oial_rocky_mountain_bighorn_sheep": "Rocky Mountain Bighorn Sheep",
    "private_lands_only_antlerless_elk": "Elk",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("\ufeff", "")


def to_int(value: object) -> int | None:
    text = clean(value).replace(",", "")
    if not text or text in {"-", "–", "—"}:
        return None
    if text.lower() == "unlimited":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def family_from_file(path: Path) -> str:
    name = path.stem
    if not name.startswith("2026_rac_"):
        return name
    return name.removeprefix("2026_rac_").removesuffix("_permits")


def species_from_family(family: str, row: dict[str, str]) -> str:
    if clean(row.get("species")):
        return clean(row.get("species"))
    for token, species in FAMILY_SPECIES.items():
        if token in family:
            return species
    return ""


def rac_source_files() -> list[Path]:
    files = []
    for path in sorted(TRUTH_ROOT.glob("2026_rac_*.csv")):
        lower = path.name.lower()
        if any(token in lower for token in EXCLUDED_RAC_FILE_TOKENS):
            continue
        files.append(path)
    return files


def normalize_row(path: Path, row_number: int, row: dict[str, str]) -> list[dict[str, str]]:
    family = family_from_file(path)
    hunt_codes_raw = clean(row.get("hunt_codes")) or clean(row.get("hunt_code"))
    codes = [code.strip() for code in hunt_codes_raw.split("|") if code.strip()] if hunt_codes_raw else [""]

    if not clean(row.get("hunt_code")) and clean(row.get("hunt_codes")):
        allocation_scope = "CATEGORY_SHARED_HUNT_CODES"
    elif not hunt_codes_raw:
        allocation_scope = "UNIT_LEVEL_NO_HUNT_CODE"
    elif clean(row.get("permits_2026_res")) or clean(row.get("permits_2026_nr")):
        allocation_scope = "HUNT_CODE_RES_NR_SPLIT"
    elif clean(row.get("permits_2026_total")) or clean(row.get("permits_2026_numeric")):
        allocation_scope = "HUNT_CODE_TOTAL_ONLY"
    else:
        allocation_scope = "HUNT_CODE_TEXT_OR_STATUS_ONLY"

    normalized = []
    for code in codes:
        permit_group = clean(row.get("permit_group"))
        hunt_name = clean(row.get("hunt_name")) or permit_group or clean(row.get("general_season_unit")) or clean(row.get("category"))
        permits_2025_total = clean(row.get("permits_2025_total")) or clean(row.get("permits_2025_numeric"))
        permits_2026_total = clean(row.get("permits_2026_total")) or clean(row.get("permits_2026_numeric")) or clean(row.get("permits_2026"))
        normalized.append(
            {
                "source_file": str(path.relative_to(ROOT)),
                "source_row_number": str(row_number),
                "rac_family": family,
                "allocation_scope": allocation_scope,
                "hunt_code": code,
                "hunt_codes_raw": hunt_codes_raw,
                "hunt_name": hunt_name,
                "permit_group": permit_group,
                "category": clean(row.get("category")),
                "species": species_from_family(family, row),
                "weapon": clean(row.get("weapon")),
                "sex_type": clean(row.get("sex_type")),
                "season_dates_2026": clean(row.get("season_dates_2026")),
                "permits_2025_res": clean(row.get("permits_2025_res")),
                "permits_2025_nr": clean(row.get("permits_2025_nr")),
                "permits_2025_total": permits_2025_total,
                "permits_2026_res": clean(row.get("permits_2026_res")),
                "permits_2026_nr": clean(row.get("permits_2026_nr")),
                "permits_2026_total": permits_2026_total,
                "permits_2025_text": clean(row.get("permits_2025_text")),
                "permits_2026_text": clean(row.get("permits_2026_text")),
                "source_document": clean(row.get("source_document")),
                "source_note": clean(row.get("source_note")),
            }
        )
    return normalized


def build_cumulative() -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    source_counts: dict[str, int] = {}
    for path in rac_source_files():
        raw_rows = read_csv(path)
        source_counts[str(path.relative_to(ROOT))] = len(raw_rows)
        for idx, row in enumerate(raw_rows, start=2):
            rows.extend(normalize_row(path, idx, row))
    return rows, source_counts


def database_index() -> dict[str, dict[str, str]]:
    return {clean(row.get("hunt_code")): row for row in read_csv(DATABASE_PATH) if clean(row.get("hunt_code"))}


def compare_row(row: dict[str, str], db: dict[str, dict[str, str]]) -> dict[str, str]:
    out = dict(row)
    code = clean(row.get("hunt_code"))
    db_row = db.get(code)
    for field in [
        "hunt_name",
        "species",
        "weapon",
        "hunt_type",
        "season",
        "permits_2026_res",
        "permits_2026_nr",
        "permits_2026_total",
        "permits_year_res",
        "permits_year_nr",
        "permits_year_total",
    ]:
        out[f"db_{field}"] = clean(db_row.get(field)) if db_row else ""

    if not code:
        status = "NO_HUNT_CODE_IN_RAC_ROW"
        detail = "RAC row is unit/category level and cannot be joined to DATABASE.csv by hunt_code."
    elif not db_row:
        status = "MISSING_IN_DATABASE"
        detail = "RAC hunt_code was not found in DATABASE.csv."
    elif row["allocation_scope"] == "CATEGORY_SHARED_HUNT_CODES":
        status = "CATEGORY_LEVEL_PRESENT_IN_DATABASE"
        detail = "RAC category total applies to multiple hunt_codes; individual DATABASE rows are present but not directly comparable row-by-row."
    else:
        rac_res = to_int(row.get("permits_2026_res"))
        rac_nr = to_int(row.get("permits_2026_nr"))
        rac_total = to_int(row.get("permits_2026_total"))
        db_res = to_int(db_row.get("permits_2026_res"))
        db_nr = to_int(db_row.get("permits_2026_nr"))
        db_total = to_int(db_row.get("permits_2026_total"))

        if rac_res is not None or rac_nr is not None:
            res_match = rac_res == db_res
            nr_match = rac_nr == db_nr
            total_match = rac_total == db_total
            if res_match and nr_match and total_match:
                status = "MATCH"
                detail = "RAC resident/nonresident/total values match DATABASE.csv."
            elif total_match and (db_res is None or db_nr is None):
                status = "TOTAL_MATCH_DATABASE_SPLIT_MISSING"
                detail = "RAC total matches DATABASE.csv, but DATABASE.csv does not carry the full split."
            else:
                status = "MISMATCH_RES_NR_TOTAL"
                detail = "RAC resident/nonresident and/or total values differ from DATABASE.csv."
        elif rac_total is not None:
            if rac_total == db_total:
                status = "MATCH_TOTAL"
                detail = "RAC total-only value matches DATABASE.csv total."
            else:
                status = "MISMATCH_TOTAL"
                detail = "RAC total-only value differs from DATABASE.csv total."
        else:
            status = "TEXT_OR_STATUS_ONLY_NOT_NUMERIC"
            detail = "RAC row has no numeric 2026 permit value to compare."

    def delta(a: object, b: object) -> str:
        left = to_int(a)
        right = to_int(b)
        if left is None or right is None:
            return ""
        return str(left - right)

    if status == "CATEGORY_LEVEL_PRESENT_IN_DATABASE":
        out["delta_res"] = ""
        out["delta_nr"] = ""
        out["delta_total"] = ""
    else:
        out["delta_res"] = delta(row.get("permits_2026_res"), out.get("db_permits_2026_res"))
        out["delta_nr"] = delta(row.get("permits_2026_nr"), out.get("db_permits_2026_nr"))
        out["delta_total"] = delta(row.get("permits_2026_total"), out.get("db_permits_2026_total"))
    out["comparison_status"] = status
    out["comparison_detail"] = detail
    total_delta = to_int(out["delta_total"])
    out["significant_difference"] = "YES" if total_delta is not None and abs(total_delta) > 5 else "NO"
    return out


def summarize(cumulative: list[dict[str, str]], compared: list[dict[str, str]], source_counts: dict[str, int]) -> dict[str, object]:
    db_codes = set(database_index())
    cumulative_codes = {clean(row.get("hunt_code")) for row in cumulative if clean(row.get("hunt_code"))}
    status_counts = Counter(row["comparison_status"] for row in compared)
    family_counts = Counter(row["rac_family"] for row in cumulative)
    species_counts = Counter(row["species"] or "UNKNOWN" for row in cumulative)
    scope_counts = Counter(row["allocation_scope"] for row in cumulative)
    significant = [row for row in compared if row["significant_difference"] == "YES"]
    missing = [row for row in compared if row["comparison_status"] == "MISSING_IN_DATABASE"]
    mismatches = [row for row in compared if row["comparison_status"].startswith("MISMATCH")]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rac_truth_root": str(TRUTH_ROOT.relative_to(ROOT)),
        "database_file": str(DATABASE_PATH.relative_to(ROOT)),
        "included_source_files": source_counts,
        "excluded_source_file_tokens": list(EXCLUDED_RAC_FILE_TOKENS),
        "cumulative_rac_rows": len(cumulative),
        "cumulative_rac_hunt_code_rows": sum(1 for row in cumulative if clean(row.get("hunt_code"))),
        "cumulative_rac_unique_hunt_codes": len(cumulative_codes),
        "database_unique_hunt_codes": len(db_codes),
        "rac_hunt_codes_missing_in_database": len(cumulative_codes - db_codes),
        "database_hunt_codes_not_in_rac_cumulative": len(db_codes - cumulative_codes),
        "comparison_status_counts": dict(status_counts),
        "rac_family_counts": dict(family_counts),
        "species_counts": dict(species_counts),
        "allocation_scope_counts": dict(scope_counts),
        "numeric_mismatch_rows": len(mismatches),
        "significant_difference_rows_abs_delta_gt_5": len(significant),
        "missing_in_database_rows": len(missing),
        "missing_in_database_hunt_codes": sorted({row["hunt_code"] for row in missing if row["hunt_code"]}),
        "significant_difference_examples": [
            {
                "hunt_code": row["hunt_code"],
                "hunt_name": row["hunt_name"],
                "species": row["species"],
                "rac_2026_total": row["permits_2026_total"],
                "database_2026_total": row["db_permits_2026_total"],
                "delta_total": row["delta_total"],
                "status": row["comparison_status"],
            }
            for row in significant[:50]
        ],
    }


def write_markdown(summary: dict[str, object]) -> None:
    lines = [
        "# All RAC 2026 Permits vs DATABASE.csv",
        "",
        "## Summary",
        "",
        f"- Cumulative RAC rows: `{summary['cumulative_rac_rows']}`",
        f"- Cumulative RAC unique hunt codes: `{summary['cumulative_rac_unique_hunt_codes']}`",
        f"- DATABASE unique hunt codes: `{summary['database_unique_hunt_codes']}`",
        f"- RAC hunt codes missing in DATABASE: `{summary['rac_hunt_codes_missing_in_database']}`",
        f"- DATABASE hunt codes not in RAC cumulative: `{summary['database_hunt_codes_not_in_rac_cumulative']}`",
        f"- Numeric mismatch rows: `{summary['numeric_mismatch_rows']}`",
        f"- Significant differences, absolute total delta > 5: `{summary['significant_difference_rows_abs_delta_gt_5']}`",
        "",
        "## Comparison Status Counts",
        "",
    ]
    for key, value in sorted(summary["comparison_status_counts"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## RAC Family Counts", ""])
    for key, value in sorted(summary["rac_family_counts"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Missing In DATABASE Hunt Codes", ""])
    missing = summary["missing_in_database_hunt_codes"]
    lines.append(", ".join(missing) if missing else "None.")
    COMPARE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    cumulative, source_counts = build_cumulative()
    db = database_index()
    compared = [compare_row(row, db) for row in cumulative]
    summary = summarize(cumulative, compared, source_counts)

    write_csv(CUMULATIVE_CSV, cumulative, OUTPUT_FIELDS)
    CUMULATIVE_JSON.write_text(json.dumps({"summary": summary, "rows": cumulative}, indent=2), encoding="utf-8")
    write_csv(COMPARE_CSV, compared, COMPARE_FIELDS)
    COMPARE_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
