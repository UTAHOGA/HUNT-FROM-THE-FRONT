from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pandas as pd
import pdfplumber


ROW_RE = re.compile(
    r"^(?P<year>\d{4})\s+"
    r"(?P<buck>\d+)\s+"
    r"(?P<antlerless>—|\d+)\s+"
    r"(?P<total>\d+)\s+"
    r"(?P<hunters>\d+\*?)$"
)


def parse_int_or_none(value: str) -> int | None:
    v = (value or "").strip()
    if not v or v == "—":
        return None
    return int(v)


def parse_hunters(value: str) -> tuple[int | None, str | None]:
    raw = (value or "").strip()
    if not raw:
        return None, None
    note = None
    if raw.endswith("*"):
        note = "footnote_star"
        raw = raw[:-1]
    return int(raw), note


def extract_rows(pdf_path: Path) -> list[dict]:
    rows: list[dict] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = " ".join(raw_line.split())
                m = ROW_RE.match(line)
                if not m:
                    continue

                hunters, hunters_note = parse_hunters(m.group("hunters"))
                row = {
                    "year": int(m.group("year")),
                    "buck_harvest": int(m.group("buck")),
                    "antlerless_harvest": parse_int_or_none(m.group("antlerless")),
                    "total_harvest": int(m.group("total")),
                    "hunters_afield": hunters,
                    "hunters_afield_note": hunters_note,
                    "source_page": page_num,
                    "source_line": line,
                }
                rows.append(row)

    # Deduplicate by year, keeping first appearance.
    deduped = {}
    for r in rows:
        deduped.setdefault(r["year"], r)
    return [deduped[y] for y in sorted(deduped.keys())]


def build_qc(rows: list[dict]) -> dict:
    years = [r["year"] for r in rows]
    min_year = min(years) if years else None
    max_year = max(years) if years else None
    expected = set(range(min_year, max_year + 1)) if years else set()
    found = set(years)
    missing = sorted(expected - found)

    return {
        "rows": len(rows),
        "min_year": min_year,
        "max_year": max_year,
        "missing_years_in_range": missing,
        "starred_hunters_rows": sum(1 for r in rows if r["hunters_afield_note"] == "footnote_star"),
        "blank_antlerless_rows": sum(1 for r in rows if r["antlerless_harvest"] is None),
    }


def write_outputs(rows: list[dict], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "STATEWIDE_MULE_DEER_HARVEST_HISTORY_UTAH_1925_2024.csv"
    xlsx_path = out_dir / "STATEWIDE_MULE_DEER_HARVEST_HISTORY_UTAH_1925_2024.xlsx"
    qc_path = out_dir / "STATEWIDE_MULE_DEER_HARVEST_HISTORY_UTAH_1925_2024_QC.txt"

    df = pd.DataFrame(rows)
    export_cols = [
        "year",
        "buck_harvest",
        "antlerless_harvest",
        "total_harvest",
        "hunters_afield",
        "hunters_afield_note",
        "source_page",
        "source_line",
    ]
    df = df[export_cols]
    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
    df.to_excel(xlsx_path, index=False)

    qc = build_qc(rows)
    with qc_path.open("w", encoding="utf-8") as f:
        f.write("Statewide mule deer harvest history extraction QC\n")
        f.write("=" * 52 + "\n")
        for k, v in qc.items():
            f.write(f"{k}: {v}\n")

    return {"csv": str(csv_path), "xlsx": str(xlsx_path), "qc": str(qc_path), "qc_data": qc}


def main():
    parser = argparse.ArgumentParser(
        description="Extract statewide mule deer harvest history (Utah 1925–2024) into columnized spreadsheet."
    )
    parser.add_argument("pdf_path", help="Path to 24_statewide mule deer harvest history.pdf")
    parser.add_argument(
        "--out-dir",
        default="pipeline/RAW/hunt_unit_database/2025/formatted_tables/statewide_mule_deer_harvest_history",
        help="Output directory",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing PDF: {pdf_path}")

    rows = extract_rows(pdf_path)
    if not rows:
        raise RuntimeError("No data rows were extracted from the PDF.")

    outputs = write_outputs(rows, out_dir)
    print("Created:")
    print(f"- {outputs['csv']}")
    print(f"- {outputs['xlsx']}")
    print(f"- {outputs['qc']}")
    print(f"Row count: {outputs['qc_data']['rows']}")
    print(
        f"Year coverage: {outputs['qc_data']['min_year']}–{outputs['qc_data']['max_year']} | Missing years: {outputs['qc_data']['missing_years_in_range']}"
    )


if __name__ == "__main__":
    main()

