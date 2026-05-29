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
DATABASE_CSV = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
OUT_BASE = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026"
LIVE_XLSX_DIR = OUT_BASE / "XLXS"
STAGE_XLSX_DIR = OUT_BASE / "CLEAN_XLXS_STAGED"
AUDIT_CSV = ROOT / "processed_data" / "audits" / "hunt_tables_2026_clean_xlsx_regeneration_audit.csv"
YEAR = "2026"

# Public display headers. NOTES intentionally moved to the final column.
HEADERS = [
    "hunt_name",
    "hunt_code",
    "sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "NOTES",
    "Harvest Prior Year",
    "Percent Harvest Success (previous hunting season)",
    "Average Age Harvested (previous hunting season)",
    "Avg Days Hunted (previous hunting season)",
]

COLUMN_WIDTHS = {
    "hunt_name": 24,
    "hunt_code": 10,
    "sex_type": 10,
    "species": 12,
    "weapon": 16,
    "hunt_type": 18,
    "season": 22,
    "permits_2026_res": 10,
    "permits_2026_nr": 10,
    "permits_2026_total": 11,
    "NOTES": 22,
    "Harvest Prior Year": 11,
    "Percent Harvest Success (previous hunting season)": 14,
    "Average Age Harvested (previous hunting season)": 14,
    "Avg Days Hunted (previous hunting season)": 14,
}

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


