from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


MASTER_CSV = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/batch_2024_subfiles_vs_master/draw_odds_master_hunt_rows_2024.csv"
)
ANTLERLESS_CSV = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/antlerless_draw_odds_2024_extract/ANTLERLESS_DRAW_ODDS_2024_PERMIT_TOTALS.csv"
)
SUBFILES_CSV = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/batch_2024_subfiles_vs_master/draw_odds_subfiles_hunt_rows_2024.csv"
)
OUT_DIR = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/comprehensive_2024"
)


def normalize_master(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["source_file"] = df["source_file"].astype(str)
    out["source_page"] = pd.to_numeric(df["source_page"], errors="coerce")
    out["hunt_code"] = df["hunt_code"].astype(str).str.upper().str.strip()
    out["hunt_name"] = df["hunt_name"].astype(str).str.strip()
    out["species_or_category"] = ""
    out["res_total_permits"] = pd.to_numeric(df["res_total_permits"], errors="coerce")
    out["nr_total_permits"] = pd.to_numeric(df["nr_total_permits"], errors="coerce")
    out["total_permits"] = pd.to_numeric(df["total_permits"], errors="coerce")
    out["totals_numbers"] = df["totals_numbers"].astype(str)
    out["raw_hunt_line"] = ""
    out["raw_totals_line"] = df["totals_line"].astype(str)
    out["parse_style"] = df["parse_style"].astype(str)
    out["dataset_family"] = "big_game_master"
    out["source_dataset"] = "24_bg-odds.pdf"
    return out


def normalize_antlerless(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["source_file"] = df["source_file"].astype(str)
    out["source_page"] = pd.to_numeric(df["source_page"], errors="coerce")
    out["hunt_code"] = df["hunt_code"].astype(str).str.upper().str.strip()
    out["hunt_name"] = df["hunt_name"].astype(str).str.strip()
    out["species_or_category"] = df["species_category"].astype(str).str.strip()
    out["res_total_permits"] = pd.to_numeric(df["res_total_permits"], errors="coerce")
    out["nr_total_permits"] = pd.to_numeric(df["nr_total_permits"], errors="coerce")
    out["total_permits"] = pd.to_numeric(df["permits_total_draw_results"], errors="coerce")
    out["totals_numbers"] = ""
    out["raw_hunt_line"] = df["raw_hunt_line"].astype(str)
    out["raw_totals_line"] = df["raw_totals_line"].astype(str)
    out["parse_style"] = "res_nr_split"
    out["dataset_family"] = "antlerless_draw_results"
    out["source_dataset"] = "2024 antlerless draw results.pdf"
    return out


def normalize_bear_from_subfiles(df: pd.DataFrame) -> pd.DataFrame:
    src = df[df["source_file"].astype(str).str.contains("Bear Draw Results.pdf", case=False, na=False)].copy()
    src = src[src["hunt_code"].astype(str).str.match(r"^BR\d{4}$", na=False)].copy()
    out = pd.DataFrame()
    out["source_file"] = src["source_file"].astype(str)
    out["source_page"] = pd.to_numeric(src["source_page"], errors="coerce")
    out["hunt_code"] = src["hunt_code"].astype(str).str.upper().str.strip()
    out["hunt_name"] = src["hunt_name"].astype(str).str.strip()
    out["species_or_category"] = "Black Bear"
    out["res_total_permits"] = pd.to_numeric(src["res_total_permits"], errors="coerce")
    out["nr_total_permits"] = pd.to_numeric(src["nr_total_permits"], errors="coerce")
    out["total_permits"] = pd.to_numeric(src["total_permits"], errors="coerce")
    out["totals_numbers"] = src["totals_numbers"].astype(str)
    out["raw_hunt_line"] = ""
    out["raw_totals_line"] = src["totals_line"].astype(str)
    out["parse_style"] = src["parse_style"].astype(str)
    out["dataset_family"] = "bear_draw_results"
    out["source_dataset"] = "2024 Bear Draw Results.pdf"
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not MASTER_CSV.exists():
        raise FileNotFoundError(f"Missing master CSV: {MASTER_CSV}")
    if not ANTLERLESS_CSV.exists():
        raise FileNotFoundError(f"Missing antlerless CSV: {ANTLERLESS_CSV}")
    if not SUBFILES_CSV.exists():
        raise FileNotFoundError(f"Missing subfiles CSV: {SUBFILES_CSV}")

    m = pd.read_csv(MASTER_CSV, dtype=str).fillna("")
    a = pd.read_csv(ANTLERLESS_CSV, dtype=str).fillna("")
    s = pd.read_csv(SUBFILES_CSV, dtype=str).fillna("")

    m2 = normalize_master(m)
    a2 = normalize_antlerless(a)
    b2 = normalize_bear_from_subfiles(s)

    # Keep only well-formed hunt codes.
    code_re = re.compile(r"^[A-Z]{2}\d{4}$")
    m2 = m2[m2["hunt_code"].map(lambda v: bool(code_re.match(str(v))))].copy()
    a2 = a2[a2["hunt_code"].map(lambda v: bool(code_re.match(str(v))))].copy()
    b2 = b2[b2["hunt_code"].map(lambda v: bool(code_re.match(str(v))))].copy()

    # De-duplicate antlerless rows that may already be in master by hunt_code.
    # Keep antlerless rows as supplemental only when code is not in big game master.
    master_codes = set(m2["hunt_code"].astype(str))
    a2_new = a2[~a2["hunt_code"].astype(str).isin(master_codes)].copy()
    a2_codes = set(a2_new["hunt_code"].astype(str))
    b2_new = b2[
        ~b2["hunt_code"].astype(str).isin(master_codes)
        & ~b2["hunt_code"].astype(str).isin(a2_codes)
    ].copy()

    combined = pd.concat([m2, a2_new, b2_new], ignore_index=True)
    combined = combined.sort_values(["hunt_code", "dataset_family", "source_page"]).reset_index(drop=True)

    out_csv = OUT_DIR / "2024_DRAW_RESULTS_COMPREHENSIVE.csv"
    out_xlsx = OUT_DIR / "2024_DRAW_RESULTS_COMPREHENSIVE.xlsx"
    out_report = OUT_DIR / "2024_DRAW_RESULTS_COMPREHENSIVE_report.json"

    combined.to_csv(out_csv, index=False, encoding="utf-8-sig")
    combined.to_excel(out_xlsx, index=False)

    report = {
        "master_source": str(MASTER_CSV).replace("\\", "/"),
        "antlerless_source": str(ANTLERLESS_CSV).replace("\\", "/"),
        "master_rows": int(len(m2)),
        "master_unique_hunt_codes": int(m2["hunt_code"].nunique()),
        "antlerless_rows": int(len(a2)),
        "antlerless_unique_hunt_codes": int(a2["hunt_code"].nunique()),
        "antlerless_rows_appended": int(len(a2_new)),
        "antlerless_unique_hunt_codes_appended": int(a2_new["hunt_code"].nunique()),
        "bear_rows": int(len(b2)),
        "bear_unique_hunt_codes": int(b2["hunt_code"].nunique()),
        "bear_rows_appended": int(len(b2_new)),
        "bear_unique_hunt_codes_appended": int(b2_new["hunt_code"].nunique()),
        "combined_rows": int(len(combined)),
        "combined_unique_hunt_codes": int(combined["hunt_code"].nunique()),
        "prefix_counts": combined["hunt_code"].str[:2].value_counts().to_dict(),
        "output_csv": str(out_csv).replace("\\", "/"),
        "output_xlsx": str(out_xlsx).replace("\\", "/"),
    }
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {out_csv}")
    print(f"Wrote {out_xlsx}")
    print(f"Wrote {out_report}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
