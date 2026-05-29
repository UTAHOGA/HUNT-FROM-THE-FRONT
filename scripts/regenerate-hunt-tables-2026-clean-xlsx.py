from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
HUNTS_DIR = ROOT / "processed_data" / "hunt_research_2026_split" / "hunts"
AGE_LATEST_CSV = ROOT / "processed_data" / "harvest_age_features_by_hunt_code_latest.csv"
OUT_BASE = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026"
LIVE_XLSX_DIR = OUT_BASE / "XLXS"
STAGE_XLSX_DIR = OUT_BASE / "CLEAN_XLXS_STAGED"
AUDIT_CSV = ROOT / "processed_data" / "audits" / "hunt_tables_2026_clean_xlsx_regeneration_audit.csv"
YEAR = "2026"

# Do not add modeled/inferred age values. AVERAGE HARVEST AGE is populated
# only when an actual average_harvest_age value already exists in source data.
HEADERS = [
    "HUNT CODE",
    "HUNT NAME",
    "SPECIES",
    "SEX TYPE",
    "HUNT_CLASS",
    "AVERAGE HARVEST AGE",
]

HUNT_CLASS_ABBREVIATIONS = {
    "once in a lifetime": "O.I.L",
    "premium limited entry": "P.L.E",
    "limited entry private land only": "L.E PRIVATE LAND ONLY",
    "limited entry private lands only": "L.E PRIVATE LAND ONLY",
    "limited entry": "L.E",
    "general season private land": "GENERAL SEASON PRIVATE LAND",
    "general season private lands": "GENERAL SEASON PRIVATE LAND",
    "general season": "GENERAL SEASON",
    "extended archery": "EXTENDED ARCHERY",
    "conservation permit": "CONSERVATION PERMIT",
    "conservation": "CONSERVATION PERMIT",
    "cwmu": "CWMU",
    "sportsman permit": "SPORTSMAN PERMIT",
    "sportsman": "SPORTSMAN PERMIT",
    "harvest objective": "HARVEST OBJECTIVE",
    "pursuit": "PURSUIT",
    "hunter choice": "HUNTER CHOICE",
    "management buck": "MANAGEMENT BUCK",
    "statewide": "STATEWIDE",
    "draw": "DRAW",
}

CLASS_SORT = [
    "O.I.L",
    "P.L.E",
    "L.E",
    "GENERAL SEASON",
    "EXTENDED ARCHERY",
    "CWMU",
    "CONSERVATION PERMIT",
    "SPORTSMAN PERMIT",
    "HARVEST OBJECTIVE",
    "PURSUIT",
    "DRAW",
    "STATEWIDE",
]


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def clean_number(value: object) -> str:
    text = norm(value)
    if not text:
        return ""
    try:
        n = float(text.replace(",", ""))
    except ValueError:
        return text
    if n == 0:
        return ""
    if n.is_integer():
        return str(int(n))
    return f"{n:.2f}".rstrip("0").rstrip(".")


