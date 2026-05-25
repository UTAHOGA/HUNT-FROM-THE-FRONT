#!/usr/bin/env python3
"""Audit historical permit lineage in canonical DATABASE.csv.

Passed hunt-year permit values are canonical only when their reviewed source
lineage is present. This audit verifies that populated 2025 permit fields in the
canonical DATABASE carry source fields and clearly separates the full historical
permit universe from the narrower bonus-point draw-results subset.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HUNTS_ROOT = Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS")
DATABASE = HUNTS_ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

OUTPUT = ROOT / "processed_data/database_historical_permit_lineage_2026.csv"
SUMMARY_JSON = ROOT / "processed_data/database_historical_permit_lineage_2026_summary.json"
SUMMARY_MD = ROOT / "processed_data/database_historical_permit_lineage_2026.md"
VALIDATION_JSON = (
    ROOT / "data_truth/comparison_outputs/validation/database_historical_permit_lineage_2026_summary.json"
)

TRIPLE_FIELDS = ("res", "nr", "total")
HISTORICAL_FAMILIES = [
    {
        "family": "permits_2025",
        "historical_year": "2025",
        "source_field": "permits_2025_source",
        "expected_source": "2025_DRAW_RESULTS_TABLES",
    },
    {
        "family": "permits_2025_draw",
        "historical_year": "2025",
        "source_field": "permits_2025_draw_source",
        "expected_source": "canonical_2026_source_of_truth_draw_results",
    },
]

OUTPUT_FIELDS = [
    "hunt_code",
    "hunt_name",
    "species",
    "historical_year",
    "field_family",
    "res",
    "nr",
    "total",
    "source_field",
    "source_value",
    "lineage_status",
    "canonical_status",
    "paired_family_compare_status",
    "review_reason",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"-", "nan", "None"}:
        return ""
    return text


def int_text(value: object) -> str:
    text = clean(value).replace(",", "")
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def read_database() -> list[dict[str, str]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def triple(row: dict[str, str], family: str) -> tuple[str, str, str]:
    return tuple(int_text(row.get(f"{family}_{field}", "")) for field in TRIPLE_FIELDS)  # type: ignore[return-value]


def has_numeric(values: tuple[str, str, str]) -> bool:
    return any(values)


def compare_pair(primary: tuple[str, str, str], secondary: tuple[str, str, str]) -> str:
    primary_has = has_numeric(primary)
    secondary_has = has_numeric(secondary)
    if not primary_has and not secondary_has:
        return "BOTH_BLANK"
    if primary_has and not secondary_has:
        return "PRIMARY_ONLY"
    if secondary_has and not primary_has:
        return "SECONDARY_ONLY"
    if primary == secondary:
        return "MATCH"
    if primary[2] and secondary[2] and primary[2] == secondary[2]:
        return "TOTAL_MATCH_SPLIT_DIFFERS"
    return "MISMATCH"


def family_audit_row(
    row: dict[str, str],
    family_def: dict[str, str],
    pair_status: str,
) -> dict[str, str]:
    values = triple(row, family_def["family"])
    source_value = clean(row.get(family_def["source_field"]))
    numeric = has_numeric(values)
    if numeric and source_value:
        lineage_status = "SOURCE_PRESENT"
        canonical_status = "CANONICAL_HISTORICAL_SOURCE_TRUTH"
        review_reason = ""
    elif numeric:
        lineage_status = "SOURCE_MISSING"
        canonical_status = "BLOCKED_LINEAGE_REPAIR_REQUIRED"
        review_reason = "Historical permit value is populated but source-lineage field is blank."
    elif source_value:
        lineage_status = "SOURCE_ONLY_NO_NUMERIC_VALUE"
        canonical_status = "SOURCE_METADATA_ONLY"
        review_reason = "Source field is populated but permit value fields are blank."
    else:
        lineage_status = "BLANK"
        canonical_status = "NO_HISTORICAL_VALUE"
        review_reason = ""

    expected_source = family_def.get("expected_source", "")
    if numeric and source_value and expected_source and source_value != expected_source:
        lineage_status = "SOURCE_PRESENT_UNEXPECTED_VALUE"
        canonical_status = "REVIEW_SOURCE_VALUE"
        review_reason = f"Expected source value {expected_source}, found {source_value}."

    return {
        "hunt_code": clean(row.get("hunt_code")).upper(),
        "hunt_name": clean(row.get("hunt_name")),
        "species": clean(row.get("species")),
        "historical_year": family_def["historical_year"],
        "field_family": family_def["family"],
        "res": values[0],
        "nr": values[1],
        "total": values[2],
        "source_field": family_def["source_field"],
        "source_value": source_value,
        "lineage_status": lineage_status,
        "canonical_status": canonical_status,
        "paired_family_compare_status": pair_status,
        "review_reason": review_reason,
    }


def build_audit() -> tuple[list[dict[str, str]], dict]:
    database_rows = read_database()
    output_rows: list[dict[str, str]] = []
    pair_counts: Counter[str] = Counter()

    for row in database_rows:
        base = triple(row, "permits_2025")
        draw = triple(row, "permits_2025_draw")
        pair_status = compare_pair(base, draw)
        pair_counts[pair_status] += 1
        for family_def in HISTORICAL_FAMILIES:
            output_rows.append(family_audit_row(row, family_def, pair_status))

    family_counts: dict[str, dict[str, int]] = defaultdict(dict)
    family_sources: dict[str, dict[str, int]] = defaultdict(dict)
    for family_def in HISTORICAL_FAMILIES:
        family = family_def["family"]
        family_rows = [row for row in output_rows if row["field_family"] == family]
        family_counts[family] = dict(sorted(Counter(row["canonical_status"] for row in family_rows).items()))
        family_sources[family] = dict(sorted(Counter(row["source_value"] or "BLANK" for row in family_rows).items()))

    lineage_blockers = [
        row["hunt_code"]
        for row in output_rows
        if row["canonical_status"] in {"BLOCKED_LINEAGE_REPAIR_REQUIRED", "REVIEW_SOURCE_VALUE"}
    ]
    canonical_rows = sum(1 for row in output_rows if row["canonical_status"] == "CANONICAL_HISTORICAL_SOURCE_TRUTH")
    full_2025_universe_rows = sum(
        1
        for row in output_rows
        if row["field_family"] == "permits_2025" and row["canonical_status"] == "CANONICAL_HISTORICAL_SOURCE_TRUTH"
    )
    bonus_point_subset_rows = sum(
        1
        for row in output_rows
        if row["field_family"] == "permits_2025_draw"
        and row["canonical_status"] == "CANONICAL_HISTORICAL_SOURCE_TRUTH"
    )
    base_only_rows = pair_counts["PRIMARY_ONLY"]

    summary = {
        "artifact": "database_historical_permit_lineage_2026",
        "database_file": str(DATABASE).replace("\\", "/"),
        "database_row_count": len(database_rows),
        "output_row_count": len(output_rows),
        "historical_years_detected": ["2025"],
        "historical_field_families": [family["family"] for family in HISTORICAL_FAMILIES],
        "historical_2025_full_permit_universe_rows": full_2025_universe_rows,
        "historical_2025_bonus_point_draw_subset_rows": bonus_point_subset_rows,
        "historical_2025_non_bonus_or_general_subset_rows": base_only_rows,
        "canonical_historical_source_truth_rows": canonical_rows,
        "lineage_blocker_count": len(lineage_blockers),
        "lineage_blocker_codes": sorted(set(lineage_blockers)),
        "family_canonical_status_counts": family_counts,
        "family_source_value_counts": family_sources,
        "paired_family_compare_counts": dict(sorted(pair_counts.items())),
        "guardrail": (
            "Passed hunt-year permit values are canonical source truth when populated with reviewed source lineage. "
            "They must not drift because a newer working file, RAC file, inferred value, or comparison output disagrees. "
            "Historical populated values without lineage are blocked for lineage repair. The permits_2025 family is "
            "the full 2025 historical permit universe in DATABASE.csv; permits_2025_draw is a narrower bonus-point "
            "draw-results subset and must not be described as the full 2025 draw/permit universe."
        ),
        "outputs": {
            "csv": OUTPUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "summary_md": SUMMARY_MD.relative_to(ROOT).as_posix(),
            "validation_json": VALIDATION_JSON.relative_to(ROOT).as_posix(),
        },
    }
    return output_rows, summary


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in OUTPUT_FIELDS})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(summary: dict) -> None:
    lines = [
        "# Database Historical Permit Lineage 2026",
        "",
        "This audit verifies that passed-year permit fields in canonical `DATABASE.csv` carry source lineage.",
        "",
        "## Summary",
        "",
        f"- DATABASE rows: `{summary['database_row_count']}`",
        f"- Audit rows: `{summary['output_row_count']}`",
        f"- Historical years detected: `{', '.join(summary['historical_years_detected'])}`",
        f"- Full 2025 historical permit universe rows: `{summary['historical_2025_full_permit_universe_rows']}`",
        f"- 2025 bonus-point draw subset rows: `{summary['historical_2025_bonus_point_draw_subset_rows']}`",
        f"- 2025 non-bonus/general subset rows: `{summary['historical_2025_non_bonus_or_general_subset_rows']}`",
        f"- Canonical historical source-truth rows: `{summary['canonical_historical_source_truth_rows']}`",
        f"- Lineage blocker count: `{summary['lineage_blocker_count']}`",
        "",
        "## Guardrail",
        "",
        summary["guardrail"],
        "",
        "## Family Status Counts",
        "",
    ]
    for family, counts in summary["family_canonical_status_counts"].items():
        lines.append(f"### {family}")
        lines.append("")
        for status, count in counts.items():
            lines.append(f"- `{status}`: `{count}`")
        lines.append("")
    lines.extend(["## Paired Family Compare Counts", ""])
    for status, count in summary["paired_family_compare_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows, summary = build_audit()
    write_csv(OUTPUT, rows)
    write_json(SUMMARY_JSON, summary)
    write_json(VALIDATION_JSON, summary)
    write_markdown(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
