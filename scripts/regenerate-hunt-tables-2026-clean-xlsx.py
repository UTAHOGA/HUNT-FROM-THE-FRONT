from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font

ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"

HARVEST_PATHS = [
    ROOT / "processed_data" / "harvest_quality_features_all_years_by_hunt_code.csv",
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "harvest_quality_features_by_hunt_code_2025_for_2026.csv",
]

OUTPUT_DIR = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026" / "CLEAN_XLXS_STAGED"
MASTER_OUTPUT = OUTPUT_DIR / "MASTER.xlsx"
DISPLAY_OUTPUT = OUTPUT_DIR / "DISPLAY_READY.xlsx"

AUDIT_DIR = ROOT / "processed_data" / "audits"
AUDIT_PATH = AUDIT_DIR / "hunt_tables_2026_master_xlsx_validation.json"

# -------------------------
# MASTER (UNCHANGED)
# -------------------------
OUTPUT_COLUMNS = [
    "HUNT TYPE","SPECIES","SEX TYPE","WEAPON","HUNT CLASS","SEASON",
    "HUNT NAME","HUNT CODE",
    "2026 PERMITS RES","2026 PERMITS NR","2026 PERMITS TOTAL",
    "HARVEST YEAR","2026 HARVEST SUCCESS","2026 HARVEST AGE","2026 HARVEST DAYS",
]

# -------------------------
# DISPLAY (NEW)
# -------------------------
DISPLAY_COLUMNS = [
    "HUNT NAME","HUNT CODE","SEX","SPECIES","TYPE","WEAPON","SEASON",
    "PERMITS / HARVEST","2025 PERFORMANCE","SAT"
]

HEADER_FONT = Font(name="Arial", size=10)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="top", wrap_text=True)

# -------------------------
# HELPERS
# -------------------------
def clean_text(v): return str(v or "").strip()
def clean_code(v): return "".join(ch for ch in clean_text(v).upper() if ch.isalnum())

def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def resolve_harvest_path():
    for p in HARVEST_PATHS:
        if p.exists():
            return p
    return None

# -------------------------
# BUILD MASTER DATA
# -------------------------
def build_rows():
    db = read_csv_rows(DATABASE_PATH)
    harvest_path = resolve_harvest_path()
    harvest_lookup = {}

    if harvest_path:
        for r in read_csv_rows(harvest_path):
            if clean_text(r.get("model_target_year")) == "2026":
                code = clean_code(r.get("hunt_code"))
                harvest_lookup[code] = r

    rows = []

    for r in db:
        code = clean_code(r.get("hunt_code"))
        h = harvest_lookup.get(code, {})

        rows.append({
            "HUNT TYPE": clean_text(r.get("hunt_type")),
            "SPECIES": clean_text(r.get("species")),
            "SEX TYPE": clean_text(r.get("sex_type")),
            "WEAPON": clean_text(r.get("weapon")),
            "HUNT CLASS": clean_text(r.get("hunt_class")),
            "SEASON": clean_text(r.get("season")),
            "HUNT NAME": clean_text(r.get("hunt_name")),
            "HUNT CODE": code,

            "2026 PERMITS RES": clean_text(r.get("permits_2026_res")),
            "2026 PERMITS NR": clean_text(r.get("permits_2026_nr")),
            "2026 PERMITS TOTAL": clean_text(r.get("permits_2026_total")),

            "HARVEST YEAR": clean_text(h.get("reported_hunt_year")),
            "2026 HARVEST SUCCESS": clean_text(h.get("percent_success")),
            "2026 HARVEST AGE": clean_text(h.get("average_age")),
            "2026 HARVEST DAYS": clean_text(h.get("average_days")),
        })

    return rows, {}

# -------------------------
# WRITE MASTER
# -------------------------
def write_master(rows):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "MASTER"

    ws.append(OUTPUT_COLUMNS)

    for r in rows:
        ws.append([r.get(c, "") for c in OUTPUT_COLUMNS])

    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.alignment = CENTER

    wb.save(MASTER_OUTPUT)

# -------------------------
# BUILD DISPLAY ROW
# -------------------------
def build_display_row(r):
    permits = r.get("2026 PERMITS TOTAL") or "0"
    harvest = r.get("2026 HARVEST SUCCESS") or "0"

    success = r.get("2026 HARVEST SUCCESS") or "0"
    age = r.get("2026 HARVEST AGE") or "—"
    days = r.get("2026 HARVEST DAYS") or "—"

    return {
        "HUNT NAME": r.get("HUNT NAME"),
        "HUNT CODE": r.get("HUNT CODE"),
        "SEX": r.get("SEX TYPE"),
        "SPECIES": r.get("SPECIES"),
        "TYPE": r.get("HUNT TYPE"),
        "WEAPON": r.get("WEAPON"),
        "SEASON": r.get("SEASON"),

        "PERMITS / HARVEST": f"{permits} / {harvest}",
        "2025 PERFORMANCE": f"{success}% | {age}yr | {days}d",
        "SAT": "—"
    }

# -------------------------
# WRITE DISPLAY (THIS IS THE MAGIC)
# -------------------------
def write_display(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "DISPLAY"

    ws.append(DISPLAY_COLUMNS)

    for r in rows:
        d = build_display_row(r)
        ws.append([d.get(c, "") for c in DISPLAY_COLUMNS])

    # STYLE
    for cell in ws[1]:
        cell.font = Font(name="Arial", size=10, bold=True)
        cell.alignment = CENTER

    # COLUMN WIDTHS (FIXES YOUR "TOO WIDE" ISSUE)
    widths = [30, 12, 8, 12, 14, 14, 20, 18, 22, 12]

    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w

    # ALIGNMENT
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if cell.column in (1, 7):  # name + season
                cell.alignment = LEFT
            else:
                cell.alignment = CENTER

    wb.save(DISPLAY_OUTPUT)

# -------------------------
# MAIN
# -------------------------

def write_display(rows):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "DISPLAY"

    headers = [
        "HUNT NAME","HUNT CODE","SEX","SPECIES","TYPE","WEAPON","SEASON",
        "PERMITS / HARVEST","2025 PERFORMANCE","SAT"
    ]

    ws.append(headers)

    for r in rows:
        permits = r.get("2026 PERMITS TOTAL") or "0"
        harvest = r.get("2026 HARVEST SUCCESS") or "0"

        success = r.get("2026 HARVEST SUCCESS") or "0"
        age = r.get("2026 HARVEST AGE") or "—"
        days = r.get("2026 HARVEST DAYS") or "—"

        ws.append([
            r.get("HUNT NAME"),
            r.get("HUNT CODE"),
            r.get("SEX TYPE"),
            r.get("SPECIES"),
            r.get("HUNT TYPE"),
            r.get("WEAPON"),
            r.get("SEASON"),
            f"{permits} / {harvest}",
            f"{success}% | {age}yr | {days}d",
            "—"
        ])

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    output_path = OUTPUT_DIR / "DISPLAY_READY.xlsx"
    wb.save(output_path)
def main() -> None:
    rows, audit = build_rows()

    write_workbook(rows)

    # 🔥 THIS IS THE ONLY NEW THING
    write_display(rows)

    validate_workbook(rows, audit)

    print("MASTER + DISPLAY GENERATED")
    print(DISPLAY_OUTPUT)

if __name__ == "__main__":
    main()