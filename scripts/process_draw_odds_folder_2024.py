from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from datetime import datetime

import pandas as pd
import pdfplumber


DRAW_DIR = Path(r"pipeline/RAW/hunt_unit_database/2025/pdf/draw_odds")
MASTER_FILE = "24_bg-odds.pdf"
# Explicitly exclude species-level "All Applicants" summary pages from master parsing.
# 24_bg-odds.pdf pages:
# - 188: LIMITED ENTRY ELK - All Applicants
# - 398: LIMITED ENTRY PRONGHORN - All Applicants
# - 537: BULL MOOSE - All Applicants
# - 573: ROCKY MTN SHEEP - All Applicants
EXCLUDED_MASTER_PAGES = {188, 398, 537, 573}
OUT_DIR = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/batch_2024_subfiles_vs_master"
)

HUNT_RE = re.compile(r"Hunt:\s*([A-Z]{2}\d{4})\s+(.+)")
TOTALS_LINE_RE = re.compile(r"^\s*Totals\b.*$", re.IGNORECASE)
NUM_RE = re.compile(r"[\d,]+")
RES_NR_TOTALS_RE = re.compile(
    r"Totals\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+"
    r"(?:1\s+in\s+[\d,.]+|N\s*/?\s*A|N/A)\s+"
    r"Totals\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)",
    re.IGNORECASE,
)


@dataclass
class HuntRow:
    source_file: str
    source_page: int
    hunt_code: str
    hunt_name: str
    totals_line: str
    totals_numbers: str
    res_total_permits: int | None
    nr_total_permits: int | None
    total_permits: int | None
    parse_style: str


def to_int_token(token: str) -> int:
    return int(token.replace(",", "").strip())


def parse_totals_line(line: str) -> dict[str, Any]:
    """
    Heuristic parser for Utah draw-odds totals lines.
    Handles common formats:
    - Totals <res_app> <res_bonus> <res_regular> <res_total> ... Totals <nr_app> <nr_bonus> <nr_regular> <nr_total> ...
    - Totals <applicants> <permits>
    """
    split_match = RES_NR_TOTALS_RE.search(" ".join(line.split()))
    if split_match:
        values = [to_int_token(split_match.group(i)) for i in range(1, 9)]
        res_total = values[3]
        nr_total = values[7]
        return {
            "totals_numbers": ";".join(str(x) for x in values),
            "res_total_permits": res_total,
            "nr_total_permits": nr_total,
            "total_permits": res_total + nr_total,
            "parse_style": "res_nr_split",
        }

    tokens = [to_int_token(t) for t in NUM_RE.findall(line)]
    if not tokens:
        return {
            "totals_numbers": "",
            "res_total_permits": None,
            "nr_total_permits": None,
            "total_permits": None,
            "parse_style": "no_numbers",
        }

    # Split-style with resident and nonresident totals.
    # In this pattern, 4th number is resident total permits and 8th is nonresident total permits.
    if len(tokens) >= 8:
        res_total = tokens[3]
        nr_total = tokens[7]
        return {
            "totals_numbers": ";".join(str(x) for x in tokens),
            "res_total_permits": res_total,
            "nr_total_permits": nr_total,
            "total_permits": res_total + nr_total,
            "parse_style": "res_nr_split",
        }

    # Compact totals style often "Totals applicants permits"
    if len(tokens) >= 2:
        return {
            "totals_numbers": ";".join(str(x) for x in tokens),
            "res_total_permits": None,
            "nr_total_permits": None,
            "total_permits": tokens[1],
            "parse_style": "compact_totals",
        }

    return {
        "totals_numbers": ";".join(str(x) for x in tokens),
        "res_total_permits": None,
        "nr_total_permits": None,
        "total_permits": None,
        "parse_style": "unparsed",
    }