def clean_filename_part(value: object) -> str:
    text = norm(value).upper()
    text = text.replace("LIMITED ENTRY", "L.E")
    text = text.replace("PREMIUM L.E", "P.L.E")
    text = text.replace("PRIVATE LANDS", "PRIVATE LAND")
    text = re.sub(r"[^A-Z0-9 .+&'-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "UNKNOWN"


def canonical_class(value: object) -> str:
    raw = norm(value)
    if not raw:
        return ""
    low = raw.lower().replace("-", " ")
    low = re.sub(r"\s+", " ", low).strip()
    for key, replacement in HUNT_CLASS_ABBREVIATIONS.items():
        if key in low:
            return replacement
    return clean_filename_part(raw)


def existing_hunt_class(record: dict) -> str:
    for key in ("hunt_class", "hunt_type", "permit_allocation_type", "allocation_type"):
        val = canonical_class(record.get(key))
        if val:
            return val
    return ""


def load_age_latest() -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not AGE_LATEST_CSV.exists():
        return out
    with AGE_LATEST_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            code = norm(row.get("hunt_code") or row.get("current_hunt_code")).upper()
            age = clean_number(row.get("average_harvest_age"))
            # No proxies. Do not use percent_5plus, adult male/female percentages,
            # quality scores, modeled fields, or any computed substitute.
            if code and age:
                out.setdefault(code, age)
    return out


def average_harvest_age(record: dict, age_latest: Dict[str, str]) -> str:
    for key in ("average_harvest_age", "avg_harvest_age", "harvest_average_age"):
        age = clean_number(record.get(key))
        if age:
            return age
    code = norm(record.get("hunt_code")).upper()
    return age_latest.get(code, "")


def row_from_record(record: dict, age_latest: Dict[str, str]) -> dict:
    return {
        "HUNT CODE": norm(record.get("hunt_code")).upper(),
        "HUNT NAME": norm(record.get("hunt_name") or record.get("dwr_unit_name") or record.get("unit_name")),
        "SPECIES": norm(record.get("species")),
        "SEX TYPE": norm(record.get("sex_type")),
        "HUNT_CLASS": existing_hunt_class(record),
        "AVERAGE HARVEST AGE": average_harvest_age(record, age_latest),
    }


def load_rows() -> List[dict]:
    if not HUNTS_DIR.exists():
        raise SystemExit(f"Missing canonical split hunt directory: {HUNTS_DIR}")
    age_latest = load_age_latest()
    rows: List[dict] = []
    for path in sorted(HUNTS_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            print(f"WARN skipped unreadable JSON {path.name}: {exc}")
            continue
        row = row_from_record(record, age_latest)
        if row["HUNT CODE"]:
            rows.append(row)
    rows.sort(key=lambda r: (r["SPECIES"], r["SEX TYPE"], r["HUNT_CLASS"], r["HUNT CODE"], r["HUNT NAME"]))
    return rows


def class_sort_key(hunt_class: str) -> Tuple[int, str]:
    c = clean_filename_part(hunt_class)
    for idx, marker in enumerate(CLASS_SORT):
        if marker in c:
            return idx, c
    return len(CLASS_SORT), c


def group_rows(rows: Iterable[dict]) -> Dict[Tuple[str, str, str], List[dict]]:
    groups: Dict[Tuple[str, str, str], List[dict]] = defaultdict(list)
    for row in rows:
        species = clean_filename_part(row["SPECIES"])
        sex_type = clean_filename_part(row["SEX TYPE"] or "ALL")
        hunt_class = clean_filename_part(row["HUNT_CLASS"] or "UNCLASSIFIED")
        groups[(species, sex_type, hunt_class)].append(row)
    return groups


def output_stem(species: str, sex_type: str, hunt_class: str) -> str:
    return re.sub(r"\s+", " ", f"{YEAR} {species} {sex_type} {hunt_class}").strip(" .")


def write_xlsx(path: Path, rows: List[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Hunt Table"

    for col_idx, header in enumerate(HEADERS, start=1):
        ws.cell(row=1, column=col_idx, value=header)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, header in enumerate(HEADERS, start=1):
            ws.cell(row=row_idx, column=col_idx, value=row.get(header, ""))

    header_fill = PatternFill(fill_type="solid", fgColor="4F2D1D")
    odd_fill = PatternFill(fill_type="solid", fgColor="FBF6EF")
    even_fill = PatternFill(fill_type="solid", fgColor="F3E8DA")
    side = Side(style="thin", color="C7B59F")
    grid = Border(left=side, right=side, top=side, bottom=side)

    for cell in ws[1]:
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
        cell.fill = header_fill
        cell.border = grid
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 24

    for row_idx in range(2, ws.max_row + 1):
        fill = odd_fill if row_idx % 2 == 0 else even_fill
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = Font(name="Calibri", size=10)
            cell.fill = fill
            cell.border = grid
            if HEADERS[col_idx - 1] == "AVERAGE HARVEST AGE":
                cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=False)
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)

    widths = {
        "HUNT CODE": 13,
        "HUNT NAME": 42,
        "SPECIES": 20,
        "SEX TYPE": 14,
        "HUNT_CLASS": 28,
        "AVERAGE HARVEST AGE": 21,
    }
    for col_idx, header in enumerate(HEADERS, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = widths[header]

    table_ref = f"A1:{get_column_letter(len(HEADERS))}{max(ws.max_row, 2)}"
    table = Table(displayName="HUNT_TABLE", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    ws.add_table(table)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = table_ref

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.2, right=0.2, top=0.25, bottom=0.25, header=0.15, footer=0.15)
    ws.print_options.horizontalCentered = True
    ws.print_options.verticalCentered = False
    ws.print_title_rows = "$1:$1"

    wb.save(path)
    wb.close()


def prepare_stage() -> None:
    if STAGE_XLSX_DIR.exists():
        shutil.rmtree(STAGE_XLSX_DIR)
    STAGE_XLSX_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)


def publish_staged() -> None:
    LIVE_XLSX_DIR.mkdir(parents=True, exist_ok=True)
    for old in LIVE_XLSX_DIR.glob("*.xlsx"):
        old.unlink()
    for staged in STAGE_XLSX_DIR.glob("*.xlsx"):
        shutil.copy2(staged, LIVE_XLSX_DIR / staged.name)


def write_audit(audit_rows: List[dict]) -> None:
    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file", "rows", "average_harvest_age_rows", "status"])
        writer.writeheader()
        writer.writerows(audit_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bottom-up regenerate clean 2026 hunt table XLSX files from canonical hunt JSON.")
    parser.add_argument("--publish", action="store_true", help="Replace live 2026 XLXS folder after staging succeeds.")
    args = parser.parse_args()

    prepare_stage()
    rows = load_rows()
    groups = group_rows(rows)
    audit_rows: List[dict] = []

    for key in sorted(groups.keys(), key=lambda k: (k[0], k[1], class_sort_key(k[2]))):
        species, sex_type, hunt_class = key
        group = sorted(groups[key], key=lambda r: (r["HUNT CODE"], r["HUNT NAME"]))
        stem = output_stem(species, sex_type, hunt_class)
        xlsx = STAGE_XLSX_DIR / f"{stem}.xlsx"
        write_xlsx(xlsx, group)
        age_count = sum(1 for row in group if norm(row.get("AVERAGE HARVEST AGE")))
        audit_rows.append({"file": xlsx.name, "rows": len(group), "average_harvest_age_rows": age_count, "status": "OK"})
        print(f"OK {xlsx.name} rows={len(group)} average_harvest_age_rows={age_count}")

    write_audit(audit_rows)
    if args.publish:
        publish_staged()
        print(f"PUBLISHED {LIVE_XLSX_DIR}")
    else:
        print(f"STAGED {STAGE_XLSX_DIR}")
    print(f"AUDIT {AUDIT_CSV}")


if __name__ == "__main__":
    main()