def normalize_code(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def norm_name(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def clean_number(value: object, *, allow_zero: bool = False) -> str:
    text = norm(value)
    if not text:
        return ""
    try:
        n = float(text.replace(",", "").replace("%", ""))
    except ValueError:
        return text
    if n == 0 and not allow_zero:
        return ""
    if n.is_integer():
        return str(int(n))
    return f"{n:.2f}".rstrip("0").rstrip(".")


def first_value(record: dict, keys: Iterable[str]) -> object:
    for key in keys:
        if key in record and norm(record.get(key)):
            return record.get(key)
    return ""


def clean_filename_part(value: object) -> str:
    text = norm(value).upper()
    text = text.replace("LIMITED ENTRY", "L.E")
    text = text.replace("PREMIUM L.E", "P.L.E")
    text = text.replace("PRIVATE LANDS", "PRIVATE LAND")
    text = re.sub(r"[^A-Z0-9 .+&'-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or "UNKNOWN"


def norm_compare(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm(value).lower())


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
    for key in ("hunt_class", "permit_allocation_type", "allocation_type"):
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


def load_database_lookup() -> tuple[Dict[str, dict], Dict[tuple[str, str], dict]]:
    by_code: Dict[str, dict] = {}
    by_name: Dict[tuple[str, str], dict] = {}
    if not DATABASE_CSV.exists():
        print(f"WARN missing DATABASE.csv season/permit enrichment source: {DATABASE_CSV}")
        return by_code, by_name

    with DATABASE_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            clean_row = {key: norm(value) for key, value in row.items()}
            code = normalize_code(clean_row.get("hunt_code"))
            if code:
                by_code[code] = clean_row
            name_key = (norm_name(clean_row.get("species")), norm_name(clean_row.get("hunt_name")))
            if all(name_key):
                by_name.setdefault(name_key, clean_row)

    print(f"Loaded DATABASE.csv enrichment rows: code={len(by_code)} name={len(by_name)}")
    return by_code, by_name


def database_row_for(record: dict, database_lookup: tuple[Dict[str, dict], Dict[tuple[str, str], dict]]) -> dict:
    by_code, by_name = database_lookup
    code = normalize_code(record.get("hunt_code"))
    if code and code in by_code:
        return by_code[code]
    name_key = (norm_name(record.get("species")), norm_name(record.get("hunt_name")))
    if all(name_key):
        return by_name.get(name_key, {})
    return {}


def first_record_or_database(record: dict, database_row: dict, keys: Iterable[str]) -> object:
    for key in keys:
        value = record.get(key)
        if norm(value):
            return value
    for key in keys:
        value = database_row.get(key)
        if norm(value):
            return value
    return ""


def note_path_from_database(database_row: dict) -> Path | None:
    note_ref = norm(database_row.get("NOTES") or database_row.get("notes"))
    if not note_ref or not note_ref.lower().endswith(".md"):
        return None
    candidates = [
        ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / note_ref.replace("../", ""),
        ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "notes" / "DATABASE" / Path(note_ref).name,
        ROOT / note_ref,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def season_from_note(database_row: dict) -> str:
    note_path = note_path_from_database(database_row)
    if not note_path:
        return ""
    text = note_path.read_text(encoding="utf-8-sig", errors="ignore")
    for line in text.splitlines():
        clean = norm(line.lstrip("-# "))
        if "season" not in clean.lower():
            continue
        # Keep the visitor-facing sentence, not the whole notes document.
        sentence = re.split(r"(?<=[.!?])\s+", clean)[0]
        if sentence:
            return sentence[:180]
    return ""


def average_harvest_age(record: dict, age_latest: Dict[str, str]) -> str:
    for key in ("average_harvest_age", "avg_harvest_age", "harvest_average_age"):
        age = clean_number(record.get(key))
        if age:
            return age
    code = norm(record.get("hunt_code")).upper()
    return age_latest.get(code, "")


def permit_value(record: dict, database_row: dict, keys: Iterable[str]) -> str:
    return clean_number(first_record_or_database(record, database_row, keys), allow_zero=False)


def notes_value(record: dict, database_row: dict) -> str:
    for key in ("notes", "note", "permit_status", "data_status"):
        val = norm(record.get(key))
        if val:
            return val.replace("SOURCE_CONFIRMED_", "").replace("NO_QUOTA_PUBLISHED", "No quota published")[:90]
    for key in ("NOTES", "notes", "note", "permit_status", "data_status"):
        val = norm(database_row.get(key))
        if val:
            return val.replace("SOURCE_CONFIRMED_", "").replace("NO_QUOTA_PUBLISHED", "No quota published")[:90]
    return ""


def row_from_record(record: dict, age_latest: Dict[str, str], database_lookup: tuple[Dict[str, dict], Dict[tuple[str, str], dict]]) -> dict:
    database_row = database_row_for(record, database_lookup)
    permits_res = permit_value(record, database_row, ("permits_2026_res", "permits_res", "resident_permits", "permits_resident", "res_permits"))
    permits_nr = permit_value(record, database_row, ("permits_2026_nr", "permits_nr", "nonresident_permits", "non_resident_permits", "nonres_permits", "nr_permits"))
    permits_total = permit_value(record, database_row, ("permits_2026_total", "permits_total", "recommended_permits", "total_permits", "permits"))
    hunt_class = existing_hunt_class(record) or canonical_class(database_row.get("hunt_class"))
    hunt_type = norm(record.get("hunt_type")) or norm(database_row.get("hunt_type")) or hunt_class

    # Do not derive RES/NR from TOTAL. If only total exists, RES and NR stay blank.
    season = norm(first_record_or_database(record, database_row, ("season", "season_dates", "dates", "season_date")))
    if not season:
        season = season_from_note(database_row)

    return {
        "hunt_name": norm(first_record_or_database(record, database_row, ("hunt_name", "dwr_unit_name", "unit_name"))),
        "hunt_code": normalize_code(first_record_or_database(record, database_row, ("hunt_code",))),
        "sex_type": norm(first_record_or_database(record, database_row, ("sex_type",))),
        "species": norm(first_record_or_database(record, database_row, ("species",))),
        "weapon": norm(first_record_or_database(record, database_row, ("weapon",))),
        "hunt_type": hunt_type,
        "season": season,
        "permits_2026_res": permits_res,
        "permits_2026_nr": permits_nr,
        "permits_2026_total": permits_total,
        "NOTES": notes_value(record, database_row),
        "Harvest Prior Year": clean_number(first_value(record, ("harvest_prior_year", "prior_year_harvest", "previous_harvest", "harvest")), allow_zero=False),
        "Percent Harvest Success (previous hunting season)": clean_number(first_value(record, ("percent_harvest_success", "percent_success", "success_percent", "previous_percent_success")), allow_zero=True),
        "Average Age Harvested (previous hunting season)": average_harvest_age(record, age_latest),
        "Avg Days Hunted (previous hunting season)": clean_number(first_value(record, ("avg_days_hunted", "average_days_hunted", "avg_days", "days_hunted")), allow_zero=False),
        "_hunt_class": hunt_class,
        "_database_join": "code" if database_row and normalize_code(record.get("hunt_code")) in database_lookup[0] else ("name" if database_row else "missing"),
    }


def load_rows() -> List[dict]:
    if not HUNTS_DIR.exists():
        raise SystemExit(f"Missing canonical split hunt directory: {HUNTS_DIR}")
    age_latest = load_age_latest()
    database_lookup = load_database_lookup()
    rows: List[dict] = []
    for path in sorted(HUNTS_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            print(f"WARN skipped unreadable JSON {path.name}: {exc}")
            continue
        row = row_from_record(record, age_latest, database_lookup)
        if row["hunt_code"]:
            rows.append(row)
    rows.sort(key=lambda r: (r["species"], r["sex_type"], r["hunt_type"], r["weapon"], r.get("_hunt_class", ""), r["hunt_code"], r["hunt_name"]))
    return rows


def class_sort_key(hunt_class: str) -> Tuple[int, str]:
    c = clean_filename_part(hunt_class)
    for idx, marker in enumerate(CLASS_SORT):
        if marker in c:
            return idx, c
    return len(CLASS_SORT), c


def base_group_key(row: dict) -> Tuple[str, str, str, str]:
    return (
        clean_filename_part(row["species"]),
        clean_filename_part(row["sex_type"] or "ALL"),
        clean_filename_part(row["hunt_type"] or "UNCLASSIFIED"),
        clean_filename_part(row["weapon"] or "ANY WEAPON"),
    )


def hunt_class_divider_needed(rows: List[dict]) -> bool:
    classes = {clean_filename_part(row.get("_hunt_class") or "") for row in rows if norm(row.get("_hunt_class"))}
    if len(classes) <= 1:
        return False
    # If the class is already present in the hunt_type text, do not duplicate it in the file split.
    base_type = clean_filename_part(rows[0].get("hunt_type") or "")
    return any(norm_compare(c) and norm_compare(c) not in norm_compare(base_type) for c in classes)


def group_rows(rows: Iterable[dict]) -> Dict[Tuple[str, str, str, str, str], List[dict]]:
    base_groups: Dict[Tuple[str, str, str, str], List[dict]] = defaultdict(list)
    for row in rows:
        base_groups[base_group_key(row)].append(row)

    final_groups: Dict[Tuple[str, str, str, str, str], List[dict]] = defaultdict(list)
    for base_key, base_rows in base_groups.items():
        if hunt_class_divider_needed(base_rows):
            for row in base_rows:
                class_part = clean_filename_part(row.get("_hunt_class") or "UNCLASSIFIED")
                final_groups[(*base_key, class_part)].append(row)
        else:
            final_groups[(*base_key, "")].extend(base_rows)
    return final_groups


def output_stem(species: str, sex_type: str, hunt_type: str, weapon: str, hunt_class: str = "") -> str:
    parts = [YEAR, species, sex_type, hunt_type, weapon]
    if hunt_class and norm_compare(hunt_class) not in norm_compare(" ".join(parts)):
        parts.append(hunt_class)
    return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip(" .")


def style_workbook(ws, row_count: int) -> None:
    header_fill = PatternFill(fill_type="solid", fgColor="5B301B")
    odd_fill = PatternFill(fill_type="solid", fgColor="F7F1E8")
    even_fill = PatternFill(fill_type="solid", fgColor="EFE5D7")
    side = Side(style="thin", color="C58F61")
    border = Border(left=side, right=side, top=side, bottom=side)

    for col, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = COLUMN_WIDTHS[header]

    for row in range(2, row_count + 2):
        fill = odd_fill if row % 2 == 0 else even_fill
        for col in range(1, len(HEADERS) + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = fill
            cell.border = border
            cell.font = Font(name="Calibri", size=11, color="000000")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[row].height = 42

    ws.row_dimensions[1].height = 45
    ws.freeze_panes = "A2"
    last_row = max(2, row_count + 1)
    table_ref = f"A1:{get_column_letter(len(HEADERS))}{last_row}"
    ws.auto_filter.ref = table_ref
    table = Table(displayName="HUNT_TABLE", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    ws.add_table(table)

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LEGAL
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins = PageMargins(left=0.15, right=0.15, top=0.25, bottom=0.25, header=0.1, footer=0.1)
    ws.print_options.horizontalCentered = True
    ws.print_options.verticalCentered = False
    ws.print_title_rows = "$1:$1"


def write_xlsx(path: Path, rows: List[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Hunt Table"
    ws.append(HEADERS)
    for row in rows:
        ws.append([row.get(header, "") for header in HEADERS])
    style_workbook(ws, len(rows))
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
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "file",
                "rows",
                "species",
                "sex_type",
                "hunt_type",
                "weapon",
                "hunt_class_split",
                "res_permit_rows",
                "nr_permit_rows",
                "total_permit_rows",
                "season_rows",
                "average_harvest_age_rows",
                "notes_rows",
                "database_code_join_rows",
                "database_name_join_rows",
                "database_missing_join_rows",
                "status",
            ],
        )
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

    for key in sorted(groups.keys(), key=lambda k: (k[0], k[1], class_sort_key(k[2]), k[3], class_sort_key(k[4]))):
        species, sex_type, hunt_type, weapon, hunt_class = key
        group = sorted(groups[key], key=lambda r: (r["hunt_code"], r["hunt_name"]))
        stem = output_stem(species, sex_type, hunt_type, weapon, hunt_class)
        xlsx = STAGE_XLSX_DIR / f"{stem}.xlsx"
        write_xlsx(xlsx, group)
        audit_rows.append(
            {
                "file": xlsx.name,
                "rows": len(group),
                "species": species,
                "sex_type": sex_type,
                "hunt_type": hunt_type,
                "weapon": weapon,
                "hunt_class_split": hunt_class,
                "res_permit_rows": sum(1 for row in group if norm(row.get("permits_2026_res"))),
                "nr_permit_rows": sum(1 for row in group if norm(row.get("permits_2026_nr"))),
                "total_permit_rows": sum(1 for row in group if norm(row.get("permits_2026_total"))),
                "season_rows": sum(1 for row in group if norm(row.get("season"))),
                "average_harvest_age_rows": sum(1 for row in group if norm(row.get("Average Age Harvested (previous hunting season)"))),
                "notes_rows": sum(1 for row in group if norm(row.get("NOTES"))),
                "database_code_join_rows": sum(1 for row in group if row.get("_database_join") == "code"),
                "database_name_join_rows": sum(1 for row in group if row.get("_database_join") == "name"),
                "database_missing_join_rows": sum(1 for row in group if row.get("_database_join") == "missing"),
                "status": "OK",
            }
        )
        print(
            f"OK {xlsx.name} rows={len(group)} "
            f"res={audit_rows[-1]['res_permit_rows']} nr={audit_rows[-1]['nr_permit_rows']} "
            f"total={audit_rows[-1]['total_permit_rows']} season={audit_rows[-1]['season_rows']} "
            f"avg_age={audit_rows[-1]['average_harvest_age_rows']} "
            f"notes={audit_rows[-1]['notes_rows']}"
        )

    write_audit(audit_rows)
    if args.publish:
        publish_staged()
        print(f"PUBLISHED {LIVE_XLSX_DIR}")
    else:
        print(f"STAGED {STAGE_XLSX_DIR}")
    print(f"AUDIT {AUDIT_CSV}")


if __name__ == "__main__":
    main()
