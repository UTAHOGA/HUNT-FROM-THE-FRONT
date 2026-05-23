"""Audit 2023 harvest supplement files against active hunt codes.

The 2024 antlerless harvest CSV has a title row before its real header, so it
must be parsed positionally instead of with the first row as headers.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARVEST_DIR = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2024" / "csv" / "Harvest Results"
ANTLERLESS_HR = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2024" / "csv" / "2024_antlerless_hr.csv"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
DRAW_FILES = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2024" / "csv" / "draw_results_2023_for_2024_long.csv",
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2024"
    / "csv"
    / "draw_results_2023_for_2024_UPLOADED_COMBINED_long.csv",
]
CORE_EXISTING = [
    HARVEST_DIR / "harvest_quality_features_by_hunt_code_2023.csv",
    HARVEST_DIR / "harvest_quality_features_bighorn_by_hunt_code_2023.csv",
    HARVEST_DIR / "harvest_results_2023_hunt_success_long.csv",
    HARVEST_DIR / "harvest_results_2023_bighorn_sheep_hunt_success_aggregate.csv",
]
EXCLUDE_NAME_TOKENS: list[str] = []


def read_csv_dict(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def split_codes(value: str) -> list[str]:
    codes = []
    for token in str(value or "").replace(";", "|").split("|"):
        token = token.strip()
        if token:
            codes.append(token)
    return codes


def code_set(rows: list[dict[str, str]]) -> set[str]:
    keys = ["hunt_code", "selected_hunt_code", "HuntNumber", "hunt_number", "huntCode", "code"]
    out: set[str] = set()
    for row in rows:
        for key in keys:
            if key in row:
                out.update(split_codes(row.get(key, "")))
    return out


def possible_codes(rows: list[dict[str, str]]) -> set[str]:
    out: set[str] = set()
    for row in rows:
        out.update(split_codes(row.get("possible_hunt_codes", "")))
    return out


def useful_fields(headers: list[str]) -> list[str]:
    tokens = [
        "harvest",
        "success",
        "satisfaction",
        "days",
        "hunter",
        "permit",
        "age",
        "length",
        "circumference",
        "reported_hunt_year",
        "model_target_year",
        "source",
        "quality",
        "reason",
    ]
    return [header for header in headers if any(token in header.lower() for token in tokens)]


def load_active_codes() -> set[str]:
    rows, _ = read_csv_dict(DATABASE)
    return {row["hunt_code"].strip() for row in rows if row.get("hunt_code", "").strip()}


def normalize_antlerless_hr(path: Path = ANTLERLESS_HR) -> tuple[list[dict[str, str]], list[str]]:
    """Normalize the malformed antlerless harvest CSV by locating its real header."""
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.reader(handle))

    header_index = None
    for index, row in enumerate(raw_rows):
        if len(row) >= 9 and row[0].strip() == "Species" and row[1].strip() == "Hunt #":
            header_index = index
            break
    if header_index is None:
        return [], []

    normalized_headers = [
        "reported_hunt_year",
        "model_target_year",
        "species",
        "hunt_code",
        "hunt_name",
        "weapon",
        "permits",
        "harvest_hunters",
        "harvest",
        "harvest_success_percent",
        "harvest_average_days",
        "source_file",
        "parse_status",
        "do_not_use_for_permit_quota",
        "do_not_use_for_p_draw_directly",
    ]
    rows: list[dict[str, str]] = []
    for raw in raw_rows[header_index + 1 :]:
        if len(raw) < 9:
            continue
        hunt_code = raw[1].strip()
        if not hunt_code:
            continue
        rows.append(
            {
                "reported_hunt_year": "2023",
                "model_target_year": "2024",
                "species": raw[0].strip(),
                "hunt_code": hunt_code,
                "hunt_name": raw[2].strip(),
                "weapon": raw[3].strip(),
                "permits": raw[4].strip(),
                "harvest_hunters": raw[5].strip(),
                "harvest": raw[6].strip(),
                "harvest_success_percent": raw[7].strip(),
                "harvest_average_days": raw[8].strip(),
                "source_file": str(path.relative_to(ROOT)),
                "parse_status": "POSITIONAL_HEADER_NORMALIZED",
                "do_not_use_for_permit_quota": "True",
                "do_not_use_for_p_draw_directly": "True",
            }
        )
    return rows, normalized_headers


def classify_file(path: Path, rows: list[dict[str, str]], codes: set[str], existing_codes: set[str]) -> str:
    name = path.name.lower()
    if not rows:
        return "missing_or_empty"
    if path.name.lower() == "2024_antlerless_hr.csv":
        return "additive_hunt_code_keyed_positional_normalized"
    if codes - existing_codes:
        return "additive_hunt_code_keyed"
    if "measurement" in name or "crosswalk" in name or "unit_dates" in name:
        return "supporting_quality_crosswalk_or_measurement"
    if "summary" in name:
        return "summary_only"
    if "all_sources" in name or "uploaded" in name:
        return "alternate_source_or_validation_support"
    if codes:
        return "covered_core_keyed_or_duplicate"
    return "needs_normalization_no_hunt_code"


def main() -> int:
    active_codes = load_active_codes()

    draw_codes: set[str] = set()
    for path in DRAW_FILES:
        rows, _ = read_csv_dict(path)
        draw_codes |= code_set(rows)

    existing_core_codes: set[str] = set()
    for path in CORE_EXISTING:
        rows, _ = read_csv_dict(path)
        existing_core_codes |= code_set(rows)

    harvest_files = []
    if HARVEST_DIR.exists():
        harvest_files.extend(
            path
            for path in sorted(HARVEST_DIR.glob("*.csv"))
            if not any(token in path.name.lower() for token in EXCLUDE_NAME_TOKENS)
        )
    if ANTLERLESS_HR.exists():
        harvest_files.append(ANTLERLESS_HR)

    rows_out: list[dict[str, object]] = []
    all_harvest_codes: set[str] = set()
    all_possible_codes: set[str] = set()
    normalized_antlerless_rows: list[dict[str, str]] = []
    normalized_antlerless_headers: list[str] = []

    for path in harvest_files:
        if path.name.lower() == "2024_antlerless_hr.csv":
            rows, headers = normalize_antlerless_hr(path)
            normalized_antlerless_rows = rows
            normalized_antlerless_headers = headers
        else:
            rows, headers = read_csv_dict(path)
        codes = code_set(rows)
        possible = possible_codes(rows)
        all_harvest_codes |= codes
        all_possible_codes |= possible
        rows_out.append(
            {
                "file": str(path.relative_to(ROOT)),
                "status": "present" if path.exists() else "missing",
                "rows": len(rows),
                "headers": len(headers),
                "unique_hunt_codes": len(codes),
                "possible_hunt_codes": len(possible),
                "codes_in_active_database": len(codes & active_codes),
                "codes_not_in_active_database": len(codes - active_codes),
                "new_codes_vs_core_harvest": len(codes - existing_core_codes),
                "new_active_codes_vs_core_harvest": len((codes - existing_core_codes) & active_codes),
                "codes_overlap_draw_2023": len(codes & draw_codes),
                "classification": classify_file(path, rows, codes, existing_core_codes),
                "useful_fields": "|".join(useful_fields(headers)),
                "sample_new_codes_vs_core": "|".join(sorted(codes - existing_core_codes)[:25]),
                "sample_headers": "|".join(headers[:30]),
            }
        )

    additive_active_codes = (all_harvest_codes - existing_core_codes) & active_codes
    summary = {
        "harvest_results_dir": str(HARVEST_DIR.relative_to(ROOT)),
        "excluded_name_tokens": EXCLUDE_NAME_TOKENS,
        "files_checked": len(harvest_files),
        "active_database_hunt_codes": len(active_codes),
        "draw_union_2023_hunt_codes": len(draw_codes),
        "core_existing_harvest_hunt_codes": len(existing_core_codes),
        "expanded_harvest_keyed_hunt_codes_excluding_turkey": len(all_harvest_codes),
        "expanded_harvest_possible_crosswalk_codes": len(all_possible_codes),
        "expanded_harvest_codes_in_active_database": len(all_harvest_codes & active_codes),
        "expanded_harvest_codes_not_active_database": len(all_harvest_codes - active_codes),
        "expanded_harvest_codes_overlap_draw_2023": len(all_harvest_codes & draw_codes),
        "new_keyed_codes_vs_core_harvest": len(all_harvest_codes - existing_core_codes),
        "new_active_keyed_codes_vs_core_harvest": len(additive_active_codes),
        "new_active_keyed_codes_vs_core_harvest_list": sorted(additive_active_codes),
        "classification_counts": dict(Counter(str(row["classification"]) for row in rows_out)),
    }

    out_dir = ROOT / "processed_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_csv = out_dir / "harvest_2023_supplement_audit.csv"
    with audit_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(rows_out[0].keys()) if rows_out else ["file"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    (out_dir / "harvest_2023_supplement_audit.json").write_text(
        json.dumps({"summary": summary, "files": rows_out}, indent=2), encoding="utf-8"
    )

    if normalized_antlerless_rows:
        with (out_dir / "harvest_results_2023_antlerless_hr_normalized.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=normalized_antlerless_headers)
            writer.writeheader()
            writer.writerows(normalized_antlerless_rows)

    lines = [
        "# 2023 Harvest Supplement Audit",
        "",
        "Turkey harvest files are included as harvest-quality supplements. They must not be used as permit quotas or direct draw odds.",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        if isinstance(value, list):
            value = ", ".join(value)
        lines.append(f"- {key}: {value}")
    lines += ["", "## Additive / Supporting Files"]
    for row in rows_out:
        if row["classification"] != "covered_core_keyed_or_duplicate":
            lines.append(
                f"- {row['file']}: {row['classification']}; rows={row['rows']}; "
                f"unique_codes={row['unique_hunt_codes']}; new_active_codes={row['new_active_codes_vs_core_harvest']}"
            )
    (out_dir / "harvest_2023_supplement_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
