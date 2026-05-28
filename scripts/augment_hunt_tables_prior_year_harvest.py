import csv
import json
from pathlib import Path
from copy import copy

from openpyxl import load_workbook


REPO = Path(__file__).resolve().parents[1]
HARVEST_FEATURES = REPO / "processed_data" / "harvest_quality_features_all_years_by_hunt_code.csv"
TARGET_MODEL_YEAR = 2026

TARGET_DIRS = [
    REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "formatted_tables",
    REPO / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026",
]

HUNT_CODE_HEADERS = {
    "hunt code",
    "hunt_code",
    "huntcode",
    "hunt no",
    "hunt_no",
    "permit number",
    "permit_number",
}

COL_PRIOR_YEAR = "Harvest Prior Year"
COL_SUCCESS = "Harvest Success (Prior Year %)"
COL_AVG_AGE = "Average Harvest Age (Prior Year)"
COL_AVG_DAYS = "Average Days Hunted (Prior Year)"
OUTPUT_HEADERS = [COL_PRIOR_YEAR, COL_SUCCESS, COL_AVG_AGE, COL_AVG_DAYS]


def normalize_code(value: str) -> str:
    return "".join(ch for ch in str(value or "").upper().strip() if ch.isalnum())


def norm_header(value: str) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def to_int(value):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return None


def to_float(value):
    try:
        return float(str(value).strip())
    except Exception:
        return None


def format_number(value):
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def choose_best(existing, candidate):
    if not existing:
        return candidate

    ex_rank = existing["rank"]
    ca_rank = candidate["rank"]
    if ca_rank > ex_rank:
        return candidate
    if ca_rank < ex_rank:
        return existing

    ex_year = existing.get("reported_year") or 0
    ca_year = candidate.get("reported_year") or 0
    if ca_year > ex_year:
        return candidate

    return existing


def load_harvest_lookup():
    lookup = {}
    if not HARVEST_FEATURES.exists():
        return lookup

    with HARVEST_FEATURES.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = normalize_code(row.get("hunt_code"))
            if not code:
                continue

            reported_year = to_int(row.get("reported_hunt_year"))
            model_target_year = to_int(row.get("model_target_year"))

            if model_target_year == TARGET_MODEL_YEAR:
                rank = 3
            elif reported_year == TARGET_MODEL_YEAR - 1:
                rank = 2
            elif reported_year:
                rank = 1
            else:
                rank = 0

            candidate = {
                "rank": rank,
                "reported_year": reported_year,
                "success_pct": to_float(row.get("percent_success")),
                "avg_age": to_float(row.get("average_age")),
                "avg_days": to_float(row.get("average_days")),
            }
            lookup[code] = choose_best(lookup.get(code), candidate)

    return lookup


def find_hunt_code_col(header_cells):
    for idx, value in enumerate(header_cells, start=1):
        if norm_header(value) in HUNT_CODE_HEADERS:
            return idx
    return None


def find_header_row(ws, max_scan_rows=20):
    for row_idx in range(1, min(ws.max_row, max_scan_rows) + 1):
        row_vals = [ws.cell(row=row_idx, column=i).value for i in range(1, ws.max_column + 1)]
        if find_hunt_code_col(row_vals):
            return row_idx
    return None


def ensure_output_cols(ws, header_row):
    header_values = [ws.cell(row=header_row, column=i).value for i in range(1, ws.max_column + 1)]
    mapping = {}
    for header in OUTPUT_HEADERS:
        found = None
        for idx, value in enumerate(header_values, start=1):
            if str(value or "").strip().lower() == header.lower():
                found = idx
                break
        if found is None:
            found = ws.max_column + 1
            ws.cell(row=header_row, column=found).value = header
            if found > 1:
                src = ws.cell(row=header_row, column=found - 1)
                dst = ws.cell(row=header_row, column=found)
                if src.has_style:
                    dst._style = copy(src._style)
                dst.font = copy(src.font)
                dst.fill = copy(src.fill)
                dst.border = copy(src.border)
                dst.alignment = copy(src.alignment)
                dst.number_format = src.number_format
                dst.protection = copy(src.protection)
        mapping[header] = found
    return mapping


def update_sheet(ws, harvest_lookup):
    header_row = find_header_row(ws)
    if not header_row:
        return 0

    header_values = [ws.cell(row=header_row, column=i).value for i in range(1, ws.max_column + 1)]
    hunt_code_col = find_hunt_code_col(header_values)
    if not hunt_code_col:
        return 0

    out_cols = ensure_output_cols(ws, header_row)
    updated = 0
    for row_idx in range(header_row + 1, ws.max_row + 1):
        code = normalize_code(ws.cell(row=row_idx, column=hunt_code_col).value)
        if not code:
            continue

        payload = harvest_lookup.get(code)
        if not payload:
            continue

        ws.cell(row=row_idx, column=out_cols[COL_PRIOR_YEAR]).value = payload.get("reported_year") or ""
        ws.cell(row=row_idx, column=out_cols[COL_SUCCESS]).value = format_number(payload.get("success_pct"))
        ws.cell(row=row_idx, column=out_cols[COL_AVG_AGE]).value = format_number(payload.get("avg_age"))
        ws.cell(row=row_idx, column=out_cols[COL_AVG_DAYS]).value = format_number(payload.get("avg_days"))
        updated += 1

    return updated


def process_workbook(file_path: Path, harvest_lookup):
    wb = load_workbook(file_path)
    updated_rows = 0
    touched_sheets = 0
    for ws in wb.worksheets:
        sheet_updates = update_sheet(ws, harvest_lookup)
        if sheet_updates:
            touched_sheets += 1
            updated_rows += sheet_updates

    if touched_sheets:
        wb.save(file_path)

    return {"file": str(file_path.relative_to(REPO)).replace("\\", "/"), "updated_rows": updated_rows, "touched_sheets": touched_sheets}


def main():
    harvest_lookup = load_harvest_lookup()
    reports = []

    for root in TARGET_DIRS:
        if not root.exists():
            continue
        for workbook in sorted(root.glob("*.xlsx")):
            reports.append(process_workbook(workbook, harvest_lookup))

    touched = [r for r in reports if r["updated_rows"] > 0]
    print(json.dumps({
        "ok": True,
        "harvest_lookup_codes": len(harvest_lookup),
        "workbooks_scanned": len(reports),
        "workbooks_updated": len(touched),
        "updates": touched,
    }, indent=2))


if __name__ == "__main__":
    main()
