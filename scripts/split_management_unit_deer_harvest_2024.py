from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pandas as pd
import pdfplumber


UNIT_RE = re.compile(r"^\d+[A-Z]*(?:/\d+[A-Z]*)?$")


def as_int_or_none(value: str):
    v = value.strip()
    if not v or "*" in v:
        return None
    return int(v)


def as_float_or_none(value: str):
    v = value.strip()
    if not v or "*" in v:
        return None
    return float(v)


def parse_year_section(
    lines: list[str], title_prefix: str, stop_title_prefixes: list[str] | None = None
) -> list[dict]:
    rows: list[dict] = []
    in_table = False
    years = [str(y) for y in range(2015, 2025)]

    stop_title_prefixes = stop_title_prefixes or []

    for raw in lines:
        line = " ".join(raw.split())
        if not line:
            continue
        if line.startswith(title_prefix):
            in_table = True
            continue
        if in_table and any(line.startswith(prefix) for prefix in stop_title_prefixes):
            break
        if not in_table:
            continue
        if line.startswith("Unit Unit name"):
            continue
        if line.startswith("*Data includes mitigation harvest."):
            continue
        if line.startswith("*Included with Wasatch Mtns, West"):
            continue
        if line.isdigit():
            continue

        tokens = line.split()
        if len(tokens) < 12:
            continue
        if not UNIT_RE.match(tokens[0]):
            continue

        unit = tokens[0]
        year_vals = tokens[-10:]
        name_tokens = tokens[1:-10]
        unit_name = " ".join(name_tokens).strip()
        if not unit_name:
            continue

        row = {"Unit": unit, "Unit name": unit_name}
        for y, val in zip(years, year_vals):
            row[y] = as_int_or_none(val)
        rows.append(row)

    return rows


def parse_total_2024(lines: list[str]) -> list[dict]:
    rows: list[dict] = []
    in_table = False

    for raw in lines:
        line = " ".join(raw.split())
        if not line:
            continue
        if line.startswith("Total deer harvest by management unit, Utah 2024."):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("Buck Antlerless Total Hunters Mean days Success"):
            continue
        if line.startswith("Unit Unit name"):
            continue
        if line.isdigit():
            continue

        tokens = line.split()
        if len(tokens) < 8:
            continue
        if not UNIT_RE.match(tokens[0]):
            continue

        unit = tokens[0]
        tail = tokens[-6:]
        name_tokens = tokens[1:-6]
        unit_name = " ".join(name_tokens).strip()
        if not unit_name:
            continue

        row = {
            "Unit": unit,
            "Unit name": unit_name,
            "Buck harvest": as_int_or_none(tail[0]),
            "Antlerless harvest": as_int_or_none(tail[1]),
            "Total harvest": as_int_or_none(tail[2]),
            "Hunters afield": as_int_or_none(tail[3]),
            "Mean days hunted": as_float_or_none(tail[4]),
            "Success rate (%)": as_float_or_none(tail[5]),
        }
        rows.append(row)

    return rows


def write_outputs(df: pd.DataFrame, base_name: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{base_name}.csv"
    xlsx_path = out_dir / f"{base_name}.xlsx"
    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
    df.to_excel(xlsx_path, index=False)
    return csv_path, xlsx_path


def main():
    parser = argparse.ArgumentParser(
        description="Split 24_management_unit_deer_harvest PDF into three section spreadsheets."
    )
    parser.add_argument("pdf_path", help="Path to 24_management_unit_deer_harvest.pdf")
    parser.add_argument(
        "--out-dir",
        default="pipeline/RAW/hunt_unit_database/2025/formatted_tables/management_unit_deer_harvest_sections",
        help="Output directory for split files",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing PDF: {pdf_path}")

    all_lines: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(text.splitlines())

    buck_rows = parse_year_section(
        all_lines,
        "Total buck deer harvest by management unit, Utah 2015",
        stop_title_prefixes=["Total antlerless* deer harvest by management unit, Utah 2015"],
    )
    antlerless_rows = parse_year_section(
        all_lines,
        "Total antlerless* deer harvest by management unit, Utah 2015",
        stop_title_prefixes=["Total deer harvest by management unit, Utah 2024"],
    )
    total_rows = parse_total_2024(all_lines)

    buck_df = pd.DataFrame(buck_rows)
    antlerless_df = pd.DataFrame(antlerless_rows)
    total_df = pd.DataFrame(total_rows)

    buck_paths = write_outputs(
        buck_df,
        "TOTAL_BUCK_DEER_HARVEST_BY_MANAGEMENT_UNIT_UTAH_2015_2024",
        out_dir,
    )
    antlerless_paths = write_outputs(
        antlerless_df,
        "TOTAL_ANTLERLESS_DEER_HARVEST_BY_MANAGEMENT_UNIT_UTAH_2015_2024",
        out_dir,
    )
    total_paths = write_outputs(
        total_df, "TOTAL_DEER_HARVEST_BY_MANAGEMENT_UNIT_UTAH_2024", out_dir
    )

    print("Created:")
    for p in [*buck_paths, *antlerless_paths, *total_paths]:
        print(f"- {p}")
    print(
        f"Row counts -> buck: {len(buck_df)}, antlerless: {len(antlerless_df)}, total_2024: {len(total_df)}"
    )


if __name__ == "__main__":
    main()
