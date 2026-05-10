from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import pdfplumber


WEAPON_SUFFIXES = [
    "Archery, muzzleloader, shotgun",
    "Any legal weapon",
    "Archery",
    "Muzzleloader",
    "Shotgun",
]


def clean_lines(text: str) -> list[str]:
    lines = [" ".join((ln or "").split()).strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def to_int(value: str | None):
    if value is None:
        return None
    v = value.strip().replace(",", "")
    if not v or v in {"*", "**", "—"}:
        return None
    if v.endswith("*"):
        v = v[:-1]
    if v == "":
        return None
    try:
        return int(v)
    except ValueError:
        return None


def to_float(value: str | None):
    if value is None:
        return None
    v = value.strip().replace(",", "")
    if not v or v in {"*", "**", "—"}:
        return None
    if v.endswith("*"):
        v = v[:-1]
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def footer_number(lines: list[str]) -> str:
    for ln in reversed(lines):
        if re.fullmatch(r"\d{1,3}", ln):
            return ln
    return ""


def parse_general_season_page(lines: list[str], adobe_page: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    # columns:
    # Unit, Hunt number, Hunt name, Buck harvest, Permits, Hunters afield, Mean days hunted, Success rate (%)
    data = []
    notes = []

    row_re = re.compile(
        r"^(?P<unit>\S+)\s+(?P<hunt_code>[A-Z]{2}\d{4})\s+(?P<hunt_name>.+?)\s+"
        r"(?P<buck>\d+)\s+(?P<permits>\d+)\s+(?P<hunters>\d+)\s+"
        r"(?P<mean>\d+(?:\.\d+)?)\s+(?P<success>\d+(?:\.\d+)?)$"
    )
    totals_re = re.compile(
        r"^Statewide totals\s+(?P<buck>\d+)\s+(?P<permits>\d+)\s+(?P<hunters>\d+)\s+"
        r"(?P<mean>\d+(?:\.\d+)?)\s+(?P<success>\d+(?:\.\d+)?)$"
    )

    for ln in lines:
        m = row_re.match(ln)
        if m:
            data.append(
                {
                    "Unit": m.group("unit"),
                    "Hunt number": m.group("hunt_code"),
                    "Hunt name": m.group("hunt_name"),
                    "Buck harvest": to_int(m.group("buck")),
                    "Permits": to_int(m.group("permits")),
                    "Hunters afield": to_int(m.group("hunters")),
                    "Mean days hunted": to_float(m.group("mean")),
                    "Success rate (%)": to_float(m.group("success")),
                    "adobe_page": adobe_page,
                }
            )
            continue
        t = totals_re.match(ln)
        if t:
            data.append(
                {
                    "Unit": "",
                    "Hunt number": "",
                    "Hunt name": "Statewide totals",
                    "Buck harvest": to_int(t.group("buck")),
                    "Permits": to_int(t.group("permits")),
                    "Hunters afield": to_int(t.group("hunters")),
                    "Mean days hunted": to_float(t.group("mean")),
                    "Success rate (%)": to_float(t.group("success")),
                    "adobe_page": adobe_page,
                }
            )
            continue
        if ln.startswith("*"):
            notes.append({"adobe_page": adobe_page, "note": ln})

    return pd.DataFrame(data), pd.DataFrame(notes)


def split_name_weapon(rest: str) -> tuple[str, str]:
    for weapon in WEAPON_SUFFIXES:
        if rest.endswith(weapon):
            name = rest[: -len(weapon)].strip().rstrip(",")
            return name, weapon
    return rest.strip(), ""


def parse_limited_entry_antlerless(lines: list[str], adobe_page: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Unit Hunt number Hunt name Weapon type Doe Fawn Total Permits Hunters Mean Success
    data = []
    notes = []
    row_re = re.compile(
        r"^(?P<unit>\S+)\s+(?P<hunt_code>[A-Z]{2}\d{4})\s+(?P<rest>.+?)\s+"
        r"(?P<doe>\d+)\s+(?P<fawn>\d+)\s+(?P<total>\d+)\s+(?P<permits>\d+)\s+"
        r"(?P<hunters>\d+)\s+(?P<mean>\d+(?:\.\d+)?)\s+(?P<success>\d+(?:\.\d+)?)$"
    )
    for ln in lines:
        m = row_re.match(ln)
        if m:
            hunt_name, weapon = split_name_weapon(m.group("rest"))
            data.append(
                {
                    "Unit": m.group("unit"),
                    "Hunt number": m.group("hunt_code"),
                    "Hunt name": hunt_name,
                    "Weapon type": weapon,
                    "Doe harvest": to_int(m.group("doe")),
                    "Fawn harvest": to_int(m.group("fawn")),
                    "Total harvest": to_int(m.group("total")),
                    "Permits": to_int(m.group("permits")),
                    "Hunters afield": to_int(m.group("hunters")),
                    "Mean days hunted": to_float(m.group("mean")),
                    "Success rate (%)": to_float(m.group("success")),
                    "adobe_page": adobe_page,
                }
            )
            continue
        if ln.startswith("*"):
            notes.append({"adobe_page": adobe_page, "note": ln})
    return pd.DataFrame(data), pd.DataFrame(notes)


def parse_cwmu_antlerless(lines: list[str], adobe_page: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Unit Hunt number CWMU name Doe Fawn Total Permits Hunters Mean Success
    data = []
    notes = []
    row_re = re.compile(
        r"^(?P<unit>\S+)\s+(?P<hunt_code>[A-Z]{2}\d{4}\*?)\s+(?P<name>.+?)\s+"
        r"(?P<doe>\d+)\s+(?P<fawn>\d+)\s+(?P<total>\d+)\s+(?P<permits>\d+)\s+"
        r"(?P<hunters>\d+)\s+(?P<mean>\d+(?:\.\d+)?)\s+(?P<success>\d+(?:\.\d+)?)$"
    )
    for ln in lines:
        m = row_re.match(ln)
        if m:
            data.append(
                {
                    "Unit": m.group("unit"),
                    "Hunt number": m.group("hunt_code").replace("*", ""),
                    "CWMU name": m.group("name"),
                    "Doe harvest": to_int(m.group("doe")),
                    "Fawn harvest": to_int(m.group("fawn")),
                    "Total harvest": to_int(m.group("total")),
                    "Permits": to_int(m.group("permits")),
                    "Hunters afield": to_int(m.group("hunters")),
                    "Mean days hunted": to_float(m.group("mean")),
                    "Success rate (%)": to_float(m.group("success")),
                    "adobe_page": adobe_page,
                }
            )
            continue
        if ln.startswith("*"):
            notes.append({"adobe_page": adobe_page, "note": ln})
    return pd.DataFrame(data), pd.DataFrame(notes)


def parse_landowner_mitigation(lines: list[str], adobe_page: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Unit Unit name Doe Fawn Total Permits Hunters Success
    data = []
    notes = []
    row_re = re.compile(
        r"^(?P<unit>\S+)\s+(?P<name>.+?)\s+"
        r"(?P<doe>\d+)\s+(?P<fawn>\d+)\s+(?P<total>\d+)\s+(?P<permits>\d+)\s+"
        r"(?P<hunters>\d+)\s+(?P<success>\d+(?:\.\d+)?)$"
    )
    totals_re = re.compile(
        r"^Statewide totals\s+(?P<doe>\d+)\s+(?P<fawn>\d+)\s+(?P<total>\d+)\s+(?P<permits>\d+)\s+"
        r"(?P<hunters>\d+)\s+(?P<success>\d+(?:\.\d+)?)$"
    )

    for ln in lines:
        m = row_re.match(ln)
        if m:
            data.append(
                {
                    "Unit": m.group("unit"),
                    "Unit name": m.group("name"),
                    "Doe harvest": to_int(m.group("doe")),
                    "Fawn harvest": to_int(m.group("fawn")),
                    "Total harvest": to_int(m.group("total")),
                    "Permits": to_int(m.group("permits")),
                    "Hunters afield": to_int(m.group("hunters")),
                    "Success rate (%)": to_float(m.group("success")),
                    "adobe_page": adobe_page,
                }
            )
            continue
        t = totals_re.match(ln)
        if t:
            data.append(
                {
                    "Unit": "",
                    "Unit name": "Statewide totals",
                    "Doe harvest": to_int(t.group("doe")),
                    "Fawn harvest": to_int(t.group("fawn")),
                    "Total harvest": to_int(t.group("total")),
                    "Permits": to_int(t.group("permits")),
                    "Hunters afield": to_int(t.group("hunters")),
                    "Success rate (%)": to_float(t.group("success")),
                    "adobe_page": adobe_page,
                }
            )
            continue
        if ln.startswith("*"):
            notes.append({"adobe_page": adobe_page, "note": ln})
    return pd.DataFrame(data), pd.DataFrame(notes)


def parse_age_table(lines: list[str], adobe_page: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = []
    notes = []
    row_re = re.compile(r"^(?P<year>\d{4}|3-yr average)\s+(?P<avg>\d+(?:\.\d+)?)\s+(?P<pct>\d+%)$")
    for ln in lines:
        m = row_re.match(ln)
        if m:
            data.append(
                {
                    "Year": m.group("year"),
                    "Average age": to_float(m.group("avg")),
                    "Percent 5+ years old": m.group("pct"),
                    "adobe_page": adobe_page,
                }
            )
        elif ln.startswith("*"):
            notes.append({"adobe_page": adobe_page, "note": ln})
    return pd.DataFrame(data), pd.DataFrame(notes)


def parse_fawn_100(lines: list[str], adobe_page: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = []
    notes = []
    years = [str(y) for y in range(2015, 2025)]
    row_re = re.compile(
        r"^(?P<unit>\S+)\s+(?P<name>.+?)\s+"
        r"(?P<y2015>\S+)\s+(?P<y2016>\S+)\s+(?P<y2017>\S+)\s+(?P<y2018>\S+)\s+"
        r"(?P<y2019>\S+)\s+(?P<y2020>\S+)\s+(?P<y2021>\S+)\s+(?P<y2022>\S+)\s+"
        r"(?P<y2023>\S+)\s+(?P<y2024>\S+)$"
    )
    avg_re = re.compile(
        r"^Statewide averages\s+"
        r"(?P<y2015>\S+)\s+(?P<y2016>\S+)\s+(?P<y2017>\S+)\s+(?P<y2018>\S+)\s+"
        r"(?P<y2019>\S+)\s+(?P<y2020>\S+)\s+(?P<y2021>\S+)\s+(?P<y2022>\S+)\s+"
        r"(?P<y2023>\S+)\s+(?P<y2024>\S+)$"
    )
    for ln in lines:
        m = row_re.match(ln)
        if m:
            # Skip header-like lines accidentally matched.
            if m.group("unit").lower() == "unit":
                continue
            if not re.match(r"^\d+[A-Z]*(?:/[0-9A-Z]+)?$", m.group("unit")):
                continue
            row = {"Unit": m.group("unit"), "Unit name": m.group("name"), "adobe_page": adobe_page}
            for y in years:
                row[y] = to_int(m.group(f"y{y}"))
            data.append(row)
            continue
        a = avg_re.match(ln)
        if a:
            row = {"Unit": "", "Unit name": "Statewide averages", "adobe_page": adobe_page}
            for y in years:
                row[y] = to_int(a.group(f"y{y}"))
            data.append(row)
            continue
        if ln.startswith("*"):
            notes.append({"adobe_page": adobe_page, "note": ln})
    return pd.DataFrame(data), pd.DataFrame(notes)


def collect_page_lines(pdf: Path, adobe_pages: Iterable[int]) -> dict[int, list[str]]:
    out = {}
    with pdfplumber.open(str(pdf)) as doc:
        for p in adobe_pages:
            text = doc.pages[p - 1].extract_text() or ""
            out[p] = clean_lines(text)
    return out


def write_table_with_notes(df: pd.DataFrame, notes: pd.DataFrame, out_base: Path):
    out_base.parent.mkdir(parents=True, exist_ok=True)
    csv_path = out_base.with_suffix(".csv")
    xlsx_path = out_base.with_suffix(".xlsx")
    df.to_csv(csv_path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
        if notes is not None and not notes.empty:
            notes.to_excel(writer, index=False, sheet_name="notes")
    return str(csv_path), str(xlsx_path)


def main():
    parser = argparse.ArgumentParser(description="Strict re-extraction for target Pages from 24_bg_report-2 tables.")
    parser.add_argument("pdf_path")
    parser.add_argument(
        "--out-dir",
        default="pipeline/RAW/hunt_unit_database/2025/formatted_tables/pages_from_24_bg_report_2_strict_tables",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    page_map = collect_page_lines(pdf_path, [1, 3, 4, 5, 13, 14, 15, 17, 23, 24])

    report = {
        "source_pdf": str(pdf_path),
        "outputs": {},
        "footers_by_page": {str(p): footer_number(lines) for p, lines in page_map.items()},
    }

    # 1) General-season deer weapon category tables (pages 1,3,4,5)
    gs_frames = []
    gs_notes = []
    for p in [1, 3, 4, 5]:
        df, notes = parse_general_season_page(page_map[p], p)
        df["table_title"] = page_map[p][0] if page_map[p] else ""
        gs_frames.append(df)
        if not notes.empty:
            notes["table_title"] = page_map[p][0] if page_map[p] else ""
            gs_notes.append(notes)
    gs_df = pd.concat(gs_frames, ignore_index=True) if gs_frames else pd.DataFrame()
    gs_notes_df = pd.concat(gs_notes, ignore_index=True) if gs_notes else pd.DataFrame()
    gs_csv, gs_xlsx = write_table_with_notes(
        gs_df,
        gs_notes_df,
        out_dir / "GENERAL_SEASON_DEER_WEAPON_CATEGORIES_PAGES_1_3_4_5",
    )
    report["outputs"]["general_season_weapon_categories"] = {"csv": gs_csv, "xlsx": gs_xlsx, "rows": int(len(gs_df))}

    # 2) Requested pages 13,14,15,17 as separate strict tables
    p13_df, p13_notes = parse_limited_entry_antlerless(page_map[13], 13)
    p13_csv, p13_xlsx = write_table_with_notes(
        p13_df, p13_notes, out_dir / "PAGE_13_LIMITED_ENTRY_ANTLERLESS_DEER_HARVEST_2024"
    )
    report["outputs"]["page_13_limited_entry_antlerless"] = {"csv": p13_csv, "xlsx": p13_xlsx, "rows": int(len(p13_df))}

    p14_df, p14_notes = parse_cwmu_antlerless(page_map[14], 14)
    p14_csv, p14_xlsx = write_table_with_notes(
        p14_df, p14_notes, out_dir / "PAGE_14_CWMU_ANTLERLESS_DEER_HARVEST_2024"
    )
    report["outputs"]["page_14_cwmu_antlerless"] = {"csv": p14_csv, "xlsx": p14_xlsx, "rows": int(len(p14_df))}

    p15_df, p15_notes = parse_landowner_mitigation(page_map[15], 15)
    p15_csv, p15_xlsx = write_table_with_notes(
        p15_df, p15_notes, out_dir / "PAGE_15_LANDOWNER_FREE_PERMIT_DEER_MITIGATION_HARVEST_2024"
    )
    report["outputs"]["page_15_landowner_mitigation"] = {"csv": p15_csv, "xlsx": p15_xlsx, "rows": int(len(p15_df))}

    p17_df, p17_notes = parse_age_table(page_map[17], 17)
    p17_csv, p17_xlsx = write_table_with_notes(
        p17_df, p17_notes, out_dir / "PAGE_17_HENRY_MTNS_AVERAGE_AGE_2005_2024"
    )
    report["outputs"]["page_17_henry_age"] = {"csv": p17_csv, "xlsx": p17_xlsx, "rows": int(len(p17_df))}

    # 3) Multi-page single table pages 23-24
    p23_df, p23_notes = parse_fawn_100(page_map[23], 23)
    p24_df, p24_notes = parse_fawn_100(page_map[24], 24)
    fawn_df = pd.concat([p23_df, p24_df], ignore_index=True)
    fawn_notes = pd.concat([p23_notes, p24_notes], ignore_index=True)
    fawn_csv, fawn_xlsx = write_table_with_notes(
        fawn_df,
        fawn_notes,
        out_dir / "PAGES_23_24_POSTSEASON_FAWN_DEER_PER_100_DOES_2015_2024",
    )
    report["outputs"]["pages_23_24_fawn_100"] = {"csv": fawn_csv, "xlsx": fawn_xlsx, "rows": int(len(fawn_df))}

    report_path = out_dir / "strict_reextract_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
