"""Normalize and reconcile 2026 permit columns against DATABASE truth.

Designed for species truth CSVs that may contain:
- text labels inside permit cells (e.g., "Res: 5", "NonRes: 1", "Total: 6")
- non-res continuation rows that should be moved up then deleted
- blank/different permit cells that should be synchronized from DATABASE

Default behavior excludes Expo/Conservation rows and reconciles all other rows.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_int(value: object) -> int | None:
    text = clean(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None
    return int(match.group(0))


def is_blank_metadata(row: dict[str, str]) -> bool:
    return not any(
        clean(row.get(col))
        for col in ("hunt_name", "hunt_code", "species", "sex_type", "weapon", "hunt_type", "hunt_class", "season")
    )


def find_column(fieldnames: list[str], aliases: list[str]) -> str:
    lower_map = {name.lower(): name for name in fieldnames}
    for alias in aliases:
        if alias.lower() in lower_map:
            return lower_map[alias.lower()]
    raise ValueError(f"Missing expected column; tried aliases: {aliases}")


def pick_db_truth(row: dict[str, str], year: int, suffix: str) -> int | None:
    primary = parse_int(row.get(f"permits_{year}_{suffix}"))
    if primary is not None:
        return primary
    fallback = parse_int(row.get(f"permit_allotment_{year}_{suffix}"))
    return fallback


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-csv", required=True, help="Target species CSV to reconcile.")
    parser.add_argument(
        "--database-csv",
        default="pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
        help="Canonical DATABASE.csv path.",
    )
    parser.add_argument("--year", type=int, default=2026, help="Permit year to reconcile.")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.80,
        help="If current-to-database similarity is at or above this value, overwrite mismatches; otherwise fill blanks only.",
    )
    parser.add_argument(
        "--include-special",
        action="store_true",
        help="Include Expo/Conservation rows. Default excludes them.",
    )
    parser.add_argument("--write", action="store_true", help="Write changes to target CSV.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_path = Path(args.target_csv)
    database_path = Path(args.database_csv)
    year = args.year

    if not target_path.exists():
        raise FileNotFoundError(f"Missing target CSV: {target_path}")
    if not database_path.exists():
        raise FileNotFoundError(f"Missing DATABASE CSV: {database_path}")

    with target_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    permit_res_col = find_column(fields, [f"{year} permits res", f"permits_{year}_res"])
    permit_nr_col = find_column(fields, [f"{year} permits non-res", f"{year} permits nr", f"permits_{year}_nr"])
    permit_total_col = find_column(fields, [f"{year} permits total", f"permits_{year}_total"])

    required = {"hunt_name", "hunt_code", "hunt_type", "hunt_class"}
    missing = sorted(col for col in required if col not in fields)
    if missing:
        raise ValueError(f"Target CSV missing required columns: {', '.join(missing)}")

    with database_path.open("r", encoding="utf-8-sig", newline="") as handle:
        db_rows = list(csv.DictReader(handle))

    db_by_code: dict[str, tuple[int | None, int | None, int | None, dict[str, str]]] = {}
    for db in db_rows:
        code = upper(db.get("hunt_code"))
        if not code:
            continue
        db_by_code[code] = (
            pick_db_truth(db, year, "res"),
            pick_db_truth(db, year, "nr"),
            pick_db_truth(db, year, "total"),
            db,
        )

    moved_nonres = 0
    deleted_lines: list[int] = []
    for idx in range(1, len(rows)):
        row = rows[idx]
        prev = rows[idx - 1]
        if not is_blank_metadata(row):
            continue
        probe_text = " ".join([clean(row.get(permit_res_col)), clean(row.get(permit_nr_col)), clean(row.get(permit_total_col))])
        if "NONRES" not in upper(probe_text) and parse_int(probe_text) is None:
            continue
        if not clean(prev.get("hunt_code")):
            continue
        incoming = parse_int(row.get(permit_res_col))
        if incoming is None:
            incoming = parse_int(row.get(permit_nr_col))
        if incoming is None:
            incoming = parse_int(row.get(permit_total_col))
        if incoming is None:
            continue
        prev_nr = parse_int(prev.get(permit_nr_col))
        if prev_nr is None or prev_nr == 0:
            prev[permit_nr_col] = str(incoming)
            moved_nonres += 1
            deleted_lines.append(idx)

    if deleted_lines:
        rows = [row for i, row in enumerate(rows) if i not in set(deleted_lines)]

    normalized_cells = 0
    for row in rows:
        res_text = clean(row.get(permit_res_col))
        nr_text = clean(row.get(permit_nr_col))
        total_text = clean(row.get(permit_total_col))

        res_num = parse_int(res_text)
        nr_num = parse_int(nr_text)
        total_num = parse_int(total_text)

        if "TOTAL" in upper(res_text) and total_num is None and res_num is not None:
            row[permit_total_col] = str(res_num)
            row[permit_res_col] = ""
            total_num = res_num
            res_num = None
            normalized_cells += 1

        if "RES" in upper(res_text) and "NONRES" not in upper(res_text) and res_num is not None and res_text != str(res_num):
            row[permit_res_col] = str(res_num)
            normalized_cells += 1
        if "NONRES" in upper(res_text) and nr_num is None and res_num is not None:
            row[permit_nr_col] = str(res_num)
            row[permit_res_col] = ""
            nr_num = res_num
            res_num = None
            normalized_cells += 1
        if "NONRES" in upper(nr_text) and nr_num is not None and nr_text != str(nr_num):
            row[permit_nr_col] = str(nr_num)
            normalized_cells += 1
        if "TOTAL" in upper(total_text) and total_num is not None and total_text != str(total_num):
            row[permit_total_col] = str(total_num)
            normalized_cells += 1

        if total_num is None and res_num is not None and nr_num is not None:
            row[permit_total_col] = str(res_num + nr_num)
            normalized_cells += 1

    comparisons = 0
    matches = 0
    for row in rows:
        code = upper(row.get("hunt_code"))
        if code not in db_by_code:
            continue
        db_res, db_nr, db_total, _db_row = db_by_code[code]
        cur_vals = [parse_int(row.get(permit_res_col)), parse_int(row.get(permit_nr_col)), parse_int(row.get(permit_total_col))]
        db_vals = [db_res, db_nr, db_total]
        for cur, truth in zip(cur_vals, db_vals):
            if cur is None or truth is None:
                continue
            comparisons += 1
            if cur == truth:
                matches += 1

    similarity = 1.0 if comparisons == 0 else (matches / comparisons)
    allow_overwrite = similarity >= args.similarity_threshold

    changes: list[dict[str, object]] = []
    skip_counts: dict[str, int] = defaultdict(int)
    filled_blanks = 0
    overwritten = 0
    unresolved_mismatch = 0

    for line_no, row in enumerate(rows, start=2):
        code = upper(row.get("hunt_code"))
        if not code:
            skip_counts["missing_hunt_code"] += 1
            continue
        if code not in db_by_code:
            skip_counts["hunt_code_not_in_database"] += 1
            continue

        _, _, _, db_row = db_by_code[code]
        is_special = any(
            token in upper(
                " ".join(
                    [
                        clean(row.get("hunt_name")),
                        clean(row.get("hunt_type")),
                        clean(row.get("hunt_class")),
                        clean(db_row.get("hunt_name")),
                        clean(db_row.get("hunt_type")),
                        clean(db_row.get("hunt_class")),
                    ]
                )
            )
            for token in ("EXPO", "CONSERVATION")
        )
        if is_special and not args.include_special:
            skip_counts["excluded_special_expo_conservation"] += 1
            continue

        db_res, db_nr, db_total, _ = db_by_code[code]
        truth_map = {
            permit_res_col: db_res,
            permit_nr_col: db_nr,
            permit_total_col: db_total,
        }

        before = {
            permit_res_col: clean(row.get(permit_res_col)),
            permit_nr_col: clean(row.get(permit_nr_col)),
            permit_total_col: clean(row.get(permit_total_col)),
        }

        row_changed = False
        for col, truth in truth_map.items():
            if truth is None:
                continue
            current = parse_int(row.get(col))
            if current is None:
                row[col] = str(truth)
                filled_blanks += 1
                row_changed = True
                continue
            if current != truth:
                if allow_overwrite:
                    row[col] = str(truth)
                    overwritten += 1
                    row_changed = True
                else:
                    unresolved_mismatch += 1

        if row_changed:
            changes.append(
                {
                    "line": line_no,
                    "hunt_code": code,
                    "before": before,
                    "after": {
                        permit_res_col: clean(row.get(permit_res_col)),
                        permit_nr_col: clean(row.get(permit_nr_col)),
                        permit_total_col: clean(row.get(permit_total_col)),
                    },
                }
            )

    backup_file = ""
    if args.write and (changes or moved_nonres or normalized_cells):
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup = target_path.with_name(f"{target_path.stem}.backup_permit_reconcile_{stamp}{target_path.suffix}")
        shutil.copy2(target_path, backup)
        backup_file = str(backup)
        with target_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    report = {
        "mode": "write" if args.write else "dry_run",
        "target_csv": str(target_path),
        "database_csv": str(database_path),
        "year": year,
        "similarity_threshold": args.similarity_threshold,
        "similarity_ratio": round(similarity, 6),
        "allow_overwrite_mismatches": allow_overwrite,
        "rows_checked": len(rows),
        "changes": len(changes),
        "moved_nonres_rows": moved_nonres,
        "deleted_nonres_continuation_rows": len(deleted_lines),
        "normalized_cells": normalized_cells,
        "filled_blank_cells": filled_blanks,
        "overwritten_mismatch_cells": overwritten,
        "unresolved_mismatch_cells": unresolved_mismatch,
        "skip_counts": dict(skip_counts),
        "backup_file": backup_file,
        "permit_columns": {
            "res": permit_res_col,
            "nr": permit_nr_col,
            "total": permit_total_col,
        },
        "sample_changes": changes[:40],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
