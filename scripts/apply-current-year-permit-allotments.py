"""Apply canonical current-year permit allotment fields to runtime CSVs.

RAC tables are authoritative for current-year available/allotted permit counts
when they provide a direct hunt_code row. Existing 2026 permit fields are used
only as fallback values when no direct RAC row exists.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ALLOTMENT_FIELDS = [
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
    "permit_allotment_2026_source",
    "permit_allotment_2026_source_file",
    "permit_allotment_2026_status",
]

RAC_SOURCE_LABEL = "2026_RAC_CURRENT_YEAR_ALLOTMENT"
FALLBACK_SOURCE_LABEL = "FALLBACK_EXISTING_2026_PERMITS"
RAC_EXCLUDE_TOKENS = (
    "comparison",
    "supplemental",
    "permit_rows_from_pdf",
    "control_units",
)

TARGET_RUNTIME_FILES = [
    "processed_data/hunt_unit_reference_linked.csv",
    "processed_data/hunt_master_enriched.csv",
    "processed_data/draw_reality_engine.csv",
    "processed_data/point_ladder_view.csv",
    "processed_data/ml_draw_predictions_v1.csv",
    "processed_data/draw_reality_engine_predictive_v2.csv",
]


@dataclass(frozen=True)
class Allotment:
    hunt_code: str
    res: str
    nr: str
    total: str
    source_file: str
    source_document: str
    has_split: bool


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text in {"-", "–", "—"}:
        return ""
    return text


def to_int_text(value: object) -> str:
    text = clean(value).replace(",", "")
    if text == "":
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    if number.is_integer():
        return str(int(number))
    return str(number)


def row_total(row: dict[str, str]) -> str:
    total = to_int_text(row.get("permits_2026_total"))
    if total:
        return total
    res = to_int_text(row.get("permits_2026_res"))
    nr = to_int_text(row.get("permits_2026_nr"))
    if res or nr:
        return str(int(res or 0) + int(nr or 0))
    return ""


def choose_allotment(existing: Allotment | None, candidate: Allotment) -> Allotment:
    if existing is None:
        return candidate
    if candidate.has_split and not existing.has_split:
        return candidate
    if candidate.total and not existing.total:
        return candidate
    return existing


def load_rac_allotments(truth_root: Path) -> tuple[dict[str, Allotment], list[dict[str, str]]]:
    allotments: dict[str, Allotment] = {}
    source_rows: list[dict[str, str]] = []

    for path in sorted(truth_root.glob("2026_rac_*.csv")):
        if any(token in path.name for token in RAC_EXCLUDE_TOKENS):
            continue
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "hunt_code" not in reader.fieldnames:
                continue
            for row in reader:
                hunt_code = clean(row.get("hunt_code")).upper()
                if not hunt_code:
                    continue
                res = to_int_text(row.get("permits_2026_res"))
                nr = to_int_text(row.get("permits_2026_nr"))
                total = row_total(row)
                if not (res or nr or total):
                    continue
                candidate = Allotment(
                    hunt_code=hunt_code,
                    res=res,
                    nr=nr,
                    total=total,
                    source_file=path.as_posix(),
                    source_document=clean(row.get("source_document")),
                    has_split=bool(res or nr),
                )
                allotments[hunt_code] = choose_allotment(allotments.get(hunt_code), candidate)
                source_rows.append(
                    {
                        "hunt_code": hunt_code,
                        "source_file": path.as_posix(),
                        "has_split": "yes" if candidate.has_split else "no",
                        "permit_allotment_2026_res": res,
                        "permit_allotment_2026_nr": nr,
                        "permit_allotment_2026_total": total,
                    }
                )
    return allotments, source_rows


def fallback_allotment(row: dict[str, str]) -> tuple[str, str, str]:
    res = to_int_text(row.get("permits_2026_res"))
    nr = to_int_text(row.get("permits_2026_nr"))
    total = to_int_text(row.get("permits_2026_total"))
    if not total:
        total = to_int_text(row.get("quota_2026_total"))
    if not total and (res or nr):
        total = str(int(res or 0) + int(nr or 0))
    return res, nr, total


def ensure_fields(fieldnames: Iterable[str]) -> list[str]:
    fields = list(fieldnames)
    for field in ALLOTMENT_FIELDS:
        if field not in fields:
            fields.append(field)
    return fields


def apply_to_csv(path: Path, allotments: dict[str, Allotment], write: bool, backup_dir: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "file": path.as_posix(),
            "status": "missing",
            "rows_checked": 0,
            "rac_rows": 0,
            "fallback_rows": 0,
            "blank_rows": 0,
            "changed_cells": 0,
            "written": False,
            "backup_path": "",
        }

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        original_fields = reader.fieldnames or []
        rows = list(reader)

    fields = ensure_fields(original_fields)
    changed_cells = 0
    rac_rows = 0
    fallback_rows = 0
    blank_rows = 0
    source_counts: Counter[str] = Counter()

    for row in rows:
        hunt_code = clean(row.get("hunt_code")).upper()
        before = {field: row.get(field, "") for field in ALLOTMENT_FIELDS}
        if hunt_code in allotments:
            allotment = allotments[hunt_code]
            row["permit_allotment_2026_res"] = allotment.res
            row["permit_allotment_2026_nr"] = allotment.nr
            row["permit_allotment_2026_total"] = allotment.total
            row["permit_allotment_2026_source"] = RAC_SOURCE_LABEL
            row["permit_allotment_2026_source_file"] = allotment.source_file
            row["permit_allotment_2026_status"] = (
                "RAC_CURRENT_YEAR_SPLIT" if allotment.has_split else "RAC_CURRENT_YEAR_TOTAL_ONLY"
            )
            rac_rows += 1
            source_counts[RAC_SOURCE_LABEL] += 1
        else:
            res, nr, total = fallback_allotment(row)
            row["permit_allotment_2026_res"] = res
            row["permit_allotment_2026_nr"] = nr
            row["permit_allotment_2026_total"] = total
            row["permit_allotment_2026_source"] = FALLBACK_SOURCE_LABEL if total or res or nr else ""
            row["permit_allotment_2026_source_file"] = clean(
                row.get("quota_source_file") or row.get("permits_2026_source") or row.get("truth_source_file")
            )
            row["permit_allotment_2026_status"] = "FALLBACK_EXISTING_2026_PERMITS" if total or res or nr else ""
            if total or res or nr:
                fallback_rows += 1
                source_counts[FALLBACK_SOURCE_LABEL] += 1
            else:
                blank_rows += 1

        for field in ALLOTMENT_FIELDS:
            if row.get(field, "") != before.get(field, ""):
                changed_cells += 1

    backup_path = ""
    if write and changed_cells:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = (backup_dir / path.name).as_posix()
        shutil.copy2(path, backup_path)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    return {
        "file": path.as_posix(),
        "status": "updated" if changed_cells else "unchanged",
        "rows_checked": len(rows),
        "rac_rows": rac_rows,
        "fallback_rows": fallback_rows,
        "blank_rows": blank_rows,
        "changed_cells": changed_cells,
        "written": bool(write and changed_cells),
        "backup_path": backup_path,
        "source_counts": dict(source_counts),
    }


def write_summary_csv(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "file",
        "status",
        "rows_checked",
        "rac_rows",
        "fallback_rows",
        "blank_rows",
        "changed_cells",
        "written",
        "backup_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth-root", default="pipeline/RAW/hunt_unit_database/2026/csv")
    parser.add_argument("--processed-root", default="processed_data")
    parser.add_argument("--write", action="store_true", help="Write runtime files. Default is dry-run only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    truth_root = Path(args.truth_root)
    processed_root = Path(args.processed_root)
    mode = "write" if args.write else "dry_run"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = processed_root / "backups" / f"current_year_allotment_overlay_{timestamp}"

    allotments, source_rows = load_rac_allotments(truth_root)
    reports = [
        apply_to_csv(Path(target), allotments, args.write, backup_dir)
        for target in TARGET_RUNTIME_FILES
    ]

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "truth_root": truth_root.as_posix(),
        "rac_current_year_allotment_source_label": RAC_SOURCE_LABEL,
        "fallback_source_label": FALLBACK_SOURCE_LABEL,
        "rac_direct_hunt_code_count": len(allotments),
        "rac_direct_rows_read": len(source_rows),
        "target_files": reports,
        "totals": {
            "rows_checked": sum(int(item["rows_checked"]) for item in reports),
            "rac_rows": sum(int(item["rac_rows"]) for item in reports),
            "fallback_rows": sum(int(item["fallback_rows"]) for item in reports),
            "blank_rows": sum(int(item["blank_rows"]) for item in reports),
            "changed_cells": sum(int(item["changed_cells"]) for item in reports),
            "files_written": sum(1 for item in reports if item["written"]),
        },
        "notes": [
            "RAC rows with direct hunt_code are canonical current-year allotments.",
            "Rows with total-only RAC source keep resident/nonresident allotment fields blank.",
            "Existing permits_2026 fields are used only when no direct RAC allotment row exists.",
            "Category-only RAC summaries without direct hunt_code are intentionally not expanded.",
        ],
    }

    report_path = processed_root / f"current_year_permit_allotment_overlay_{mode}.json"
    summary_path = processed_root / f"current_year_permit_allotment_overlay_{mode}_summary.csv"
    source_path = processed_root / "current_year_permit_allotment_rac_index.csv"

    processed_root.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_summary_csv(summary_path, reports)
    if args.write:
        with source_path.open("w", newline="", encoding="utf-8") as handle:
            fields = [
                "hunt_code",
                "source_file",
                "has_split",
                "permit_allotment_2026_res",
                "permit_allotment_2026_nr",
                "permit_allotment_2026_total",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(source_rows)

    print(json.dumps(report["totals"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
