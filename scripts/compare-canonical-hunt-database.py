"""Compare canonical hunt catalog surfaces against DATABASE.csv.

The comparison is keyed by hunt_code and checks hunt name plus explicit active
2026 permit fields. Ambiguous legacy permit-year aliases are intentionally not
part of this publish-readiness comparison.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
OUT_CSV = ROOT / "processed_data" / "canonical_vs_DATABASE_hunt_code_name_permits_year.csv"
OUT_JSON = ROOT / "processed_data" / "canonical_vs_DATABASE_hunt_code_name_permits_year.json"
OUT_MD = ROOT / "processed_data" / "canonical_vs_DATABASE_hunt_code_name_permits_year.md"
GAP_JSON = ROOT / "processed_data" / "new_2026_rac_hunts_explain_1394_gap.json"

CANONICAL_TARGETS = [
    ROOT / "hunt-master-canonical-2026.json",
    ROOT / "canonical" / "hunt-planner-2026.json",
    ROOT / "generated" / "pages" / "hunt-planner.json",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
]

DIRECT_FIELDS = [
    "hunt_name",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
]

def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"-", "–", "—", "null", "None"}:
        return ""
    return text


def norm_text(value: object) -> str:
    return " ".join(clean(value).lower().replace("&", "and").split())


def norm_number(value: object) -> str:
    text = clean(value).replace(",", "")
    if text == "":
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return str(int(number)) if number.is_integer() else str(number)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def read_target(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    if path.suffix.lower() == ".csv":
        return read_csv(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("hunt_catalog") or data.get("hunts") or data.get("records") or []
    else:
        rows = []
    fields = list(dict.fromkeys(key for row in rows if isinstance(row, dict) for key in row.keys()))
    return fields, rows


def code_of(row: dict[str, Any]) -> str:
    return clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()


def rows_by_code(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = code_of(row)
        if code and code not in out:
            out[code] = row
    return out


def compare_value(field: str, db_value: object, canonical_value: object) -> tuple[bool, str, str]:
    if field == "hunt_name":
        db_norm = norm_text(db_value)
        canonical_norm = norm_text(canonical_value)
        return db_norm == canonical_norm, clean(db_value), clean(canonical_value)
    return norm_number(db_value) == norm_number(canonical_value), norm_number(db_value), norm_number(canonical_value)


def compare_target(path: Path, db_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    fields, rows = read_target(path)
    target_rows = rows_by_code(rows)
    db_codes = set(db_rows)
    target_codes = set(target_rows)
    row_reports: list[dict[str, str]] = []
    field_counts: Counter[str] = Counter()

    shared_fields = [field for field in DIRECT_FIELDS if field in fields and field in next(iter(db_rows.values()))]
    for code in sorted(db_codes | target_codes):
        db_row = db_rows.get(code, {})
        target_row = target_rows.get(code, {})
        if code not in db_codes:
            row_reports.append(
                {
                    "canonical_file": path.relative_to(ROOT).as_posix(),
                    "hunt_code": code,
                    "status": "CANONICAL_ONLY",
                    "field": "",
                    "database_value": "",
                    "canonical_value": "",
                    "hunt_name_database": "",
                    "hunt_name_canonical": clean(target_row.get("hunt_name") or target_row.get("title")),
                }
            )
            continue
        if code not in target_codes:
            row_reports.append(
                {
                    "canonical_file": path.relative_to(ROOT).as_posix(),
                    "hunt_code": code,
                    "status": "DATABASE_ONLY",
                    "field": "",
                    "database_value": "",
                    "canonical_value": "",
                    "hunt_name_database": clean(db_row.get("hunt_name")),
                    "hunt_name_canonical": "",
                }
            )
            continue

        for field in shared_fields:
            ok, db_value, canonical_value = compare_value(field, db_row.get(field), target_row.get(field))
            if ok:
                continue
            field_counts[field] += 1
            row_reports.append(
                {
                    "canonical_file": path.relative_to(ROOT).as_posix(),
                    "hunt_code": code,
                    "status": "FIELD_MISMATCH",
                    "field": field,
                    "database_value": db_value,
                    "canonical_value": canonical_value,
                    "hunt_name_database": clean(db_row.get("hunt_name")),
                    "hunt_name_canonical": clean(target_row.get("hunt_name") or target_row.get("title")),
                }
            )

    status_counts = Counter(row["status"] for row in row_reports)
    direct_mismatch_count = status_counts.get("FIELD_MISMATCH", 0)
    return {
        "canonical_file": path.relative_to(ROOT).as_posix(),
        "database_hunt_code_count": len(db_codes),
        "canonical_hunt_code_count": len(target_codes),
        "in_both_hunt_code_count": len(db_codes & target_codes),
        "database_only_hunt_code_count": len(db_codes - target_codes),
        "canonical_only_hunt_code_count": len(target_codes - db_codes),
        "mismatch_row_count": sum(1 for row in row_reports if row["status"] == "FIELD_MISMATCH"),
        "active_2026_or_name_mismatch_count": direct_mismatch_count,
        "status_counts": dict(sorted(status_counts.items())),
        "field_mismatch_counts": dict(sorted(field_counts.items())),
        "database_only_examples": sorted(db_codes - target_codes)[:50],
        "canonical_only_examples": sorted(target_codes - db_codes)[:50],
        "mismatch_examples": [row for row in row_reports if row["status"] == "FIELD_MISMATCH"][:50],
        "rows": row_reports,
    }


def write_outputs(summary: dict[str, Any], target_reports: list[dict[str, Any]]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    fieldnames = [
        "canonical_file",
        "hunt_code",
        "status",
        "field",
        "database_value",
        "canonical_value",
        "hunt_name_database",
        "hunt_name_canonical",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for report in target_reports:
            writer.writerows(report["rows"])
    lines = [
        "# Canonical Vs DATABASE Hunt Code / Name / Permit-Year Cross-Check",
        "",
        f"Generated UTC: {summary['generated_at_utc']}",
        f"Database rows: {summary['database_rows']}",
        f"Database unique hunt codes: {summary['database_unique_hunt_codes']}",
        "",
        "| Canonical file | Codes | In both | DB only | Canonical only | Active 2026/name mismatches |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for report in target_reports:
        lines.append(
            f"| {report['canonical_file']} | {report['canonical_hunt_code_count']} | {report['in_both_hunt_code_count']} | {report['database_only_hunt_code_count']} | {report['canonical_only_hunt_code_count']} | {report['active_2026_or_name_mismatch_count']} |"
        )
    aligned = [
        report["canonical_file"]
        for report in target_reports
        if report["database_only_hunt_code_count"] == 0
        and report["canonical_only_hunt_code_count"] == 0
        and report["active_2026_or_name_mismatch_count"] == 0
    ]
    lagging = [
        report["canonical_file"]
        for report in target_reports
        if report["database_only_hunt_code_count"] > 0 or report["active_2026_or_name_mismatch_count"] > 0
    ]
    lines.extend(["", "## Active 2026 Alignment", ""])
    if aligned:
        lines.append("- Aligned with `DATABASE.csv` for hunt code, normalized hunt name, and active 2026 permit fields: " + ", ".join(f"`{item}`" for item in aligned) + ".")
    if lagging:
        lines.append("- Needs review or regeneration before treating as publish-canonical: " + ", ".join(f"`{item}`" for item in lagging) + ".")
    if GAP_JSON.exists():
        gap = json.loads(GAP_JSON.read_text(encoding="utf-8"))
        lines.extend(
            [
                "",
                "## 1,411 To 1,394 Gap Explanation",
                "",
                f"- The former 17-code gap in stale 1,394-code catalog files is explained by new 2026 RAC rows.",
                f"- New 2026 antlerless elk rows: {gap.get('antlerless_elk_new_2026_count', 0)} hunt codes from `pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_antlerless_elk_permits.csv`.",
                f"- New 2026 doe pronghorn rows: {gap.get('doe_pronghorn_new_2026_count', 0)} hunt code, `PD1039`, from `pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_doe_pronghorn_permits.csv`.",
                f"- Combined permits represented by those rows: {gap.get('total_2026_permits', 0)} total permits (`{gap.get('total_2026_res', 0)}` resident / `{gap.get('total_2026_nr', 0)}` nonresident).",
                "- Detailed pullout: `processed_data/new_2026_rac_hunts_explain_1394_gap.md`.",
            ]
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Active 2026/name mismatches compare shared `hunt_name`, `permits_2026_*`, and `permit_allotment_2026_*` columns.",
            "- Ambiguous `permits_year_*` columns are intentionally excluded; explicit `permits_2025_draw_*` and active 2026 allotment fields carry year-specific permit meaning.",
            "- Hunt names are compared case-insensitively with whitespace normalized.",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    _, db_raw_rows = read_csv(DATABASE)
    db_rows = rows_by_code(db_raw_rows)
    target_reports = [compare_target(path, db_rows) for path in CANONICAL_TARGETS if path.exists()]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_file": DATABASE.relative_to(ROOT).as_posix(),
        "database_rows": len(db_raw_rows),
        "database_unique_hunt_codes": len(db_rows),
        "canonical_reports": [
            {key: value for key, value in report.items() if key != "rows"}
            for report in target_reports
        ],
        "outputs": {
            "csv": OUT_CSV.relative_to(ROOT).as_posix(),
            "json": OUT_JSON.relative_to(ROOT).as_posix(),
            "md": OUT_MD.relative_to(ROOT).as_posix(),
        },
    }
    write_outputs(summary, target_reports)
    console_summary = {
        key: value
        for key, value in summary.items()
        if key != "canonical_reports"
    }
    console_summary["canonical_reports"] = [
        {
            "canonical_file": report["canonical_file"],
            "canonical_hunt_code_count": report["canonical_hunt_code_count"],
            "database_only_hunt_code_count": report["database_only_hunt_code_count"],
            "canonical_only_hunt_code_count": report["canonical_only_hunt_code_count"],
            "active_2026_or_name_mismatch_count": report["active_2026_or_name_mismatch_count"],
            "database_only_examples": report["database_only_examples"],
            "field_mismatch_counts": report["field_mismatch_counts"],
        }
        for report in summary["canonical_reports"]
    ]
    print(json.dumps(console_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