def parse_pdf_hunt_rows(pdf_path: Path, excluded_pages: set[int] | None = None) -> tuple[list[HuntRow], dict[str, Any]]:
    rows: list[HuntRow] = []
    pages_with_hunt = 0
    pages_with_totals = 0
    pages_no_text = 0
    pages_excluded = 0
    total_pages = 0

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page_idx, page in enumerate(pdf.pages, start=1):
            if excluded_pages and page_idx in excluded_pages:
                pages_excluded += 1
                continue
            text = page.extract_text() or ""
            if not text.strip():
                pages_no_text += 1
                continue
            lines = text.splitlines()
            hunt_line = None
            totals_line = None
            for ln in lines:
                if hunt_line is None and "Hunt:" in ln:
                    m = HUNT_RE.search(ln)
                    if m:
                        hunt_line = (m.group(1).strip().upper(), m.group(2).strip())
                if totals_line is None and TOTALS_LINE_RE.match(ln):
                    totals_line = " ".join(ln.split())
                if hunt_line and totals_line:
                    break

            if hunt_line:
                pages_with_hunt += 1
            if totals_line:
                pages_with_totals += 1

            if hunt_line and totals_line:
                parsed = parse_totals_line(totals_line)
                rows.append(
                    HuntRow(
                        source_file=pdf_path.name,
                        source_page=page_idx,
                        hunt_code=hunt_line[0],
                        hunt_name=hunt_line[1],
                        totals_line=totals_line,
                        totals_numbers=parsed["totals_numbers"],
                        res_total_permits=parsed["res_total_permits"],
                        nr_total_permits=parsed["nr_total_permits"],
                        total_permits=parsed["total_permits"],
                        parse_style=parsed["parse_style"],
                    )
                )

    return rows, {
        "file": str(pdf_path.relative_to(DRAW_DIR)).replace("\\", "/"),
        "pages": total_pages,
        "rows_extracted": len(rows),
        "pages_with_hunt": pages_with_hunt,
        "pages_with_totals": pages_with_totals,
        "pages_no_text": pages_no_text,
        "pages_excluded": pages_excluded,
    }


