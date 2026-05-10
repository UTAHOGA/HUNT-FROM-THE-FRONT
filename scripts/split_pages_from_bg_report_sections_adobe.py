from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import pandas as pd
import pdfplumber


MULTI_PAGES = set([7, 20, 22] + list(range(25, 45)))


def clean_lines(text: str) -> list[str]:
    lines = [" ".join((ln or "").split()).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    # drop bare page-number footer lines
    lines = [ln for ln in lines if not re.fullmatch(r"\d{1,3}", ln)]
    return lines


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()[:80] or "SECTION"


def save_section(
    out_tables: Path,
    manifest_rows: list[dict],
    source_pdf: Path,
    adobe_page: int,
    section_index: int,
    title: str,
    lines: list[str],
    notes: str = "",
):
    base = f"ADOBE_PAGE_{adobe_page:03d}_SECTION_{section_index:02d}_{slug(title)}"
    csv_path = out_tables / f"{base}.csv"
    xlsx_path = out_tables / f"{base}.xlsx"
    df = pd.DataFrame({"line_number": list(range(1, len(lines) + 1)), "text": lines})
    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
    df.to_excel(xlsx_path, index=False)
    manifest_rows.append(
        {
            "source_pdf": str(source_pdf),
            "adobe_page": adobe_page,
            "section_index": section_index,
            "title": title,
            "rows": len(lines),
            "csv_file": str(csv_path),
            "xlsx_file": str(xlsx_path),
            "notes": notes,
        }
    )


def split_page_7(lines: list[str]) -> list[tuple[str, list[str]]]:
    sections = []
    title_idxs = []
    for i, ln in enumerate(lines):
        if "Utah 2024." in ln:
            title_idxs.append(i)
    for s_idx, start in enumerate(title_idxs):
        end = title_idxs[s_idx + 1] if s_idx + 1 < len(title_idxs) else len(lines)
        title = lines[start]
        block = lines[start:end]
        sections.append((title, block))
    return sections


def split_page_20(lines: list[str]) -> list[tuple[str, list[str]]]:
    starts = []
    for i, ln in enumerate(lines):
        if ln.startswith("Adult female deer survival by management unit, Utah 2023"):
            starts.append(i)
        if ln.startswith("Fawn female deer survival by management unit, Utah 2023"):
            starts.append(i)
    starts = sorted(set(starts))
    sections = []
    for s_idx, start in enumerate(starts):
        end = starts[s_idx + 1] if s_idx + 1 < len(starts) else len(lines)
        sections.append((lines[start], lines[start:end]))
    return sections


def split_page_22(lines: list[str]) -> list[tuple[str, list[str]]]:
    starts = []
    for i, ln in enumerate(lines):
        if ln.startswith("Number of postseason buck deer per 100 does for"):
            starts.append(i)
    starts = sorted(set(starts))
    sections = []
    for s_idx, start in enumerate(starts):
        end = starts[s_idx + 1] if s_idx + 1 < len(starts) else len(lines)
        title = lines[start]
        # include wrapped Utah line when present
        if start + 1 < len(lines) and lines[start + 1].startswith("Utah "):
            title = f"{title} {lines[start + 1]}"
        sections.append((title, lines[start:end]))
    return sections


def split_pages_25_44(lines: list[str], page_title: str) -> list[tuple[str, list[str]]]:
    # Unit-section blocks: each starts with a unit name line, followed by repeated header + year rows.
    sections = []
    i = 0
    year_re = re.compile(r"^\d{4}[–-]\d{2}\s+\d+")
    header_re = re.compile(r"^(Fawns per|Year n|100 does|100 adults|% bucks)")

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("Deer postseason classification data by management unit"):
            i += 1
            continue
        if header_re.match(ln):
            i += 1
            continue
        # likely unit label if next few lines include year rows
        lookahead = lines[i + 1 : i + 8]
        if any(year_re.match(x) for x in lookahead):
            unit = ln
            start = i
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if header_re.match(nxt):
                    i += 1
                    continue
                # next unit block detection
                next_look = lines[i + 1 : i + 8]
                if any(year_re.match(x) for x in next_look) and not year_re.match(nxt):
                    break
                if year_re.match(nxt):
                    i += 1
                    continue
                # unexpected line; include and continue cautiously
                i += 1
                # if no year rows ahead, stop this block
                if not any(year_re.match(x) for x in lines[i : i + 4]):
                    break
            end = i
            block = lines[start:end]
            title = f"{page_title} | {unit}"
            sections.append((title, block))
            continue
        i += 1

    return sections


def default_single_section(lines: list[str]) -> list[tuple[str, list[str]]]:
    title = lines[0] if lines else "UNTITLED_SECTION"
    return [(title, lines)]


def split_by_adobe_page(adobe_page: int, lines: list[str]) -> list[tuple[str, list[str], str]]:
    if adobe_page == 7:
        return [(t, b, "adobe_multi_title_split") for t, b in split_page_7(lines)]
    if adobe_page == 20:
        return [(t, b, "adobe_multi_title_split") for t, b in split_page_20(lines)]
    if adobe_page == 22:
        return [(t, b, "adobe_multi_title_split") for t, b in split_page_22(lines)]
    if 25 <= adobe_page <= 44:
        page_title = next((ln for ln in lines if ln.startswith("Deer postseason classification data by management unit")), "Deer postseason classification")
        sec = split_pages_25_44(lines, page_title)
        if sec:
            return [(t, b, "adobe_multi_unit_split") for t, b in sec]
        return [(t, b, "fallback_single") for t, b in default_single_section(lines)]
    return [(t, b, "default_single") for t, b in default_single_section(lines)]


def main():
    parser = argparse.ArgumentParser(description="Split Pages from 24_bg_report-2 by Adobe page sections.")
    parser.add_argument("pdf_path")
    parser.add_argument(
        "--out-dir",
        default="pipeline/RAW/hunt_unit_database/2025/formatted_tables/pages_from_24_bg_report_2_adobe_section_splits",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).resolve()
    out_dir = Path(args.out_dir).resolve()
    tables_dir = out_dir / "tables"
    page_text_dir = out_dir / "page_text"
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    page_text_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for adobe_page, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines = clean_lines(text)
            (page_text_dir / f"ADOBE_PAGE_{adobe_page:03d}.txt").write_text("\n".join(lines), encoding="utf-8")

            sections = split_by_adobe_page(adobe_page, lines)
            for s_idx, (title, block_lines, notes) in enumerate(sections, start=1):
                if not block_lines:
                    continue
                save_section(
                    out_tables=tables_dir,
                    manifest_rows=manifest_rows,
                    source_pdf=pdf_path,
                    adobe_page=adobe_page,
                    section_index=s_idx,
                    title=title,
                    lines=block_lines,
                    notes=notes,
                )

    manifest_df = pd.DataFrame(manifest_rows)
    manifest_csv = out_dir / "section_split_manifest.csv"
    manifest_xlsx = out_dir / "section_split_manifest.xlsx"
    manifest_json = out_dir / "section_split_manifest.json"
    report_txt = out_dir / "section_split_report.txt"

    manifest_df.to_csv(manifest_csv, index=False, encoding="utf-8")
    manifest_df.to_excel(manifest_xlsx, index=False)
    manifest_df.to_json(manifest_json, orient="records", indent=2, force_ascii=False)

    multi_counts = (
        manifest_df.groupby("adobe_page").size().reset_index(name="section_count")
        if not manifest_df.empty
        else pd.DataFrame(columns=["adobe_page", "section_count"])
    )
    with report_txt.open("w", encoding="utf-8") as f:
        f.write("Adobe page section split report\n")
        f.write("===============================\n")
        f.write(f"source_pdf: {pdf_path}\n")
        f.write(f"total_pages: {manifest_df['adobe_page'].max() if not manifest_df.empty else 0}\n")
        f.write(f"total_sections_written: {len(manifest_df)}\n")
        f.write("multi-page targets: 7,20,22,25-44\n")
        f.write("\nsections per page:\n")
        for _, row in multi_counts.iterrows():
            f.write(f"page {int(row['adobe_page'])}: {int(row['section_count'])}\n")

    print(
        json.dumps(
            {
                "source_pdf": str(pdf_path),
                "out_dir": str(out_dir),
                "sections_written": int(len(manifest_df)),
                "manifest_csv": str(manifest_csv),
                "manifest_xlsx": str(manifest_xlsx),
                "manifest_json": str(manifest_json),
                "report_txt": str(report_txt),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

