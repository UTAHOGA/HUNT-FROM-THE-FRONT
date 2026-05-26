#!/usr/bin/env python3
"""Validate canonical 2026 antlerless elk private-lands EA permit source.

This script treats the supplied DWR Hunt Planner CSV as canonical source
evidence, normalizes its totals, and compares it to the protected current
DATABASE.csv without modifying DATABASE values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits/elk antlerless private lands only EA.csv"
)
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"

NORMALIZED = (
    ROOT
    / "data_truth/permit_overlay_truth/normalized/elk_antlerless_private_lands_EA_2026_canonical.csv"
)
COMPARISON = (
    ROOT
    / "data_truth/permit_overlay_truth/validation/elk_antlerless_private_lands_EA_2026_vs_DATABASE.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/permit_overlay_truth/validation/elk_antlerless_private_lands_EA_2026_summary.json"
)
SUMMARY_MD = ROOT / "processed_data/elk_antlerless_private_lands_EA_2026_summary.md"

NORMALIZED_FIELDS = [
    "hunt_code",
    "hunt_name",
    "sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "permits_2026_total",
    "permits_2026_total_numeric",
    "source_file",
    "source_sha256",
    "source_status",
]

COMPARISON_FIELDS = [
    "hunt_code",
    "source_hunt_name",
    "database_hunt_name",
    "source_permits_2026_total",
    "database_permits_2026_total",
    "comparison_status",
    "review_action",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip().replace("\ufeff", "")


def numeric_total(value: object) -> int | None:
    text = clean(value).replace(",", "")
    match = re.search(r"-?\d+", text)
    return int(match.group(0)) if match else None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_source(rows: list[dict[str, str]], sha256: str) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for row in rows:
        total = numeric_total(row.get("permits_2026_total"))
        normalized.append(
            {
                "hunt_code": row.get("hunt_code", ""),
                "hunt_name": row.get("hunt_name", ""),
                "sex_type": row.get("sex_type", ""),
                "species": row.get("species", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "season": row.get("season", ""),
                "permits_2026_total": row.get("permits_2026_total", ""),
                "permits_2026_total_numeric": total if total is not None else "",
                "source_file": SOURCE.relative_to(ROOT).as_posix(),
                "source_sha256": sha256,
                "source_status": "CANONICAL_USER_SUPPLIED_DWR_HUNT_PLANNER_EVIDENCE",
            }
        )
    return normalized


def database_total(row: dict[str, str]) -> int | None:
    for field in ("permits_2026_total", "Total", "total"):
        total = numeric_total(row.get(field))
        if total is not None:
            return total
    return None


def compare_to_database(
    normalized_rows: list[dict[str, object]],
    database_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    by_code = {clean(row.get("hunt_code")): row for row in database_rows}
    output: list[dict[str, object]] = []
    for row in normalized_rows:
        code = clean(row.get("hunt_code"))
        source_total = numeric_total(row.get("permits_2026_total_numeric"))
        database_row = by_code.get(code)
        if database_row is None:
            database_name = ""
            database_permits = ""
            status = "MISSING_IN_DATABASE"
            action = "Add reviewed current-code row only after DATABASE promotion approval."
        else:
            database_name = database_row.get("hunt_name", "")
            database_total_value = database_total(database_row)
            database_permits = database_total_value if database_total_value is not None else ""
            if source_total == database_total_value:
                status = "MATCH"
                action = "No action."
            else:
                status = "DATABASE_PROTECTED_VALUE_DIFFERS_FROM_CANONICAL_SOURCE"
                action = (
                    "Review for explicit DATABASE promotion; do not overwrite populated DATABASE values "
                    "without approval."
                )
        output.append(
            {
                "hunt_code": code,
                "source_hunt_name": row.get("hunt_name", ""),
                "database_hunt_name": database_name,
                "source_permits_2026_total": source_total if source_total is not None else "",
                "database_permits_2026_total": database_permits,
                "comparison_status": status,
                "review_action": action,
            }
        )
    return output


def validate(normalized_rows: list[dict[str, object]]) -> list[str]:
    blockers: list[str] = []
    codes = [clean(row.get("hunt_code")) for row in normalized_rows]
    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    if duplicates:
        blockers.append(f"Duplicate hunt codes: {', '.join(duplicates)}")
    for row in normalized_rows:
        code = clean(row.get("hunt_code"))
        if not code.startswith("EA"):
            blockers.append(f"{code}: hunt_code is not EA-prefixed")
        if row.get("sex_type") != "Antlerless":
            blockers.append(f"{code}: sex_type is not Antlerless")
        if row.get("species") != "Elk":
            blockers.append(f"{code}: species is not Elk")
        if row.get("hunt_type") != "Private Lands Only":
            blockers.append(f"{code}: hunt_type is not Private Lands Only")
        if numeric_total(row.get("permits_2026_total_numeric")) is None:
            blockers.append(f"{code}: missing numeric permits_2026_total")
    return blockers


def build_summary(
    normalized_rows: list[dict[str, object]],
    comparison_rows: list[dict[str, object]],
    blockers: list[str],
    sha256: str,
) -> dict[str, object]:
    mismatch_rows = [
        row
        for row in comparison_rows
        if row["comparison_status"] == "DATABASE_PROTECTED_VALUE_DIFFERS_FROM_CANONICAL_SOURCE"
    ]
    missing_rows = [row for row in comparison_rows if row["comparison_status"] == "MISSING_IN_DATABASE"]
    return {
        "artifact": "elk_antlerless_private_lands_EA_2026_canonical_validation",
        "source_file": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": sha256,
        "source_status": "CANONICAL_USER_SUPPLIED_DWR_HUNT_PLANNER_EVIDENCE",
        "database_file": DATABASE.relative_to(ROOT).as_posix(),
        "source_rows": len(normalized_rows),
        "unique_hunt_codes": len({row["hunt_code"] for row in normalized_rows}),
        "source_total_permits_2026": sum(
            numeric_total(row.get("permits_2026_total_numeric")) or 0 for row in normalized_rows
        ),
        "database_missing_count": len(missing_rows),
        "database_mismatch_count": len(mismatch_rows),
        "database_mismatch_codes": [row["hunt_code"] for row in mismatch_rows],
        "blocker_count": len(blockers),
        "blockers": blockers,
        "guardrail": (
            "This validation registers the supplied EA private-lands file as canonical source evidence. "
            "It does not overwrite populated DATABASE.csv values; differing protected cells require explicit "
            "review and promotion approval."
        ),
        "outputs": {
            "normalized_csv": NORMALIZED.relative_to(ROOT).as_posix(),
            "comparison_csv": COMPARISON.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "summary_md": SUMMARY_MD.relative_to(ROOT).as_posix(),
        },
    }


def write_markdown(summary: dict[str, object]) -> None:
    lines = [
        "# 2026 EA Private-Lands Canonical Source Validation",
        "",
        "User-supplied DWR Hunt Planner source for antlerless elk private-lands-only `EA` permits.",
        "",
        "## Results",
        "",
        f"- Source rows: `{summary['source_rows']}`",
        f"- Unique hunt codes: `{summary['unique_hunt_codes']}`",
        f"- Source total 2026 permits: `{summary['source_total_permits_2026']}`",
        f"- Missing in DATABASE: `{summary['database_missing_count']}`",
        f"- DATABASE protected-value mismatches: `{summary['database_mismatch_count']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        "",
        "## DATABASE Mismatch Codes",
        "",
    ]
    mismatch_codes = summary["database_mismatch_codes"]
    if mismatch_codes:
        for code in mismatch_codes:
            lines.append(f"- `{code}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Guardrail", "", str(summary["guardrail"])])
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    if not DATABASE.exists():
        raise FileNotFoundError(DATABASE)

    sha256 = source_hash(SOURCE)
    source_rows = read_csv(SOURCE)
    database_rows = read_csv(DATABASE)
    normalized_rows = normalize_source(source_rows, sha256)
    blockers = validate(normalized_rows)
    comparison_rows = compare_to_database(normalized_rows, database_rows)
    summary = build_summary(normalized_rows, comparison_rows, blockers, sha256)

    write_csv(NORMALIZED, normalized_rows, NORMALIZED_FIELDS)
    write_csv(COMPARISON, comparison_rows, COMPARISON_FIELDS)
    write_json(SUMMARY_JSON, summary)
    write_markdown(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
