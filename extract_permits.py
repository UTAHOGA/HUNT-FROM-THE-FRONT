#!/usr/bin/env python3
"""Extract Utah DWR permit numbers from draw-result PDFs.

The extractor is intentionally conservative: it only accepts lines that begin
with "Hunt:" so table values, dates, ratios, and page numbers are ignored.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - exercised by runtime only
    raise SystemExit(
        "Missing dependency: pypdf. Install it or run with the bundled Codex Python runtime."
    ) from exc


HUNT_LINE_RE = re.compile(
    r"^\s*Hunt:\s*(?P<permit_number>[A-Z]{1,6}\d{3,5})\s+(?P<body>.+?)\s*$"
)

TRAILING_PAGE_RE = re.compile(r"\s+Page\s+\d+\s*$", re.IGNORECASE)

TABLE_HEADER_RE = re.compile(
    r"^(Resident Applicants|Non-Resident Applicants|Total|Preference|Bonus|Regular|Points|"
    r"Utah Division|Species:|Page\s+\d+|\d+\s+)",
    re.IGNORECASE,
)

PERMIT_PREFIX_CATEGORY = {
    "DA": "Antlerless Deer",
    "DB": "Buck Deer",
    "EA": "Antlerless Elk",
    "EB": "Bull Elk",
    "PB": "Pronghorn",
    "BI": "Bison",
    "DS": "Desert Bighorn Sheep",
    "RS": "Rocky Mountain Bighorn Sheep",
    "RE": "Rocky Mountain Bighorn Sheep Ewe",
    "MB": "Moose",
    "GO": "Mountain Goat",
    "BR": "Black Bear",
    "TK": "Turkey",
}


@dataclass(frozen=True)
class PermitRow:
    source_file: str
    page_number: int
    hunt_code: str
    permit_number: str
    species_or_category: str
    hunt_name: str
    method_or_weapon: str
    permits_res_bonus: int | None
    permits_res_regular: int | None
    permits_res_total: int | None
    permits_nonres_bonus: int | None
    permits_nonres_regular: int | None
    permits_nonres_total: int | None
    permits_total: int | None
    raw_hunt_line: str
    raw_totals_line: str


def normalize_text_lines(text: str) -> List[str]:
    """Return page lines with simple fallback repair for split Hunt lines."""
    raw_lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    lines: List[str] = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if line.startswith("Hunt:"):
            parts = [line]
            j = i + 1
            # Some PDF extractors split a long hunt title/method over multiple
            # physical lines. Keep joining until the draw table/header starts.
            while j < len(raw_lines):
                nxt = raw_lines[j]
                if nxt.startswith("Hunt:") or TABLE_HEADER_RE.match(nxt):
                    break
                parts.append(nxt)
                j += 1
            lines.append(" ".join(parts))
            i = j
            continue
        lines.append(line)
        i += 1
    return lines


def parse_hunt_line(raw_line: str) -> Tuple[str, str, str, str] | None:
    """Parse one normalized Hunt line.

    Returns permit number, species/category, hunt name, and method/weapon.
    """
    match = HUNT_LINE_RE.match(raw_line)
    if not match:
        return None

    permit_number = match.group("permit_number")
    body = re.sub(r"\s+", " ", match.group("body")).strip()
    body = TRAILING_PAGE_RE.sub("", body).strip()
    chunks = [part.strip() for part in re.split(r"\s+-\s*|\s*-\s+", body) if part.strip()]

    species_or_category = chunks[0] if chunks else ""
    hunt_name = chunks[1] if len(chunks) >= 2 else ""
    method_or_weapon = " - ".join(chunks[2:]) if len(chunks) >= 3 else ""

    # General-season deer PDFs often omit the species/category and start with
    # the unit name: "Hunt: DB1501 Box Elder - Archery Page 2".
    # In that layout, keep the raw line intact but infer the category from the
    # permit prefix so the verification table still has a useful category.
    if len(chunks) == 2:
        first, second = chunks
        prefix = re.match(r"^[A-Z]+", permit_number)
        inferred = PERMIT_PREFIX_CATEGORY.get(prefix.group(0) if prefix else "")
        if inferred and not re.search(
            r"\b(deer|elk|pronghorn|bison|sheep|moose|goat|bear|turkey)\b",
            first,
            re.IGNORECASE,
        ):
            species_or_category = inferred
            hunt_name = first
            method_or_weapon = second

    return permit_number, species_or_category, hunt_name, method_or_weapon


def parse_totals_side(side_text: str) -> dict:
    """Parse one resident/nonresident side of a DWR Totals row.

    Expected side shape after the word "Totals":
    eligible_applicants bonus_permits regular_permits total_permits success_ratio...
    """
    values = re.findall(r"\b\d[\d,]*\b", side_text or "")
    if len(values) < 4:
        return {
            "eligible_applicants": None,
            "bonus_permits": None,
            "regular_permits": None,
            "total_permits": None,
        }
    parsed = [int(value.replace(",", "")) for value in values[:4]]
    return {
        "eligible_applicants": parsed[0],
        "bonus_permits": parsed[1],
        "regular_permits": parsed[2],
        "total_permits": parsed[3],
    }


def parse_totals_line(raw_line: str) -> dict | None:
    """Parse a full two-sided resident/nonresident Totals row."""
    line = re.sub(r"\s+", " ", raw_line or "").strip()
    match = re.match(r"^Totals\s+(?P<resident>.+?)\s+Totals\s+(?P<nonresident>.+)$", line)
    if not match:
        return None
    resident = parse_totals_side(match.group("resident"))
    nonresident = parse_totals_side(match.group("nonresident"))
    res_total = resident["total_permits"]
    nonres_total = nonresident["total_permits"]
    permits_total = None
    if res_total is not None or nonres_total is not None:
        permits_total = (res_total or 0) + (nonres_total or 0)
    return {
        "permits_res_bonus": resident["bonus_permits"],
        "permits_res_regular": resident["regular_permits"],
        "permits_res_total": res_total,
        "permits_nonres_bonus": nonresident["bonus_permits"],
        "permits_nonres_regular": nonresident["regular_permits"],
        "permits_nonres_total": nonres_total,
        "permits_total": permits_total,
        "raw_totals_line": line,
    }


EMPTY_TOTALS = {
    "permits_res_bonus": None,
    "permits_res_regular": None,
    "permits_res_total": None,
    "permits_nonres_bonus": None,
    "permits_nonres_regular": None,
    "permits_nonres_total": None,
    "permits_total": None,
    "raw_totals_line": "",
}


def extract_permits(pdf_path: Path) -> Tuple[List[PermitRow], dict]:
    reader = PdfReader(str(pdf_path))
    rows: List[PermitRow] = []
    seen = set()
    duplicate_count = 0
    pages_with_no_text: List[int] = []
    pages_with_hunt_line_missing_totals: List[int] = []
    hunt_lines_found = 0

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            pages_with_no_text.append(page_number)
            continue

        normalized_lines = normalize_text_lines(text)
        totals = None
        for line in normalized_lines:
            if line.startswith("Totals "):
                totals = parse_totals_line(line)
                if totals:
                    break

        for line in normalized_lines:
            if not line.startswith("Hunt:"):
                continue
            parsed = parse_hunt_line(line)
            if not parsed:
                continue
            hunt_lines_found += 1
            hunt_code, species_or_category, hunt_name, method_or_weapon = parsed
            key = (page_number, hunt_code, line)
            if key in seen:
                duplicate_count += 1
                continue
            seen.add(key)
            row_totals = totals or EMPTY_TOTALS
            if totals is None:
                pages_with_hunt_line_missing_totals.append(page_number)
            rows.append(
                PermitRow(
                    source_file=pdf_path.name,
                    page_number=page_number,
                    hunt_code=hunt_code,
                    permit_number="" if row_totals["permits_total"] is None else str(row_totals["permits_total"]),
                    species_or_category=species_or_category,
                    hunt_name=hunt_name,
                    method_or_weapon=method_or_weapon,
                    permits_res_bonus=row_totals["permits_res_bonus"],
                    permits_res_regular=row_totals["permits_res_regular"],
                    permits_res_total=row_totals["permits_res_total"],
                    permits_nonres_bonus=row_totals["permits_nonres_bonus"],
                    permits_nonres_regular=row_totals["permits_nonres_regular"],
                    permits_nonres_total=row_totals["permits_nonres_total"],
                    permits_total=row_totals["permits_total"],
                    raw_hunt_line=line,
                    raw_totals_line=row_totals["raw_totals_line"],
                )
            )

    report = {
        "source_file": str(pdf_path),
        "total_pages_scanned": len(reader.pages),
        "total_hunt_lines_found": hunt_lines_found,
        "total_permit_numbers_found": len(rows),
        "pages_with_no_extractable_text": pages_with_no_text,
        "pages_with_hunt_line_missing_totals": pages_with_hunt_line_missing_totals,
        "duplicate_count": duplicate_count,
    }
    return rows, report


def extract_many(pdf_paths: Sequence[Path]) -> Tuple[List[PermitRow], dict]:
    combined_rows: List[PermitRow] = []
    file_reports = []
    for pdf_path in pdf_paths:
        rows, report = extract_permits(pdf_path)
        combined_rows.extend(rows)
        file_reports.append(report)
    combined_report = {
        "source_files": [str(path) for path in pdf_paths],
        "file_reports": file_reports,
        "total_pages_scanned": sum(item["total_pages_scanned"] for item in file_reports),
        "total_hunt_lines_found": sum(item["total_hunt_lines_found"] for item in file_reports),
        "total_permit_numbers_found": len(combined_rows),
        "pages_with_no_extractable_text": {
            Path(item["source_file"]).name: item["pages_with_no_extractable_text"]
            for item in file_reports
            if item["pages_with_no_extractable_text"]
        },
        "pages_with_hunt_line_missing_totals": {
            Path(item["source_file"]).name: item["pages_with_hunt_line_missing_totals"]
            for item in file_reports
            if item["pages_with_hunt_line_missing_totals"]
        },
        "duplicate_count": sum(item["duplicate_count"] for item in file_reports),
    }
    return combined_rows, combined_report


def write_csv(rows: Sequence[PermitRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_file",
        "page_number",
        "hunt_code",
        "permit_number",
        "species_or_category",
        "hunt_name",
        "method_or_weapon",
        "permits_res_bonus",
        "permits_res_regular",
        "permits_res_total",
        "permits_nonres_bonus",
        "permits_nonres_regular",
        "permits_nonres_total",
        "permits_total",
        "raw_hunt_line",
        "raw_totals_line",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_json(rows: Sequence[PermitRow], report: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "report": report,
        "rows": [asdict(row) for row in rows],
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def format_report(rows: Sequence[PermitRow], report: dict) -> str:
    preview = rows[:10]
    source_label = report.get("source_file") or ", ".join(report.get("source_files", []))
    lines = [
        "Utah DWR Permit Number Extraction Report",
        "========================================",
        f"Source file: {source_label}",
        f"Total pages scanned: {report['total_pages_scanned']}",
        f"Total hunt lines found: {report['total_hunt_lines_found']}",
        f"Total permit numbers found: {report['total_permit_numbers_found']}",
        f"Pages with no extractable text: {report['pages_with_no_extractable_text'] or 'None'}",
        f"Pages with hunt line but no totals row: {report.get('pages_with_hunt_line_missing_totals') or 'None'}",
        f"Duplicate count: {report['duplicate_count']}",
        "",
        "First 10 extracted rows:",
    ]
    for row in preview:
        lines.append(
            f"- p.{row.page_number} {row.hunt_code}: permits {row.permits_total} "
            f"(Res {row.permits_res_total}, NonRes {row.permits_nonres_total}) | "
            f"{row.species_or_category} | {row.hunt_name} | {row.method_or_weapon}"
        )
    return "\n".join(lines) + "\n"


def write_report(rows: Sequence[PermitRow], report: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(format_report(rows, report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract Utah DWR permit numbers from draw-result PDFs."
    )
    parser.add_argument(
        "pdf",
        type=Path,
        nargs="+",
        help="Path to one or more Utah DWR draw-result PDFs",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs"),
        help="Output directory for permit_numbers.csv/json and extraction_report.txt",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    pdf_paths = args.pdf
    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            parser.error(f"PDF not found: {pdf_path}")

    rows, report = extract_many(pdf_paths)
    if not rows:
        raise SystemExit(f"No permit numbers found in: {', '.join(map(str, pdf_paths))}")

    out_dir = args.out
    write_csv(rows, out_dir / "permit_numbers.csv")
    write_json(rows, report, out_dir / "permit_numbers.json")
    write_report(rows, report, out_dir / "extraction_report.txt")

    print(format_report(rows, report))
    print(f"Wrote: {out_dir / 'permit_numbers.csv'}")
    print(f"Wrote: {out_dir / 'permit_numbers.json'}")
    print(f"Wrote: {out_dir / 'extraction_report.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
