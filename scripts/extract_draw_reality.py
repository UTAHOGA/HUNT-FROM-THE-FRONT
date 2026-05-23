#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pdfplumber


HUNT_RE = re.compile(r"Hunt:\s+(?P<hunt_code>[A-Z]{1,4}\d{4})\s+(?P<hunt_name>.+?)(?:\s+Page\s+\d+)?$", re.I)

ROW_RE = re.compile(
    r"^\s*"
    r"(?P<res_points>\d+)\s+"
    r"(?P<res_applicants>\d+)\s+"
    r"(?P<res_bonus>\d+)\s+"
    r"(?P<res_regular>\d+)\s+"
    r"(?P<res_total>\d+)\s+"
    r"(?P<res_ratio>N/A|1\s+in\s+[\d.]+)"
    r"\s+"
    r"(?P<nr_points>\d+)\s+"
    r"(?P<nr_applicants>\d+)\s+"
    r"(?P<nr_bonus>\d+)\s+"
    r"(?P<nr_regular>\d+)\s+"
    r"(?P<nr_total>\d+)\s+"
    r"(?P<nr_ratio>N/A|1\s+in\s+[\d.]+)"
    r"\s*$",
    re.I,
)


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip()


def parse_pdf(pdf_path: Path, year: int) -> list[dict]:
    rows = []
    current_hunt_code = None
    current_hunt_name = None

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = clean_line(raw_line)

                hunt_match = HUNT_RE.search(line)
                if hunt_match:
                    current_hunt_code = hunt_match.group("hunt_code").strip()
                    current_hunt_name = hunt_match.group("hunt_name").strip()
                    continue

                if not current_hunt_code:
                    continue

                if line.startswith("Totals "):
                    continue

                row_match = ROW_RE.match(line)
                if not row_match:
                    continue

                m = row_match.groupdict()

                rows.append({
                    "source_file": pdf_path.name,
                    "page_number": page_num,
                    "hunt_code": current_hunt_code,
                    "hunt_name": current_hunt_name,
                    "year": year,
                    "residency": "Resident",
                    "points": int(m["res_points"]),
                    "eligible_applicants": int(m["res_applicants"]),
                    "bonus_permits": int(m["res_bonus"]),
                    "regular_permits": int(m["res_regular"]),
                    "total_drawn": int(m["res_total"]),
                    "total_permits": int(m["res_total"]),
                    "success_ratio": m["res_ratio"],
                    "status": "" if m["res_applicants"] != "0" or m["res_total"] != "0" else "NO DATA",
                })

                rows.append({
                    "source_file": pdf_path.name,
                    "page_number": page_num,
                    "hunt_code": current_hunt_code,
                    "hunt_name": current_hunt_name,
                    "year": year,
                    "residency": "Nonresident",
                    "points": int(m["nr_points"]),
                    "eligible_applicants": int(m["nr_applicants"]),
                    "bonus_permits": int(m["nr_bonus"]),
                    "regular_permits": int(m["nr_regular"]),
                    "total_drawn": int(m["nr_total"]),
                    "total_permits": int(m["nr_total"]),
                    "success_ratio": m["nr_ratio"],
                    "status": "" if m["nr_applicants"] != "0" or m["nr_total"] != "0" else "NO DATA",
                })

    return rows


def write_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "hunt_code",
        "year",
        "residency",
        "points",
        "eligible_applicants",
        "total_drawn",
        "bonus_permits",
        "regular_permits",
        "total_permits",
        "status",
        "success_ratio",
        "hunt_name",
        "source_file",
        "page_number",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract Utah DWR draw-result PDFs into draw_reality_engine.csv format."
    )
    parser.add_argument("--input", required=True, help="PDF file or folder of PDFs")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--year", required=True, type=int, help="Draw year, example: 2025")
    parser.add_argument("--append", action="store_true", help="Append to existing output CSV")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    if input_path.is_file():
        pdfs = [input_path]
    else:
        pdfs = sorted(input_path.glob("*.pdf"))

    if not pdfs:
        raise SystemExit(f"No PDFs found in: {input_path}")

    all_rows = []

    for pdf in pdfs:
        print(f"Extracting: {pdf}")
        rows = parse_pdf(pdf, args.year)
        print(f"  rows: {len(rows)}")
        all_rows.extend(rows)

    if args.append and output_path.exists():
        import pandas as pd
        old = pd.read_csv(output_path, low_memory=False)
        new = pd.DataFrame(all_rows)
        combined = pd.concat([old, new], ignore_index=True)
        combined.to_csv(output_path, index=False)
    else:
        write_csv(all_rows, output_path)

    print()
    print(f"WROTE: {output_path}")
    print(f"PDFS: {len(pdfs)}")
    print(f"ROWS: {len(all_rows)}")

    if all_rows:
        hunt_count = len(set(r["hunt_code"] for r in all_rows))
        print(f"HUNTS: {hunt_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())