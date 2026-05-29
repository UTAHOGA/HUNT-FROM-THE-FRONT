from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2023"
    / "harvest_results_2022_for_2023_database"
    / "harvest_results_2022_for_2023_all_long.csv"
)

AGE_BIG_GAME_LATEST = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2023"
    / "big_game_2022_for_2023_harvest_age_database_package"
    / "average_harvest_age_2022_for_2023_latest_only.csv"
)
AGE_BLACK_BEAR_FIXED_HC = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2023"
    / "black_bear_2022_for_2023_age_fixed_package"
    / "black_bear_2022_for_2023_hunt_code_rows.csv"
)
AGE_BLACK_BEAR_FIXED_CURRENT = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2023"
    / "black_bear_2022_for_2023_age_fixed_package"
    / "black_bear_2022_for_2023_current_harvest_rows.csv"
)

OUT_DIR = ROOT / "data_model" / "harvest_quality"
OUT_EXPANDED = OUT_DIR / "harvest_results_2022_for_2023_age_rows_expanded.csv"
OUT_COMPLETE = OUT_DIR / "harvest_results_2022_for_2023_complete_database.csv"
OUT_SUMMARY = OUT_DIR / "harvest_results_2022_for_2023_complete_database_summary.json"


def norm(text: str) -> str:
    value = (text or "").lower()
    value = value.replace("&", " and ").replace("/", " ")
    value = value.replace("mtns", "mountains").replace("mtn", "mountain")
    value = value.replace("o.i.l.", "oil")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def species_norm(text: str) -> str:
    t = norm(text)
    if "deer" in t:
        return "mule deer"
    if "elk" in t:
        return "elk"
    if "pronghorn" in t:
        return "pronghorn"
    if "moose" in t:
        return "moose"
    if "mountain goat" in t or "goat" in t:
        return "mountain goat"
    if "black bear" in t or "bear" in t:
        return "black bear"
    return t


def unit_key_variants(text: str) -> list[str]:
    raw = norm(text)
    if not raw:
        return []
    variants = {raw}
    variants.add(raw.replace(" south slope ", " "))
    variants.add(raw.replace(" north slope ", " "))
    parts = [p.strip() for p in re.split(r",| and ", text) if p.strip()]
    for p in parts:
        variants.add(norm(p))
    return sorted(v for v in variants if v)


def build_base_index(base_df: pd.DataFrame) -> tuple[dict[tuple[str, str], set[str]], dict[str, str]]:
    by_species_unit: dict[tuple[str, str], set[str]] = defaultdict(set)
    by_code_name: dict[str, str] = {}
    for _, r in base_df.iterrows():
        code = str(r.get("hunt_code", "")).strip().upper()
        if not code:
            continue
        sp = species_norm(str(r.get("species", "")))
        hname = str(r.get("hunt_name", ""))
        by_code_name[code] = hname
        for uv in unit_key_variants(hname):
            by_species_unit[(sp, uv)].add(code)
    return by_species_unit, by_code_name


