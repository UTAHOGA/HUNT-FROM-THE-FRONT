from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Tuple

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

ROOT = Path(r"C:\Users\tyler\Desktop\GitHub\HUNT-BUILDER")
TARGET_DIR = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026" / "XLXS"
AUDIT_CSV = ROOT / "processed_data" / "audits" / "hunt_tables_2026_xlsx_reformat_audit.csv"


def find_header_row(ws) -> Optional[int]:
    probe_max = min(ws.max_row, 14)
    best_row = None
    best_score = -1
    for r in range(1, probe_max + 1):
        vals = [str(c.value).strip() if c.value is not None else "" for c in ws[r]]
        non = [v for v in vals if v]
        if not non:
            continue
        key = " | ".join(v.lower() for v in non)
        score = len(non)
        if "hunt_code" in key:
            score += 20
        if "hunt_name" in key:
            score += 12
        if "species" in key:
            score += 6
        if score > best_score:
            best_score = score
            best_row = r
    return best_row


def header_bounds(ws, header_row: int) -> Optional[Tuple[int, int]]:
    max_col = ws.max_column
    first_col = None
    last_col = None
    for c in range(1, max_col + 1):
        v = ws.cell(row=header_row, column=c).value
        if v is None or str(v).strip() == "":
            continue
        if first_col is None:
            first_col = c
        last_col = c
    if first_col is None or last_col is None:
        return None
    return first_col, last_col


def find_last_data_row(ws, header_row: int, first_col: int, last_col: int) -> int:
    last = header_row
    for r in range(header_row + 1, ws.max_row + 1):
        has_val = False
        for c in range(first_col, last_col + 1):
            v = ws.cell(row=r, column=c).value
            if v is not None and str(v).strip() != "":
                has_val = True
                break
        if has_val:
            last = r
    if last == header_row:
        last = header_row + 1
    return last


def reset_tables(ws) -> None:
    for name in list(ws.tables.keys()):
        del ws.tables[name]


def sanitize_header_row(ws, header_row: int, first_col: int, last_col: int) -> None:
    seen = set()
    for c in range(first_col, last_col + 1):
        raw = ws.cell(row=header_row, column=c).value
        text = "" if raw is None else str(raw).strip()
        if not text:
            text = f"column_{c}"
        base = text
        i = 2
        while text.lower() in seen:
            text = f"{base}_{i}"
            i += 1
        seen.add(text.lower())
        ws.cell(row=header_row, column=c).value = text


def apply_visual_polish(ws, header_row: int, first_col: int, last_col: int, last_row: int) -> None:
    header_fill = PatternFill(fill_type="solid", fgColor="4F2D1D")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)

    for c in range(first_col, last_col + 1):
        cell = ws.cell(row=header_row, column=c)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r in range(header_row + 1, last_row + 1):
        for c in range(first_col, last_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = data_font
            cell.alignment = Alignment(vertical="center", wrap_text=False)

    for c in range(first_col, last_col + 1):
        col_letter = get_column_letter(c)
        max_len = 0
        for r in range(header_row, min(last_row, header_row + 350) + 1):
            v = ws.cell(row=r, column=c).value
            if v is None:
                continue
            max_len = max(max_len, len(str(v)))
        if max_len <= 10:
            width = 14
        elif max_len <= 20:
            width = 20
        elif max_len <= 35:
            width = 28
        else:
            width = 36
        ws.column_dimensions[col_letter].width = width

    ws.freeze_panes = ws.cell(row=header_row + 1, column=first_col)
    ws.auto_filter.ref = f"{get_column_letter(first_col)}{header_row}:{get_column_letter(last_col)}{last_row}"


def process_file(path: Path, idx: int) -> dict:
    out = {
        "file": path.name,
        "sheet": "",
        "header_row": "",
        "first_col": "",
        "last_col": "",
        "last_row": "",
        "table_ref": "",
        "columns": "",
        "data_rows": "",
        "status": "",
        "error": "",
    }
    wb = None
    try:
        wb = load_workbook(path)
        ws = wb[wb.sheetnames[0]]
        out["sheet"] = ws.title

        hr = find_header_row(ws)
        if hr is None:
            out["status"] = "SKIP"
            out["error"] = "header_not_found"
            return out

        bounds = header_bounds(ws, hr)
        if bounds is None:
            out["status"] = "SKIP"
            out["error"] = "header_bounds_not_found"
            return out

        fc, lc = bounds
        lr = find_last_data_row(ws, hr, fc, lc)

        reset_tables(ws)
        sanitize_header_row(ws, hr, fc, lc)

        ref = f"{get_column_letter(fc)}{hr}:{get_column_letter(lc)}{lr}"
        tname = f"HUNT_TABLE_{idx:03d}"
        table = Table(displayName=tname, ref=ref)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws.add_table(table)

        apply_visual_polish(ws, hr, fc, lc, lr)

        wb.save(path)

        out.update(
            {
                "header_row": hr,
                "first_col": fc,
                "last_col": lc,
                "last_row": lr,
                "table_ref": ref,
                "columns": lc - fc + 1,
                "data_rows": max(0, lr - hr),
                "status": "OK",
            }
        )
        return out
    except Exception as exc:
        out["status"] = "ERROR"
        out["error"] = str(exc)
        return out
    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass


def main() -> None:
    if not TARGET_DIR.exists():
        raise SystemExit(f"Missing target folder: {TARGET_DIR}")

    files = sorted(TARGET_DIR.glob("*.xlsx"))
    if not files:
        raise SystemExit("No .xlsx files found")

    results = []
    for i, f in enumerate(files, start=1):
        res = process_file(f, i)
        results.append(res)
        print(f"{res['file']}: {res['status']} {res['table_ref']} {res['error']}")

    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "file",
                "sheet",
                "header_row",
                "first_col",
                "last_col",
                "last_row",
                "table_ref",
                "columns",
                "data_rows",
                "status",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    ok = sum(1 for r in results if r["status"] == "OK")
    err = sum(1 for r in results if r["status"] == "ERROR")
    skip = sum(1 for r in results if r["status"] == "SKIP")
    print(f"DONE total={len(results)} ok={ok} skip={skip} error={err} audit={AUDIT_CSV}")


if __name__ == "__main__":
    main()
