from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import pandas as pd
import pdfplumber


def sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")


def clean_table(raw_rows: list[list[str | None]]) -> list[list[str]]:
    cleaned: list[list[str]] = []
    max_cols = 0
    for row in raw_rows:
        cells = [(cell or "").replace("\n", " ").strip() for cell in row]
        if any(cell for cell in cells):
            cleaned.append(cells)
            max_cols = max(max_cols, len(cells))
    if max_cols == 0:
        return []
    normalized = [row + [""] * (max_cols - len(row)) for row in cleaned]
    return normalized


def table_to_dataframe(table_rows: list[list[str]]) -> pd.DataFrame:
    if not table_rows:
        return pd.DataFrame()
    header = table_rows[0]
    body = table_rows[1:] if len(table_rows) > 1 else []
    use_header = any(cell for cell in header)
    if use_header:
        cols = []
        seen = {}
        for i, cell in enumerate(header):
            base = cell if cell else f"col_{i+1}"
            count = seen.get(base, 0) + 1
            seen[base] = count
            cols.append(base if count == 1 else f"{base}_{count}")
        return pd.DataFrame(body, columns=cols)
    width = len(header)
    cols = [f"col_{i+1}" for i in range(width)]
    return pd.DataFrame(table_rows, columns=cols)


def page_title_hint(page_text: str) -> str:
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return ""
    for ln in lines[:6]:
        if len(ln) > 8:
            return ln[:160]
    return lines[0][:160]


def extract(pdf_path: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = out_dir / "tables"
    text_dir = out_dir / "page_text"
    tables_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict] = []
    summary = {
        "source_pdf": str(pdf_path),
        "pages": 0,
        "tables_detected": 0,
        "tables_written": 0,
        "pages_without_tables": 0,
    }

    forced_multi_pages = set([7, 20, 22] + list(range(25, 45)))

    table_settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "intersection_tolerance": 5,
        "snap_tolerance": 3,
        "join_tolerance": 3,
    }

    with pdfplumber.open(str(pdf_path)) as pdf:
        summary["pages"] = len(pdf.pages)
        for page_index, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            title_hint = page_title_hint(page_text)
            (text_dir / f"page_{page_index:03d}.txt").write_text(page_text, encoding="utf-8")

            regions = []
            if page_index in forced_multi_pages:
                mid_x = page.width / 2
                regions = [
                    ("L", page.within_bbox((0, 0, mid_x, page.height))),
                    ("R", page.within_bbox((mid_x, 0, page.width, page.height))),
                ]
            else:
                regions = [("FULL", page)]

            found_any = False
            page_tables_written = 0

            for region_name, region_page in regions:
                found_tables = region_page.find_tables(table_settings=table_settings)
                if not found_tables:
                    continue

                found_any = True
                summary["tables_detected"] += len(found_tables)
                for table_index, table_obj in enumerate(found_tables, start=1):
                    raw_rows = table_obj.extract()
                    normalized = clean_table(raw_rows)
                    if not normalized:
                        manifest_rows.append(
                            {
                                "source_pdf": str(pdf_path),
                                "page": page_index,
                                "region": region_name,
                                "table_index": table_index,
                                "status": "empty_after_clean",
                                "rows": 0,
                                "cols": 0,
                                "title_hint": title_hint,
                                "csv_file": "",
                                "xlsx_file": "",
                                "notes": "",
                            }
                        )
                        continue

                    df = table_to_dataframe(normalized)
                    rows = int(df.shape[0])
                    cols = int(df.shape[1])
                    base_name = f"page_{page_index:03d}_{region_name}_table_{table_index:02d}"
                    csv_file = tables_dir / f"{base_name}.csv"
                    xlsx_file = tables_dir / f"{base_name}.xlsx"

                    df.to_csv(csv_file, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
                    df.to_excel(xlsx_file, index=False)
                    summary["tables_written"] += 1
                    page_tables_written += 1

                    manifest_rows.append(
                        {
                            "source_pdf": str(pdf_path),
                            "page": page_index,
                            "region": region_name,
                            "table_index": table_index,
                            "status": "written",
                            "rows": rows,
                            "cols": cols,
                            "title_hint": title_hint,
                            "csv_file": str(csv_file),
                            "xlsx_file": str(xlsx_file),
                            "notes": "forced_left_right_split" if page_index in forced_multi_pages else "",
                        }
                    )

            if not found_any:
                summary["pages_without_tables"] += 1
                manifest_rows.append(
                    {
                        "source_pdf": str(pdf_path),
                        "page": page_index,
                        "region": "FULL",
                        "table_index": "",
                        "status": "no_table_detected",
                        "rows": 0,
                        "cols": 0,
                        "title_hint": title_hint,
                        "csv_file": "",
                        "xlsx_file": "",
                        "notes": "",
                    }
                )

    manifest_csv = out_dir / "table_split_manifest.csv"
    manifest_json = out_dir / "table_split_manifest.json"
    manifest_xlsx = out_dir / "table_split_manifest.xlsx"
    report_txt = out_dir / "table_split_report.txt"

    manifest_df = pd.DataFrame(manifest_rows)
    manifest_df.to_csv(manifest_csv, index=False, encoding="utf-8")
    manifest_df.to_json(manifest_json, orient="records", indent=2, force_ascii=False)
    manifest_df.to_excel(manifest_xlsx, index=False)

    report_txt.write_text(
        "\n".join(
            [
                "Pages-from-24_bg_report table split report",
                "========================================",
                f"source_pdf: {summary['source_pdf']}",
                f"pages: {summary['pages']}",
                f"tables_detected: {summary['tables_detected']}",
                f"tables_written: {summary['tables_written']}",
                f"pages_without_tables: {summary['pages_without_tables']}",
                f"manifest_csv: {manifest_csv}",
                f"manifest_json: {manifest_json}",
                f"manifest_xlsx: {manifest_xlsx}",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "summary": summary,
        "manifest_csv": str(manifest_csv),
        "manifest_json": str(manifest_json),
        "manifest_xlsx": str(manifest_xlsx),
        "report_txt": str(report_txt),
        "tables_dir": str(tables_dir),
        "text_dir": str(text_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split each detected table from Pages from 24_bg_report-2.pdf into review spreadsheets."
    )
    parser.add_argument("pdf_path", help="Path to the source PDF.")
    parser.add_argument(
        "--out-dir",
        default="pipeline/RAW/hunt_unit_database/2025/formatted_tables/pages_from_24_bg_report_2_table_splits",
        help="Output directory.",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).resolve()
    out_dir = Path(args.out_dir).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    result = extract(pdf_path, out_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
