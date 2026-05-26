"""Promote reviewed 2026 Expo hard-copy permit totals into DATABASE.csv."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
EXPO_XLSX = ROOT / "pipeline/RAW/hunt_unit_database/2026/xlsx/expo permits 2026.xlsx"
AUDIT_OUT = ROOT / "data_truth/crosswalk_truth/validation/expo_hard_copy_promoted_to_DATABASE_2026.csv"
SUMMARY_OUT = ROOT / "data_truth/crosswalk_truth/validation/expo_hard_copy_promoted_to_DATABASE_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/expo_hard_copy_promoted_to_DATABASE_2026.md"

SOURCE_LABEL = "2026_EXPO_PERMITS_HARD_COPY"
STATUS_LABEL = "HARD_COPY_EXPO_TOTAL_ONLY"
EXPO_TARGETS = {
    "Manti": "EA1220",
    "La Sal": "EA1258",
    "Fishlake/Thousand Lakes": "EA1221",
}
LINE_RE = re.compile(
    r"^Antlerless Elk - General Season - Any Open Season and Unit Within Boundary - "
    r"(?P<unit>.+?) - Permits: (?P<permits>\d+)$"
)


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("\ufeff", "")


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [{key: clean(value) for key, value in row.items()} for row in reader], list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def extract_expo_totals() -> list[dict[str, str]]:
    workbook = openpyxl.load_workbook(EXPO_XLSX, data_only=True, read_only=True)
    rows: list[dict[str, str]] = []
    for sheet in workbook.worksheets:
        for row_number, cells in enumerate(sheet.iter_rows(values_only=True), start=1):
            text = clean(cells[0] if cells else "")
            match = LINE_RE.match(text)
            if not match:
                continue
            unit = match.group("unit")
            hunt_code = EXPO_TARGETS.get(unit)
            if not hunt_code:
                continue
            rows.append(
                {
                    "hunt_code": hunt_code,
                    "unit": unit,
                    "permits_2026_total": match.group("permits"),
                    "source_file": EXPO_XLSX.relative_to(ROOT).as_posix(),
                    "source_sheet": sheet.title,
                    "source_row": str(row_number),
                    "source_text": text,
                }
            )
    return rows


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    expo_rows = extract_expo_totals()
    by_code = {row["hunt_code"]: row for row in expo_rows}
    missing_source_codes = sorted(set(EXPO_TARGETS.values()) - set(by_code))

    db_rows, db_fields = read_csv(DATABASE)
    changed_rows = 0
    audit_rows: list[dict[str, str]] = []
    for db_row in db_rows:
        code = clean(db_row.get("hunt_code"))
        source = by_code.get(code)
        if not source:
            continue
        old_total = clean(db_row.get("permits_2026_total"))
        new_total = source["permits_2026_total"]
        fields = {
            "permits_2026_res": "",
            "permits_2026_nr": "",
            "permits_2026_total": new_total,
            "permits_2026_source": SOURCE_LABEL,
            "permit_allotment_2026_res": "",
            "permit_allotment_2026_nr": "",
            "permit_allotment_2026_total": new_total,
            "permit_allotment_2026_source": SOURCE_LABEL,
            "permit_allotment_2026_source_file": source["source_file"],
            "permit_allotment_2026_status": STATUS_LABEL,
        }
        changed = any(clean(db_row.get(field)) != value for field, value in fields.items())
        for field, value in fields.items():
            db_row[field] = value
        if changed:
            changed_rows += 1
        audit_rows.append(
            {
                "snapshot_utc": timestamp,
                "hunt_code": code,
                "hunt_name": clean(db_row.get("hunt_name")),
                "old_total": old_total,
                "new_total": new_total,
                "promotion_status": "UPDATED_FROM_EXPO_HARD_COPY" if changed else "UNCHANGED_ALREADY_MATCHED_EXPO_HARD_COPY",
                **source,
            }
        )

    write_csv(DATABASE, db_rows, db_fields)
    audit_fields = [
        "snapshot_utc",
        "hunt_code",
        "hunt_name",
        "unit",
        "old_total",
        "new_total",
        "promotion_status",
        "source_file",
        "source_sheet",
        "source_row",
        "source_text",
    ]
    write_csv(AUDIT_OUT, audit_rows, audit_fields)

    summary = {
        "artifact": "expo_hard_copy_promoted_to_DATABASE_2026",
        "snapshot_utc": timestamp,
        "source_file": EXPO_XLSX.relative_to(ROOT).as_posix(),
        "source_row_count": len(expo_rows),
        "promoted_row_count": len(audit_rows),
        "changed_rows": changed_rows,
        "missing_source_codes": missing_source_codes,
        "guardrail": "Expo hard-copy permit values are promoted as total-only permit totals; resident/nonresident splits are not invented.",
        "outputs": {
            "audit_csv": AUDIT_OUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_OUT.relative_to(ROOT).as_posix(),
            "report_md": REPORT_OUT.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Expo Hard-Copy Permits Promoted To DATABASE 2026",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- Source file: `{summary['source_file']}`",
        f"- Source rows found: `{len(expo_rows)}`",
        f"- Promoted rows: `{len(audit_rows)}`",
        f"- Changed rows: `{changed_rows}`",
        "",
        "## Promoted Rows",
        "",
    ]
    for row in audit_rows:
        lines.append(f"- `{row['hunt_code']}` {row['hunt_name']}: `{row['new_total']}` total permits from row `{row['source_row']}`")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not missing_source_codes else 1


if __name__ == "__main__":
    raise SystemExit(main())