def load_age_rows() -> pd.DataFrame:
    big = pd.read_csv(AGE_BIG_GAME_LATEST, dtype=str, low_memory=False).fillna("")
    big_rows = []
    for _, r in big.iterrows():
        big_rows.append(
            {
                "source_package": "big_game_2022_for_2023_harvest_age_database_package",
                "source_file": r.get("source_file", ""),
                "source_page": r.get("source_page", ""),
                "source_table_title": r.get("source_table_title", ""),
                "reported_hunt_year": r.get("reported_hunt_year", ""),
                "model_target_year": r.get("model_target_year", ""),
                "species": r.get("species", ""),
                "species_norm": species_norm(r.get("species", "")),
                "hunt_code": str(r.get("hunt_code", "")).strip().upper(),
                "unit_name": r.get("unit_name", ""),
                "average_harvest_age": r.get("average_harvest_age", ""),
                "average_harvest_age_3yr": r.get("average_harvest_age_3yr", ""),
                "percent_mature_or_5_plus": r.get("percent_mature_or_5_plus", ""),
                "percent_mature_or_5_plus_3yr": r.get("percent_mature_or_5_plus_3yr", ""),
                "age_match_scope": r.get("age_match_scope", ""),
                "age_match_confidence": r.get("hunt_code_match_confidence", ""),
                "notes": r.get("notes", ""),
            }
        )

    bb_hc = pd.read_csv(AGE_BLACK_BEAR_FIXED_HC, dtype=str, low_memory=False).fillna("")
    bb_hc_rows = []
    for _, r in bb_hc.iterrows():
        bb_hc_rows.append(
            {
                "source_package": "black_bear_2022_for_2023_age_fixed_package_hunt_code_rows",
                "source_file": r.get("source_file", ""),
                "source_page": r.get("source_page", ""),
                "source_table_title": r.get("source_table_title", ""),
                "reported_hunt_year": r.get("reported_hunt_year", ""),
                "model_target_year": r.get("model_target_year", ""),
                "species": r.get("species", ""),
                "species_norm": species_norm(r.get("species", "")),
                "hunt_code": str(r.get("hunt_code", "")).strip().upper(),
                "unit_name": r.get("unit_subunit", ""),
                "average_harvest_age": r.get("average_harvest_age", ""),
                "average_harvest_age_3yr": "",
                "percent_mature_or_5_plus": "",
                "percent_mature_or_5_plus_3yr": "",
                "age_match_scope": r.get("age_match_scope", ""),
                "age_match_confidence": r.get("age_match_confidence", ""),
                "notes": r.get("match_status", ""),
            }
        )

    bb_current = pd.read_csv(AGE_BLACK_BEAR_FIXED_CURRENT, dtype=str, low_memory=False).fillna("")
    bb_current_rows = []
    for _, r in bb_current.iterrows():
        if str(r.get("hunt_code", "")).strip():
            continue
        age_val = str(r.get("average_harvest_age", "")).strip()
        if not age_val:
            continue
        bb_current_rows.append(
            {
                "source_package": "black_bear_2022_for_2023_age_fixed_package_current_rows_unit_level",
                "source_file": r.get("source_file", ""),
                "source_page": r.get("source_page", ""),
                "source_table_title": r.get("source_table_title", ""),
                "reported_hunt_year": r.get("reported_hunt_year", ""),
                "model_target_year": r.get("model_target_year", ""),
                "species": r.get("species", ""),
                "species_norm": species_norm(r.get("species", "")),
                "hunt_code": "",
                "unit_name": r.get("unit_subunit", ""),
                "average_harvest_age": age_val,
                "average_harvest_age_3yr": "",
                "percent_mature_or_5_plus": "",
                "percent_mature_or_5_plus_3yr": "",
                "age_match_scope": r.get("age_match_scope", ""),
                "age_match_confidence": r.get("age_match_confidence", ""),
                "notes": r.get("match_status", ""),
            }
        )

    all_rows = big_rows + bb_hc_rows + bb_current_rows
    df = pd.DataFrame(all_rows).fillna("")
    # keep only 2022 rows
    df = df[df["reported_hunt_year"].astype(str).str.strip() == "2022"].copy()
    return df


def expand_age_rows(age_df: pd.DataFrame, by_species_unit: dict[tuple[str, str], set[str]]) -> pd.DataFrame:
    expanded: list[dict[str, str]] = []
    for _, r in age_df.iterrows():
        direct_code = str(r.get("hunt_code", "")).strip().upper()
        if direct_code:
            out = dict(r)
            out["candidate_hunt_code"] = direct_code
            out["hunt_code_candidate_count"] = "1"
            out["hunt_code_mapping_status"] = "mapped_direct_hunt_code"
            out["expanded_candidate_index"] = "1/1"
            expanded.append(out)
            continue

        sp = str(r.get("species_norm", "")).strip()
        unit_name = str(r.get("unit_name", "")).strip()
        candidates: set[str] = set()
        for uv in unit_key_variants(unit_name):
            candidates |= by_species_unit.get((sp, uv), set())

        cand_list = sorted(candidates)
        if not cand_list:
            out = dict(r)
            out["candidate_hunt_code"] = ""
            out["hunt_code_candidate_count"] = "0"
            out["hunt_code_mapping_status"] = "no_hunt_code_match_found"
            out["expanded_candidate_index"] = ""
            expanded.append(out)
            continue

        status = "mapped_unit_level_repeated_to_hunt_codes" if len(cand_list) > 1 else "mapped_unit_level_unique"
        for idx, c in enumerate(cand_list, start=1):
            out = dict(r)
            out["hunt_code"] = c
            out["candidate_hunt_code"] = ";".join(cand_list)
            out["hunt_code_candidate_count"] = str(len(cand_list))
            out["hunt_code_mapping_status"] = status
            out["expanded_candidate_index"] = f"{idx}/{len(cand_list)}"
            expanded.append(out)

    return pd.DataFrame(expanded).fillna("")


