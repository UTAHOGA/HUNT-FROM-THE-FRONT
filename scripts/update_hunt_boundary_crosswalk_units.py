#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from openpyxl import Workbook


def read_csv_fallback(path: Path):
    last = None
    for enc in ("utf-8-sig", "cp1252", "latin1"):
        try:
            with path.open(newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except Exception as e:
            last = e
    raise last


def main():
    parser = argparse.ArgumentParser(
        description="Update hunt boundary crosswalk unit column from harvest/generated tables."
    )
    parser.add_argument(
        "--crosswalk",
        default=r"processed_data\hunt_boundary_crosswalk_2026.csv",
        help="Crosswalk CSV path.",
    )
    parser.add_argument(
        "--scan-root",
        default=r"pipeline\RAW\hunt_unit_database",
        help="Root folder to scan for CSV files containing both hunt_code and unit columns.",
    )
    parser.add_argument(
        "--report-prefix",
        default=r"processed_data\hunt_boundary_crosswalk_2026_unit_fill",
        help="Output prefix for report files.",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    crosswalk_csv = (repo / args.crosswalk).resolve()
    crosswalk_xlsx = crosswalk_csv.with_suffix(".xlsx")
    scan_root = (repo / args.scan_root).resolve()
    report_prefix = (repo / args.report_prefix).resolve()
    report_json = report_prefix.with_name(report_prefix.name + "_report.json")
    report_csv = report_prefix.with_name(report_prefix.name + "_sources.csv")

    if not crosswalk_csv.exists():
        raise FileNotFoundError(f"Crosswalk not found: {crosswalk_csv}")
    if not scan_root.exists():
        raise FileNotFoundError(f"Scan root not found: {scan_root}")

    # Build mapping hunt_code -> set(unit values)
    unit_map: dict[str, set[str]] = {}
    source_rows = []
    scanned_files = 0
    contributing_files = 0
    for p in scan_root.rglob("*.csv"):
        scanned_files += 1
        try:
            rows = read_csv_fallback(p)
        except Exception:
            continue
        if not rows:
            continue
        keys = {k.lower(): k for k in rows[0].keys()}
        if "hunt_code" not in keys:
            continue
        unit_key = None
        if "unit" in keys:
            unit_key = keys["unit"]
        elif "unit_code" in keys:
            unit_key = keys["unit_code"]
        elif "unit_name" in keys:
            unit_key = keys["unit_name"]
        if unit_key is None:
            continue

        has_rows = False
        hc_key = keys["hunt_code"]
        for r in rows:
            hc_raw = str(r.get(hc_key, "") or "").strip()
            unit_val = str(r.get(unit_key, "") or "").strip()
            if not hc_raw or not unit_val:
                continue
            has_rows = True
            for hc in [x.strip().upper() for x in hc_raw.split(";") if x.strip()]:
                unit_map.setdefault(hc, set()).add(unit_val)
                source_rows.append(
                    {"source_file": str(p), "hunt_code": hc, "unit": unit_val}
                )
        if has_rows:
            contributing_files += 1

    # Apply to crosswalk
    with crosswalk_csv.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        cross_rows = list(reader)

    if "unit" not in headers:
        headers = ["unit"] + headers
        for r in cross_rows:
            r["unit"] = ""

    blank_before = sum(1 for r in cross_rows if not str(r.get("unit", "")).strip())
    updated = 0
    for r in cross_rows:
        hc = str(r.get("hunt_code", "")).strip().upper()
        if not hc:
            continue
        vals = unit_map.get(hc)
        if not vals:
            continue
        new_val = ";".join(sorted(vals))
        if str(r.get("unit", "")).strip() != new_val:
            r["unit"] = new_val
            updated += 1
    blank_after = sum(1 for r in cross_rows if not str(r.get("unit", "")).strip())

    with crosswalk_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(cross_rows)

    wb = Workbook()
    ws = wb.active
    ws.title = "crosswalk_2026"
    ws.append(headers)
    for r in cross_rows:
        ws.append([r.get(h, "") for h in headers])
    wb.save(crosswalk_xlsx)

    with report_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["source_file", "hunt_code", "unit"])
        w.writeheader()
        w.writerows(source_rows)

    report = {
        "crosswalk_csv": str(crosswalk_csv),
        "crosswalk_xlsx": str(crosswalk_xlsx),
        "scan_root": str(scan_root),
        "csv_files_scanned": scanned_files,
        "csv_files_contributing": contributing_files,
        "mapped_hunt_codes": len(unit_map),
        "rows_total": len(cross_rows),
        "blank_unit_before": blank_before,
        "blank_unit_after": blank_after,
        "rows_updated": updated,
        "source_report_csv": str(report_csv),
    }
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

