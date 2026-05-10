#!/usr/bin/env python3
"""
Careful Utah harvest PDF parser (line-preserving).

- Parses hunt rows from text-based PDF pages
- Preserves raw line and page number for audit
- Supports mixed numeric-tail formats (5 or 7 trailing numeric values)
- Emits CSV, JSON, and TXT report outputs
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber

HUNT_CODE_RE = re.compile(r"\b[A-Z]{2}\d{4}\b")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass
class ParsedRow:
    source_file: str
    page_number: int
    hunt_code: str
    row_format: str
    table_context: str
    permits_res: Optional[float]
    permits_nr: Optional[float]
    permits_total: Optional[float]
    hunters: Optional[float]
    harvest: Optional[float]
    avg_days: Optional[float]
    success_percent: Optional[float]
    metric_4: Optional[float]
    metric_5: Optional[float]
    raw_line: str


def to_num(text: str) -> float:
    if text is None:
        return None
    if "." in text:
        return float(text)
    return int(text)


def classify_page_context(page_text: str) -> str:
    t = (page_text or "").lower()
    if "mean days" in t and "success" in t:
        return "days_success"
    if "avg satisfaction" in t and "success" in t:
        return "satisfaction_success"
    if "unit permits" in t:
        return "unit_permits"
    return "unknown"


def parse_line(line: str, page_context: str) -> Optional[Dict]:
    code_match = HUNT_CODE_RE.search(line)
    if not code_match:
        return None

    hunt_code = code_match.group(0)
    numbers = [m.group(0) for m in NUMBER_RE.finditer(line[code_match.end() :])]
    if len(numbers) < 5:
        return None

    # Use trailing values only to avoid numbers embedded in names/units.
    tail7 = numbers[-7:] if len(numbers) >= 7 else None
    tail5 = numbers[-5:]

    parsed = {
        "hunt_code": hunt_code,
        "permits_res": None,
        "permits_nr": None,
        "permits_total": None,
        "hunters": None,
        "harvest": None,
        "avg_days": None,
        "success_percent": None,
        "metric_4": None,
        "metric_5": None,
        "row_format": "unknown",
    }

    # Prefer 7-tail when reasonable (split permit rows).
    if tail7:
        r, nr, total, hunters, harvest, m4, m5 = [to_num(x) for x in tail7]
        # sanity: total should usually be >= r and >= nr
        if (isinstance(total, (int, float)) and isinstance(r, (int, float)) and isinstance(nr, (int, float))
                and total >= r and total >= nr):
            parsed.update(
                {
                    "permits_res": r,
                    "permits_nr": nr,
                    "permits_total": total,
                    "hunters": hunters,
                    "harvest": harvest,
                    "metric_4": m4,
                    "metric_5": m5,
                    "row_format": "split_7",
                }
            )
            if page_context == "days_success":
                parsed["avg_days"] = m4
                parsed["success_percent"] = m5
            return parsed

    # Fallback 5-tail (single permit total rows).
    total, hunters, harvest, m4, m5 = [to_num(x) for x in tail5]
    parsed.update(
        {
            "permits_total": total,
            "hunters": hunters,
            "harvest": harvest,
            "metric_4": m4,
            "metric_5": m5,
            "row_format": "total_5",
        }
    )
    if page_context == "days_success":
        parsed["avg_days"] = m4
        parsed["success_percent"] = m5
    return parsed


def parse_pdf(pdf_path: Path) -> Dict:
    rows: List[ParsedRow] = []
    pages_with_no_text: List[int] = []
    hunt_line_count = 0
    duplicate_count = 0

    seen = set()  # dedupe exact same row on same page

    with pdfplumber.open(str(pdf_path)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                pages_with_no_text.append(idx)
                continue

            page_context = classify_page_context(text)
            for raw_line in text.splitlines():
                if not HUNT_CODE_RE.search(raw_line):
                    continue
                hunt_line_count += 1
                parsed = parse_line(raw_line, page_context)
                if not parsed:
                    continue

                key = (idx, parsed["hunt_code"], raw_line.strip())
                if key in seen:
                    duplicate_count += 1
                    continue
                seen.add(key)

                rows.append(
                    ParsedRow(
                        source_file=str(pdf_path),
                        page_number=idx,
                        hunt_code=parsed["hunt_code"],
                        row_format=parsed["row_format"],
                        table_context=page_context,
                        permits_res=parsed["permits_res"],
                        permits_nr=parsed["permits_nr"],
                        permits_total=parsed["permits_total"],
                        hunters=parsed["hunters"],
                        harvest=parsed["harvest"],
                        avg_days=parsed["avg_days"],
                        success_percent=parsed["success_percent"],
                        metric_4=parsed["metric_4"],
                        metric_5=parsed["metric_5"],
                        raw_line=raw_line.strip(),
                    )
                )

    if not rows:
        raise RuntimeError("No hunt rows were parsed from this PDF.")

    report = {
        "source_file": str(pdf_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pages_scanned": len(pdf.pages),
        "total_hunt_lines_found": hunt_line_count,
        "total_rows_parsed": len(rows),
        "pages_with_no_extractable_text": pages_with_no_text,
        "duplicate_count": duplicate_count,
        "row_format_counts": {
            "split_7": sum(1 for r in rows if r.row_format == "split_7"),
            "total_5": sum(1 for r in rows if r.row_format == "total_5"),
            "unknown": sum(1 for r in rows if r.row_format == "unknown"),
        },
    }

    return {"report": report, "rows": rows}


def write_outputs(parsed: Dict, out_dir: Path, stem: str) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{stem}_harvest_rows.csv"
    json_path = out_dir / f"{stem}_harvest_rows.json"
    txt_path = out_dir / f"{stem}_extraction_report.txt"

    rows = parsed["rows"]
    report = parsed["report"]

    fieldnames = list(asdict(rows[0]).keys())
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "report": report,
                "rows": [asdict(r) for r in rows],
                "preview_first_10": [asdict(r) for r in rows[:10]],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    with txt_path.open("w", encoding="utf-8") as f:
        f.write("Utah Harvest PDF Extraction Report\n")
        f.write("=" * 40 + "\n")
        for k, v in report.items():
            f.write(f"{k}: {v}\n")
        f.write("\nFirst 10 rows:\n")
        for row in rows[:10]:
            f.write(f"- p{row.page_number} {row.hunt_code} | {row.row_format} | {row.raw_line}\n")

    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "txt": str(txt_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Utah harvest-report PDF hunt rows carefully.")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--out", default="processed_data", help="Output directory")
    parser.add_argument("--id", default=None, help="Output stem override")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    stem = args.id or pdf_path.stem.lower().replace(" ", "_")
    parsed = parse_pdf(pdf_path)
    outputs = write_outputs(parsed, Path(args.out), stem)

    print(json.dumps({"report": parsed["report"], "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
