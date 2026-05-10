from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import pdfplumber


BASE_PDF_DIR = Path(r"pipeline/RAW/hunt_unit_database/2025/pdf/harvest_report/ELK")
BASE_OUT_DIR = Path(r"pipeline/RAW/hunt_unit_database/2025/formatted_tables")
MASTER_REF_PDF = BASE_PDF_DIR / "24_elk_bg_report.pdf"


def clean_token(token: str) -> str:
    t = (token or "").strip()
    if t in {"—", "-", "–"}:
        return ""
    return t


def norm(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("&", " and ").replace("/", " ")
    s = s.replace("mtns", "mountains").replace("mtn", "mountain")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def read_lines(pdf_path: Path) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            lines.extend((page.extract_text() or "").splitlines())
    return lines


def rows_to_outputs(rows: list[dict], out_dir: Path, stem: str) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows extracted for {stem}")

    csv_path = out_dir / f"{stem}.csv"
    xlsx_path = out_dir / f"{stem}.xlsx"
    manifest_path = out_dir / f"{stem}_manifest.json"

    cols = list(rows[0].keys())
    pd.DataFrame(rows, columns=cols).to_csv(csv_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(rows, columns=cols).to_excel(xlsx_path, index=False)

    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "stem": stem,
                "rows": len(rows),
                "columns": cols,
                "csv": str(csv_path).replace("\\", "/"),
                "xlsx": str(xlsx_path).replace("\\", "/"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return csv_path, xlsx_path, manifest_path


def extract_historical_unit_years(pdf_name: str, out_dir_name: str, stem: str, title_filter: str) -> dict:
    pdf_path = BASE_PDF_DIR / pdf_name
    line_re = re.compile(
        r"^(\S+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)$"
    )
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            for raw in (page.extract_text() or "").splitlines():
                line = raw.strip()
                if not line:
                    continue
                if line.startswith(title_filter):
                    continue
                if line.startswith("Unit Unit name"):
                    continue
                if line.startswith("*Data includes"):
                    continue
                if line.isdigit():
                    continue
                m = line_re.match(line)
                if not m:
                    continue
                g = m.groups()
                rows.append(
                    {
                        "Unit": g[0],
                        "Unit name": g[1],
                        "2015": clean_token(g[2]),
                        "2016": clean_token(g[3]),
                        "2017": clean_token(g[4]),
                        "2018": clean_token(g[5]),
                        "2019": clean_token(g[6]),
                        "2020": clean_token(g[7]),
                        "2021": clean_token(g[8]),
                        "2022": clean_token(g[9]),
                        "2023": clean_token(g[10]),
                        "2024": clean_token(g[11]),
                        "source_page": page_idx,
                    }
                )
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / out_dir_name, stem)
    return {"pdf": pdf_name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_bull_by_unit_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "2024 ELK BULL BY UNIT.pdf"
    p1_re = re.compile(
        r"^(\S+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9.—-]+)\s+([0-9.—-]+)$"
    )
    rows_total: list[dict] = []
    rows_archery: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        # Page 1: Total elk harvest by unit, 2024
        for line in (pdf.pages[0].extract_text() or "").splitlines():
            s = line.strip()
            if not s or s.isdigit():
                continue
            if s.startswith("Total elk harvest by management unit"):
                continue
            if s.startswith("Bull Antlerless Total Hunters Mean days Success rate"):
                continue
            if s.startswith("Unit Unit name"):
                continue
            if s.startswith("harvest harvest harvest afield hunted"):
                continue
            if s.startswith("*"):
                continue
            m = p1_re.match(s)
            if not m:
                continue
            g = m.groups()
            rows_total.append(
                {
                    "Unit": g[0],
                    "Unit name": g[1],
                    "Bull harvest": clean_token(g[2]),
                    "Antlerless harvest": clean_token(g[3]),
                    "Total harvest": clean_token(g[4]),
                    "Hunters afield": clean_token(g[5]),
                    "Mean days hunted": clean_token(g[6]),
                    "Success rate (%)": clean_token(g[7]),
                }
            )

        # Page 2: General-season archery elk harvest by unit, 2024
        p2_re = re.compile(
            r"^(\S+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9.—-]+)\s+([0-9.—-]+)$"
        )
        for line in (pdf.pages[1].extract_text() or "").splitlines():
            s = line.strip()
            if not s or s.isdigit():
                continue
            if s.startswith("General-season archery elk harvest by management unit"):
                continue
            if s.startswith("Bull Cow Calf Total Hunters Mean days Success rate"):
                continue
            if s.startswith("Unit Unit name"):
                continue
            if s.startswith("harvest harvest harvest harvest afield"):
                continue
            if s.startswith("*"):
                continue
            if s.startswith("Statewide totals"):
                continue
            m = p2_re.match(s)
            if not m:
                continue
            g = m.groups()
            rows_archery.append(
                {
                    "Unit": g[0],
                    "Unit name": g[1],
                    "Bull harvest": clean_token(g[2]),
                    "Cow harvest": clean_token(g[3]),
                    "Calf harvest": clean_token(g[4]),
                    "Total harvest": clean_token(g[5]),
                    "Hunters afield": clean_token(g[6]),
                    "Success rate (%)": clean_token(g[7]),
                }
            )

    out_dir = BASE_OUT_DIR / "elk_bull_by_unit_2024_extract"
    c1, x1, _ = rows_to_outputs(rows_total, out_dir, "ELK_TOTAL_HARVEST_BY_UNIT_2024")
    c2, x2, _ = rows_to_outputs(rows_archery, out_dir, "ELK_GENERAL_SEASON_ARCHERY_HARVEST_BY_UNIT_2024")
    return {"pdf": pdf_path.name, "rows_total_table": len(rows_total), "rows_archery_table": len(rows_archery), "csv_total": str(c1), "csv_archery": str(c2), "xlsx_total": str(x1), "xlsx_archery": str(x2)}


def extract_cwmu_bull_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "2024 ELK CWMU bull elk harvest.pdf"
    row_re = re.compile(
        r"^(\S+)\s+(EB\d+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9.—-]+)\s+([0-9.—-]+)$"
    )
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            for line in (page.extract_text() or "").splitlines():
                s = line.strip()
                if not s or s.isdigit():
                    continue
                if s.startswith("CWMU bull elk harvest"):
                    continue
                if s.startswith("Hunt Bull Hunters Mean days Success"):
                    continue
                if s.startswith("Unit CWMU name Permits"):
                    continue
                if s.startswith("number harvest afield hunted"):
                    continue
                m = row_re.match(s)
                if not m:
                    continue
                g = m.groups()
                rows.append(
                    {
                        "Unit": g[0],
                        "Hunt number": g[1],
                        "CWMU name": g[2],
                        "Permits": clean_token(g[3]),
                        "Bull harvest": clean_token(g[4]),
                        "Hunters afield": clean_token(g[5]),
                        "Mean days hunted": clean_token(g[6]),
                        "Success rate (%)": clean_token(g[7]),
                        "source_page": page_idx,
                    }
                )
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_cwmu_bull_harvest_2024_extract", "ELK_CWMU_BULL_HARVEST_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_general_extended_archery_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "2024 ELK GENERAL EXTENDED ARCHERY HARVEST.pdf"
    row_re = re.compile(
        r"^(\S+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9.—-]+)$"
    )
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for line in (pdf.pages[0].extract_text() or "").splitlines():
            s = line.strip()
            if not s or s.isdigit():
                continue
            if s.startswith("General-season extended archery elk harvest by management unit"):
                continue
            if s.startswith("Unit Unit name Bull harvest Cow harvest"):
                continue
            if s.startswith("*"):
                continue
            if s.startswith("Statewide totals"):
                continue
            m = row_re.match(s)
            if not m:
                continue
            g = m.groups()
            rows.append(
                {
                    "Unit": g[0],
                    "Unit name": g[1],
                    "Bull harvest": clean_token(g[2]),
                    "Cow harvest": clean_token(g[3]),
                    "Calf harvest": clean_token(g[4]),
                    "Total harvest": clean_token(g[5]),
                    "Hunters afield": clean_token(g[6]),
                    "Success rate (%)": clean_token(g[7]),
                }
            )
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_general_extended_archery_2024_extract", "ELK_GENERAL_EXTENDED_ARCHERY_HARVEST_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_limited_antlerless_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "2024 ELK LIMITED ANTLERLESS.pdf"
    full_re = re.compile(
        r"^(\S+)\s+(EA\d+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9.—-]+)\s+([0-9.—-]+)$"
    )
    no_name_re = re.compile(
        r"^(\S+)\s+(EA\d+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9.—-]+)\s+([0-9.—-]+)$"
    )
    rows: list[dict] = []
    current_section = ""
    pending_name = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            for raw in (page.extract_text() or "").splitlines():
                s = raw.strip()
                if not s or s.isdigit():
                    continue

                if s.startswith("Limited-entry archery antlerless elk harvest"):
                    current_section = "Limited-entry archery antlerless elk harvest"
                    pending_name = ""
                    continue
                if s.startswith("Limited-entry muzzleloader antlerless elk harvest"):
                    current_section = "Limited-entry muzzleloader antlerless elk harvest"
                    pending_name = ""
                    continue
                if s.startswith("Limited-entry any legal weapon antlerless elk harvest"):
                    current_section = "Limited-entry any legal weapon antlerless elk harvest"
                    pending_name = ""
                    continue
                if s.startswith("Cow Calf Total Hunters Mean days Success") or s.startswith("Unit Hunt number Hunt name Permits"):
                    continue
                if s.startswith("harvest harvest harvest afield") or s.startswith("*"):
                    continue

                m = full_re.match(s)
                if m:
                    g = m.groups()
                    rows.append(
                        {
                            "Section": current_section,
                            "Unit": g[0],
                            "Hunt number": g[1],
                            "Hunt name": g[2],
                            "Cow harvest": clean_token(g[3]),
                            "Calf harvest": clean_token(g[4]),
                            "Total harvest": clean_token(g[5]),
                            "Permits": clean_token(g[6]),
                            "Hunters afield": clean_token(g[7]),
                            "Mean days hunted": clean_token(g[8]),
                            "Success rate (%)": clean_token(g[9]),
                            "source_page": page_idx,
                        }
                    )
                    pending_name = ""
                    continue

                m2 = no_name_re.match(s)
                if m2 and pending_name:
                    g = m2.groups()
                    rows.append(
                        {
                            "Section": current_section,
                            "Unit": g[0],
                            "Hunt number": g[1],
                            "Hunt name": pending_name,
                            "Cow harvest": clean_token(g[2]),
                            "Calf harvest": clean_token(g[3]),
                            "Total harvest": clean_token(g[4]),
                            "Permits": clean_token(g[5]),
                            "Hunters afield": clean_token(g[6]),
                            "Mean days hunted": clean_token(g[7]),
                            "Success rate (%)": clean_token(g[8]),
                            "source_page": page_idx,
                        }
                    )
                    pending_name = ""
                    continue

                # likely wrapped hunt name line
                if "," in s and not re.match(r"^\S+\s+EA\d+", s):
                    pending_name = s

    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_limited_antlerless_2024_extract", "ELK_LIMITED_ANTLERLESS_HARVEST_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_youth_any_bull_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "2024 ELK LIMITED ENTRY youth any bull hunters choice elk harvest.pdf"
    row_re = re.compile(
        r"^(\S+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9.—-]+)\s+([0-9.—-]+)$"
    )
    rows: list[dict] = []
    section = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            for raw in (page.extract_text() or "").splitlines():
                s = raw.strip()
                if not s or s.isdigit():
                    continue
                if s.startswith("General-season draw-only youth any bull/hunter"):
                    section = "General-season draw-only youth any bull/hunter's choice elk harvest"
                    continue
                if s == "2024.":
                    continue
                if s.startswith("General-season youth multiseason elk harvest"):
                    section = "General-season youth multiseason elk harvest"
                    continue
                if s.startswith("Bull Cow Calf Total Hunters Mean days Success"):
                    continue
                if s.startswith("Unit Unit name"):
                    continue
                if s.startswith("harvest harvest harvest harvest afield"):
                    continue
                if s.startswith("*") or s.startswith("Statewide totals"):
                    continue
                m = row_re.match(s)
                if not m:
                    continue
                g = m.groups()
                rows.append(
                    {
                        "Section": section,
                        "Unit": g[0],
                        "Unit name": g[1],
                        "Bull harvest": clean_token(g[2]),
                        "Cow harvest": clean_token(g[3]),
                        "Calf harvest": clean_token(g[4]),
                        "Total harvest": clean_token(g[5]),
                        "Hunters afield": clean_token(g[6]),
                        "Mean days hunted": clean_token(g[7]),
                        "Success rate (%)": clean_token(g[8]),
                        "source_page": page_idx,
                    }
                )
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_youth_any_bull_hunters_choice_2024_extract", "ELK_YOUTH_ANY_BULL_HUNTERS_CHOICE_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_statewide_stats_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "2024 ELK STATEWIDE STATS.pdf"
    p1_re = re.compile(r"^(\d{4}\*?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)$")
    p23_re = re.compile(r"^(\d{4}\*?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)$")
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            for raw in (page.extract_text() or "").splitlines():
                s = raw.strip()
                if not s or s.isdigit():
                    continue
                if s.startswith("Statewide elk harvest statistics"):
                    continue
                if s.startswith("Year Bull harvest"):
                    continue
                if s.startswith("*In 2001 and 2002"):
                    continue
                m = p1_re.match(s)
                if m:
                    g = m.groups()
                    rows.append(
                        {
                            "Year": g[0].replace("*", ""),
                            "Bull harvest": clean_token(g[1]),
                            "Cow harvest": clean_token(g[2]),
                            "Calf harvest": clean_token(g[3]),
                            "Antlerless harvest": "",
                            "Unknown harvest": clean_token(g[4]),
                            "Total harvest": clean_token(g[5]),
                            "Hunters afield": clean_token(g[6]),
                            "source_page": page_idx,
                        }
                    )
                    continue
                m2 = p23_re.match(s)
                if m2:
                    g = m2.groups()
                    rows.append(
                        {
                            "Year": g[0].replace("*", ""),
                            "Bull harvest": clean_token(g[1]),
                            "Cow harvest": "",
                            "Calf harvest": "",
                            "Antlerless harvest": clean_token(g[2]),
                            "Unknown harvest": "",
                            "Total harvest": clean_token(g[3]),
                            "Hunters afield": clean_token(g[4]),
                            "source_page": page_idx,
                        }
                    )
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_statewide_stats_1931_2024_extract", "ELK_STATEWIDE_HARVEST_STATS_1931_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_winter_population_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "ELK 2024 WINTER POPULATION.pdf"
    row_re = re.compile(r"^(\S+)\s+(.+?)\s+([0-9]+(?:-[0-9]+)?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)$")
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for s in (pdf.pages[0].extract_text() or "").splitlines():
            t = s.strip()
            if not t or t.isdigit():
                continue
            if t.startswith("Elk winter population estimates and objectives"):
                continue
            if t.startswith("Unit Unit name Objective"):
                continue
            m = row_re.match(t)
            if not m:
                continue
            g = m.groups()
            rows.append(
                {
                    "Unit": g[0],
                    "Unit name": g[1],
                    "Objective": clean_token(g[2]),
                    "2020": clean_token(g[3]),
                    "2021": clean_token(g[4]),
                    "2022": clean_token(g[5]),
                    "2023": clean_token(g[6]),
                    "2024": clean_token(g[7]),
                }
            )
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_winter_population_2020_2024_extract", "ELK_WINTER_POPULATION_ESTIMATES_2020_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_preseason_calf_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "PRESEASON CALF ELK PER 100 COWS 2015–2024.pdf"
    row_re = re.compile(
        r"^(\S+)\s+(.+?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)$"
    )
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for s in (pdf.pages[0].extract_text() or "").splitlines():
            t = s.strip()
            if not t or t.isdigit():
                continue
            if t.startswith("Number of preseason calf elk per 100 cows"):
                continue
            if t.startswith("Unit Unit name 2015 2016"):
                continue
            m = row_re.match(t)
            if not m:
                continue
            g = m.groups()
            rows.append(
                {
                    "Unit": g[0],
                    "Unit name": g[1],
                    "2015": clean_token(g[2]),
                    "2016": clean_token(g[3]),
                    "2017": clean_token(g[4]),
                    "2018": clean_token(g[5]),
                    "2019": clean_token(g[6]),
                    "2020": clean_token(g[7]),
                    "2021": clean_token(g[8]),
                    "2022": clean_token(g[9]),
                    "2023": clean_token(g[10]),
                    "2024": clean_token(g[11]),
                }
            )
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_preseason_calf_per_100_cows_2015_2024_extract", "ELK_PRESEASON_CALF_PER_100_COWS_2015_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def extract_winter_trend_2024() -> dict:
    pdf_path = BASE_PDF_DIR / "2024 ELK WINTER TREND.pdf"
    year_re = re.compile(r"^(\d{4}[–-]\d{2}\*?)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)\s+([0-9—-]+)$")
    rows: list[dict] = []
    current_unit = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            for raw in (page.extract_text() or "").splitlines():
                s = raw.strip()
                if not s or s.isdigit():
                    continue
                if s.startswith("Elk winter trend count data by management unit"):
                    continue
                if s.startswith("Calves per Bulls per Mature bulls per") or s.startswith("Year n") or s.startswith("100 cows"):
                    continue
                if s.startswith("*"):
                    continue
                ym = year_re.match(s)
                if ym:
                    g = ym.groups()
                    rows.append(
                        {
                            "Unit name": current_unit,
                            "Year": g[0].replace("*", ""),
                            "n": clean_token(g[1]),
                            "Calves per 100 cows": clean_token(g[2]),
                            "Bulls per 100 cows": clean_token(g[3]),
                            "Mature bulls per 100 cows": clean_token(g[4]),
                            "source_page": page_idx,
                        }
                    )
                    continue
                # anything else is likely a unit title
                current_unit = s
    c, x, m = rows_to_outputs(rows, BASE_OUT_DIR / "elk_winter_trend_2015_2024_extract", "ELK_WINTER_TREND_2015_2024")
    return {"pdf": pdf_path.name, "rows": len(rows), "csv": str(c), "xlsx": str(x), "manifest": str(m)}


def crosscheck_vs_master(output_csvs: Iterable[Path]) -> tuple[Path, Path]:
    with pdfplumber.open(MASTER_REF_PDF) as pdf:
        master_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    master_norm = norm(master_text)

    rows: list[dict] = []
    for csv_path in output_csvs:
        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            rd = csv.DictReader(f)
            recs = list(rd)
        unit_col = "Unit name" if recs and "Unit name" in recs[0] else ("CWMU name" if recs and "CWMU name" in recs[0] else "")
        if not unit_col:
            rows.append(
                {
                    "file": str(csv_path).replace("\\", "/"),
                    "rows": len(recs),
                    "unit_col": "",
                    "unit_rows_checked": 0,
                    "unit_name_matches_in_master": 0,
                    "unit_name_match_rate": "",
                    "note": "no_unit_name_column",
                }
            )
            continue
        unit_vals = [r.get(unit_col, "").strip() for r in recs if (r.get(unit_col, "").strip())]
        checked = len(unit_vals)
        matched = sum(1 for u in unit_vals if norm(u) and norm(u) in master_norm)
        rate = round((matched / checked) * 100.0, 2) if checked else 0.0
        rows.append(
            {
                "file": str(csv_path).replace("\\", "/"),
                "rows": len(recs),
                "unit_col": unit_col,
                "unit_rows_checked": checked,
                "unit_name_matches_in_master": matched,
                "unit_name_match_rate": rate,
                "note": "",
            }
        )

    out_csv = BASE_OUT_DIR / "elk_2024_crosscheck_vs_master.csv"
    out_json = BASE_OUT_DIR / "elk_2024_crosscheck_vs_master.json"
    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8-sig")
    out_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "master_reference_pdf": str(MASTER_REF_PDF).replace("\\", "/"),
                "files_checked": len(rows),
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return out_csv, out_json


def main() -> None:
    summary: list[dict] = []

    summary.append(extract_historical_unit_years("2024 ELK BY UNIT HISTORICAL 2015–2024.pdf", "elk_by_unit_historical_2015_2024_extract", "ELK_BULL_BY_UNIT_2015_2024", "Total bull elk harvest by management unit"))
    summary.append(extract_bull_by_unit_2024())
    summary.append(extract_cwmu_bull_2024())
    summary.append(extract_general_extended_archery_2024())
    summary.append(extract_limited_antlerless_2024())
    summary.append(extract_youth_any_bull_2024())
    summary.append(extract_statewide_stats_2024())
    summary.append(extract_winter_population_2024())
    summary.append(extract_preseason_calf_2024())
    summary.append(extract_winter_trend_2024())

    out_csvs: list[Path] = []
    for entry in summary:
        for k in ("csv", "csv_total", "csv_archery"):
            if k in entry:
                out_csvs.append(Path(entry[k]))

    c_csv, c_json = crosscheck_vs_master(out_csvs)
    summary_path = BASE_OUT_DIR / "elk_harvest_bundle_2024_extract_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "summary": summary,
                "crosscheck_csv": str(c_csv).replace("\\", "/"),
                "crosscheck_json": str(c_json).replace("\\", "/"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {summary_path}")
    print(f"Wrote {c_csv}")
    print(f"Wrote {c_json}")


if __name__ == "__main__":
    main()