def build_complete(base_df: pd.DataFrame, expanded_df: pd.DataFrame) -> pd.DataFrame:
    out = base_df.copy()
    out["average_harvest_age_2022"] = ""
    out["average_harvest_age_3yr_2022"] = ""
    out["percent_mature_or_5_plus_2022"] = ""
    out["percent_mature_or_5_plus_3yr_2022"] = ""
    out["age_data_available_2022"] = "false"
    out["age_source_package_2022"] = ""
    out["age_mapping_status_2022"] = ""
    out["age_match_confidence_2022"] = ""
    out["age_candidate_count_2022"] = ""

    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for _, r in expanded_df.iterrows():
        code = str(r.get("hunt_code", "")).strip().upper()
        if not code:
            continue
        by_code[code].append(r.to_dict())

    for i, row in out.iterrows():
        code = str(row.get("hunt_code", "")).strip().upper()
        if not code:
            continue
        hits = by_code.get(code, [])
        if not hits:
            continue

        age_vals = sorted({str(h.get("average_harvest_age", "")).strip() for h in hits if str(h.get("average_harvest_age", "")).strip()})
        age3_vals = sorted({str(h.get("average_harvest_age_3yr", "")).strip() for h in hits if str(h.get("average_harvest_age_3yr", "")).strip()})
        p5_vals = sorted({str(h.get("percent_mature_or_5_plus", "")).strip() for h in hits if str(h.get("percent_mature_or_5_plus", "")).strip()})
        p53_vals = sorted(
            {str(h.get("percent_mature_or_5_plus_3yr", "")).strip() for h in hits if str(h.get("percent_mature_or_5_plus_3yr", "")).strip()}
        )
        pkgs = sorted({str(h.get("source_package", "")).strip() for h in hits if str(h.get("source_package", "")).strip()})
        statuses = sorted({str(h.get("hunt_code_mapping_status", "")).strip() for h in hits if str(h.get("hunt_code_mapping_status", "")).strip()})
        confs = sorted({str(h.get("age_match_confidence", "")).strip() for h in hits if str(h.get("age_match_confidence", "")).strip()})
        cand_counts = sorted({str(h.get("hunt_code_candidate_count", "")).strip() for h in hits if str(h.get("hunt_code_candidate_count", "")).strip()})

        out.at[i, "average_harvest_age_2022"] = age_vals[0] if len(age_vals) == 1 else ""
        out.at[i, "average_harvest_age_3yr_2022"] = age3_vals[0] if len(age3_vals) == 1 else ""
        out.at[i, "percent_mature_or_5_plus_2022"] = p5_vals[0] if len(p5_vals) == 1 else ""
        out.at[i, "percent_mature_or_5_plus_3yr_2022"] = p53_vals[0] if len(p53_vals) == 1 else ""
        out.at[i, "age_data_available_2022"] = "true" if age_vals else "false"
        out.at[i, "age_source_package_2022"] = ";".join(pkgs)
        out.at[i, "age_mapping_status_2022"] = ";".join(statuses)
        out.at[i, "age_match_confidence_2022"] = ";".join(confs)
        out.at[i, "age_candidate_count_2022"] = ";".join(cand_counts)

    return out


def main() -> None:
    if not BASE_PATH.exists():
        raise FileNotFoundError(f"Missing base file: {BASE_PATH}")
    for p in [AGE_BIG_GAME_LATEST, AGE_BLACK_BEAR_FIXED_HC, AGE_BLACK_BEAR_FIXED_CURRENT]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required source: {p}")

    base = pd.read_csv(BASE_PATH, dtype=str, low_memory=False).fillna("")
    base_2022 = base[base["reported_hunt_year"].astype(str).str.strip() == "2022"].copy()
    age_raw = load_age_rows()
    by_species_unit, _ = build_base_index(base_2022)
    age_expanded = expand_age_rows(age_raw, by_species_unit)
    complete = build_complete(base_2022, age_expanded)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    age_expanded.to_csv(OUT_EXPANDED, index=False, encoding="utf-8-sig")
    complete.to_csv(OUT_COMPLETE, index=False, encoding="utf-8-sig")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_file": str(BASE_PATH).replace("\\", "/"),
        "base_rows_2022": int(len(base_2022)),
        "age_rows_raw_2022": int(len(age_raw)),
        "age_rows_raw_by_species": age_raw["species"].value_counts().to_dict(),
        "age_rows_expanded": int(len(age_expanded)),
        "age_mapping_status_counts": age_expanded["hunt_code_mapping_status"].value_counts().to_dict(),
        "complete_rows": int(len(complete)),
        "complete_rows_with_age": int((complete["average_harvest_age_2022"].astype(str).str.strip() != "").sum()),
        "complete_rows_with_age_by_species": complete[
            complete["average_harvest_age_2022"].astype(str).str.strip() != ""
        ]["species"].value_counts().to_dict(),
        "outputs": {
            "age_rows_expanded": str(OUT_EXPANDED).replace("\\", "/"),
            "complete_database": str(OUT_COMPLETE).replace("\\", "/"),
        },
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