def compare_subfiles_to_master(sub_df: pd.DataFrame, master_df: pd.DataFrame) -> pd.DataFrame:
    sub = sub_df.copy()
    mst = master_df.copy()

    # Master lookup by hunt_code.
    master_lookup = (
        mst.sort_values(["hunt_code", "source_page"])
        .drop_duplicates(subset=["hunt_code"], keep="first")
        .set_index("hunt_code")
    )

    out_rows: list[dict[str, Any]] = []
    for _, r in sub.iterrows():
        code = str(r["hunt_code"])
        if code not in master_lookup.index:
            out_rows.append(
                {
                    "source_file": r["source_file"],
                    "hunt_code": code,
                    "hunt_name_subfile": r["hunt_name"],
                    "permits_subfile": r["total_permits"],
                    "permits_master": None,
                    "comparison_status": "missing_in_master",
                }
            )
            continue
        mr = master_lookup.loc[code]
        sub_permits = r["total_permits"]
        master_permits = mr["total_permits"]
        status = "permit_match"
        if pd.isna(sub_permits) or pd.isna(master_permits):
            status = "permit_unparsed"
        elif int(sub_permits) != int(master_permits):
            status = "permit_mismatch"
        out_rows.append(
            {
                "source_file": r["source_file"],
                "hunt_code": code,
                "hunt_name_subfile": r["hunt_name"],
                "hunt_name_master": mr["hunt_name"],
                "permits_subfile": sub_permits,
                "permits_master": master_permits,
                "comparison_status": status,
            }
        )

    # Master-only codes not found in any subfile.
    sub_codes = set(sub["hunt_code"].astype(str))
    for _, mr in mst.iterrows():
        code = str(mr["hunt_code"])
        if code in sub_codes:
            continue
        out_rows.append(
            {
                "source_file": MASTER_FILE,
                "hunt_code": code,
                "hunt_name_subfile": None,
                "hunt_name_master": mr["hunt_name"],
                "permits_subfile": None,
                "permits_master": mr["total_permits"],
                "comparison_status": "master_only_code",
            }
        )

    return pd.DataFrame(out_rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(DRAW_DIR.rglob("*.pdf"))
    master_pdf = DRAW_DIR / MASTER_FILE
    if master_pdf not in pdfs:
        raise FileNotFoundError(f"Master PDF not found: {master_pdf}")

    sub_pdfs = [p for p in pdfs if p.resolve() != master_pdf.resolve()]
    all_stats: list[dict[str, Any]] = []

    sub_rows: list[HuntRow] = []
    for pdf in sub_pdfs:
        if not pdf.exists():
            all_stats.append(
                {
                    "file": str(pdf.relative_to(DRAW_DIR)).replace("\\", "/"),
                    "status": "missing_file_skipped",
                }
            )
            continue
        rows, stats = parse_pdf_hunt_rows(pdf)
        sub_rows.extend(rows)
        all_stats.append(stats)

    if not master_pdf.exists():
        raise FileNotFoundError(f"Master PDF not found at runtime: {master_pdf}")

    master_rows, master_stats = parse_pdf_hunt_rows(master_pdf, excluded_pages=EXCLUDED_MASTER_PAGES)
    all_stats.append(master_stats)

    sub_df = pd.DataFrame([asdict(r) for r in sub_rows])
    master_df = pd.DataFrame([asdict(r) for r in master_rows])
    compare_df = compare_subfiles_to_master(sub_df, master_df)

    sub_csv = OUT_DIR / "draw_odds_subfiles_hunt_rows_2024.csv"
    sub_xlsx = OUT_DIR / "draw_odds_subfiles_hunt_rows_2024.xlsx"
    master_csv = OUT_DIR / "draw_odds_master_hunt_rows_2024.csv"
    master_xlsx = OUT_DIR / "draw_odds_master_hunt_rows_2024.xlsx"
    compare_csv = OUT_DIR / "draw_odds_subfiles_vs_master_2024.csv"
    compare_xlsx = OUT_DIR / "draw_odds_subfiles_vs_master_2024.xlsx"
    report_json = OUT_DIR / "draw_odds_subfiles_vs_master_2024_report.json"

    def with_fallback(path: Path) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return path.with_name(f"{path.stem}_{stamp}{path.suffix}")

    def write_csv(df: pd.DataFrame, path: Path) -> Path:
        try:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            return path
        except PermissionError:
            alt = with_fallback(path)
            df.to_csv(alt, index=False, encoding="utf-8-sig")
            return alt

    def write_xlsx(df: pd.DataFrame, path: Path) -> Path:
        try:
            df.to_excel(path, index=False)
            return path
        except PermissionError:
            alt = with_fallback(path)
            df.to_excel(alt, index=False)
            return alt

    sub_csv_written = write_csv(sub_df, sub_csv)
    sub_xlsx_written = write_xlsx(sub_df, sub_xlsx)
    master_csv_written = write_csv(master_df, master_csv)
    master_xlsx_written = write_xlsx(master_df, master_xlsx)
    compare_csv_written = write_csv(compare_df, compare_csv)
    compare_xlsx_written = write_xlsx(compare_df, compare_xlsx)

    report = {
        "master_file": MASTER_FILE,
        "excluded_master_pages": sorted(EXCLUDED_MASTER_PAGES),
        "subfiles_processed": [str(p.relative_to(DRAW_DIR)).replace("\\", "/") for p in sub_pdfs],
        "file_stats": all_stats,
        "subfile_rows_extracted": int(len(sub_df)),
        "subfile_unique_hunt_codes": int(sub_df["hunt_code"].nunique()) if not sub_df.empty else 0,
        "master_rows_extracted": int(len(master_df)),
        "master_unique_hunt_codes": int(master_df["hunt_code"].nunique()) if not master_df.empty else 0,
        "comparison_status_counts": compare_df["comparison_status"].value_counts().to_dict()
        if not compare_df.empty
        else {},
    }
    report["written_files"] = {
        "sub_csv": str(sub_csv_written).replace("\\", "/"),
        "sub_xlsx": str(sub_xlsx_written).replace("\\", "/"),
        "master_csv": str(master_csv_written).replace("\\", "/"),
        "master_xlsx": str(master_xlsx_written).replace("\\", "/"),
        "compare_csv": str(compare_csv_written).replace("\\", "/"),
        "compare_xlsx": str(compare_xlsx_written).replace("\\", "/"),
    }
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {sub_csv_written}")
    print(f"Wrote {sub_xlsx_written}")
    print(f"Wrote {master_csv_written}")
    print(f"Wrote {master_xlsx_written}")
    print(f"Wrote {compare_csv_written}")
    print(f"Wrote {compare_xlsx_written}")
    print(f"Wrote {report_json}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
