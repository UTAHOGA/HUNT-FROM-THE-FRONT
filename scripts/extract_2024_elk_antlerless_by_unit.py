from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import pdfplumber


YEAR_COLUMNS = [str(y) for y in range(2015, 2025)]
ROW_RE = re.compile(
    r"^(\S+)\s+(.+?)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$"
)


@dataclass
class HarvestRow:
    unit: str
    unit_name: str
    y2015: int
    y2016: int
    y2017: int
    y2018: int
    y2019: int
    y2020: int
    y2021: int
    y2022: int
    y2023: int
    y2024: int


def parse_rows(pdf_path: Path) -> tuple[list[HarvestRow], dict]:
    rows: list[HarvestRow] = []
    skipped_lines: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text_lines = (page.extract_text() or "").splitlines()
            for line_idx, raw_line in enumerate(text_lines, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("Total antlerless* elk harvest by management unit"):
                    continue
                if line.startswith("Unit Unit name 2015 2016 2017"):
                    continue
                if line.startswith("*Data includes mitigation harvest."):
                    continue
                if line.isdigit():
                    continue

                m = ROW_RE.match(line)
                if not m:
                    skipped_lines.append(
                        {
                            "page": page_idx,
                            "line": line_idx,
                            "raw_line": line,
                            "reason": "regex_no_match",
                        }
                    )
                    continue

                vals = m.groups()
                row = HarvestRow(
                    unit=vals[0],
                    unit_name=vals[1],
                    y2015=int(vals[2]),
                    y2016=int(vals[3]),
                    y2017=int(vals[4]),
                    y2018=int(vals[5]),
                    y2019=int(vals[6]),
                    y2020=int(vals[7]),
                    y2021=int(vals[8]),
                    y2022=int(vals[9]),
                    y2023=int(vals[10]),
                    y2024=int(vals[11]),
                )
                rows.append(row)

        report = {
            "source_pdf": str(pdf_path).replace("\\", "/"),
            "pages_scanned": len(pdf.pages),
            "rows_extracted": len(rows),
            "skipped_line_count": len(skipped_lines),
            "skipped_lines_preview": skipped_lines[:20],
            "footnote": "*Data includes mitigation harvest.",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    return rows, report


def write_outputs(rows: list[HarvestRow], report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    data = [asdict(r) for r in rows]
    ordered_cols = ["unit", "unit_name", "y2015", "y2016", "y2017", "y2018", "y2019", "y2020", "y2021", "y2022", "y2023", "y2024"]
    df = pd.DataFrame(data, columns=ordered_cols)
    rename_map = {
        "unit": "Unit",
        "unit_name": "Unit name",
        "y2015": "2015",
        "y2016": "2016",
        "y2017": "2017",
        "y2018": "2018",
        "y2019": "2019",
        "y2020": "2020",
        "y2021": "2021",
        "y2022": "2022",
        "y2023": "2023",
        "y2024": "2024",
    }
    df = df.rename(columns=rename_map)

    csv_path = out_dir / "ELK_ANTLERLESS_BY_UNIT_2015_2024.csv"
    xlsx_path = out_dir / "ELK_ANTLERLESS_BY_UNIT_2015_2024.xlsx"
    manifest_csv = out_dir / "elk_antlerless_by_unit_2015_2024_manifest.csv"
    manifest_json = out_dir / "elk_antlerless_by_unit_2015_2024_manifest.json"
    report_txt = out_dir / "elk_antlerless_by_unit_2015_2024_extract_report.txt"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    with manifest_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["output_file", "rows", "columns"])
        w.writerow([csv_path.name, len(df), len(df.columns)])
        w.writerow([xlsx_path.name, len(df), len(df.columns)])

    manifest_json.write_text(
        json.dumps(
            {
                "title": "Total antlerless elk harvest by management unit, Utah 2015-2024",
                "source_pdf": report["source_pdf"],
                "outputs": [
                    {"file": str(csv_path).replace("\\", "/"), "rows": len(df), "columns": list(df.columns)},
                    {"file": str(xlsx_path).replace("\\", "/"), "rows": len(df), "columns": list(df.columns)},
                ],
                "footnote": report["footnote"],
                "generated_at": report["generated_at"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report_txt.write_text(
        "\n".join(
            [
                "ELK antlerless by unit extract report",
                f"Source PDF: {report['source_pdf']}",
                f"Pages scanned: {report['pages_scanned']}",
                f"Rows extracted: {report['rows_extracted']}",
                f"Skipped lines: {report['skipped_line_count']}",
                f"Footnote: {report['footnote']}",
                "",
                "Columns:",
                ", ".join(df.columns.tolist()),
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    pdf_path = Path(
        r"pipeline/RAW/hunt_unit_database/2025/pdf/harvest_report/ELK/2024 ELK ANTLERLESS BY UNIT 2015-2024.pdf"
    )
    out_dir = Path(r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/elk_antlerless_by_unit_2015_2024_extract")

    rows, report = parse_rows(pdf_path)
    write_outputs(rows, report, out_dir)

    print(f"Extracted {len(rows)} rows")
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()
