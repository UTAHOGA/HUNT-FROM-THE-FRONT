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
    / "2024"
    / "csv"
    / "Harvest Results"
    / "harvest_results_2023_hunt_code_keyed_all_sources.csv"
)
AGE_LATEST = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2024"
    / "big_game_2023_for_2024_harvest_age_database_package"
    / "average_harvest_age_2023_for_2024_latest_only.csv"
)
AGE_ALL = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2024"
    / "big_game_2023_for_2024_harvest_age_database_package"
    / "average_harvest_age_2023_for_2024_all_available.csv"
)

OUT_DIR = ROOT / "data_model" / "harvest_quality"
OUT_EXPANDED = OUT_DIR / "harvest_results_2023_for_2024_age_rows_expanded.csv"
OUT_COMPLETE = OUT_DIR / "harvest_results_2023_for_2024_complete_database.csv"
OUT_SUMMARY = OUT_DIR / "harvest_results_2023_for_2024_complete_database_summary.json"


def norm(text: str) -> str:
    value = (text or "").lower()
    value = value.replace("&", " and ").replace("/", " ")
    value = value.replace("*", " ")
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


def parse_age(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    # Guardrail against obvious parsing leaks like 2006.0 in age columns.
    if number <= 0 or number >= 30:
        return ""
    return f"{number:.2f}".rstrip("0").rstrip(".")


def build_base_index(base_df: pd.DataFrame) -> tuple[dict[tuple[str, str], set[str]], set[str]]:
    by_species_unit: dict[tuple[str, str], set[str]] = defaultdict(set)
    valid_codes: set[str] = set()
    for _, r in base_df.iterrows():
        code = str(r.get("hunt_code", "")).strip().upper()
        if not code:
            continue
        valid_codes.add(code)
        sp = species_norm(str(r.get("species", "")))
        hname = str(r.get("hunt_name", ""))
        for uv in unit_key_variants(hname):
            by_species_unit[(sp, uv)].add(code)
    return by_species_unit, valid_codes


def load_age_rows() -> pd.DataFrame:
    latest = pd.read_csv(AGE_LATEST, dtype=str, low_memory=False).fillna("")
    all_rows = pd.read_csv(AGE_ALL, dtype=str, low_memory=False).fillna("")
    rows = []

    # Prefer latest-only for canonical ingest; keep all-available for fallback when latest misses a unit.
    for source_label, df in [("latest_only", latest), ("all_available", all_rows)]:
        for _, r in df.iterrows():
            reported_year = str(r.get("reported_hunt_year", "")).strip()
            if reported_year != "2023":
                continue
            age = parse_age(r.get("average_harvest_age", ""))
            if not age:
                continue
            rows.append(
                {
                    "source_lane": source_label,
                    "source_file": r.get("source_file", ""),
                    "source_page": r.get("source_page", ""),
                    "source_table_title": r.get("source_table_title", ""),
                    "reported_hunt_year": reported_year,
                    "model_target_year": str(r.get("model_target_year", "")).strip() or "2024",
                    "species": r.get("species", ""),
                    "species_norm": species_norm(r.get("species", "")),
                    "hunt_code": str(r.get("hunt_code", "")).strip().upper(),
                    "hunt_code_scope": str(r.get("hunt_code_scope", "")).strip(),
                    "unit_name": r.get("unit_name", ""),
                    "average_harvest_age": age,
                    "average_harvest_age_3yr": parse_age(r.get("average_harvest_age_3yr", "")),
                    "percent_mature_or_5_plus": str(r.get("percent_mature_or_5_plus", "")).strip(),
                    "percent_mature_or_5_plus_3yr": str(r.get("percent_mature_or_5_plus_3yr", "")).strip(),
                    "age_match_confidence": str(r.get("hunt_code_match_confidence", "")).strip(),
                    "notes": str(r.get("notes", "")).strip(),
                }
            )

    df = pd.DataFrame(rows).fillna("")
    # Keep latest rows first when duplicate content appears.
    if not df.empty:
        lane_rank = {"latest_only": 0, "all_available": 1}
        df["lane_rank"] = df["source_lane"].map(lane_rank).fillna(9)
        df = df.sort_values(["lane_rank", "species", "unit_name", "hunt_code", "average_harvest_age"]).reset_index(drop=True)
    return df


def expand_age_rows(age_df: pd.DataFrame, by_species_unit: dict[tuple[str, str], set[str]], valid_codes: set[str]) -> pd.DataFrame:
    expanded: list[dict[str, str]] = []
    seen = set()
    for _, r in age_df.iterrows():
        direct_code = str(r.get("hunt_code", "")).strip().upper()
        scope_codes = [c.strip().upper() for c in str(r.get("hunt_code_scope", "")).split(";") if c.strip()]
        scope_codes = [c for c in scope_codes if c in valid_codes]
        sp = str(r.get("species_norm", "")).strip()
        unit_name = str(r.get("unit_name", "")).strip()

        candidates: list[str] = []
        status = ""
        if direct_code and direct_code in valid_codes:
            candidates = [direct_code]
            status = "mapped_direct_hunt_code"
        elif scope_codes:
            candidates = sorted(set(scope_codes))
            status = "mapped_hunt_code_scope"
        else:
            unit_candidates: set[str] = set()
            for uv in unit_key_variants(unit_name):
                unit_candidates |= by_species_unit.get((sp, uv), set())
            candidates = sorted(unit_candidates)
            if candidates:
                status = "mapped_unit_level_repeated_to_hunt_codes" if len(candidates) > 1 else "mapped_unit_level_unique"
            else:
                status = "no_hunt_code_match_found"

        if not candidates:
            out = dict(r)
            out["candidate_hunt_code"] = ""
            out["hunt_code_candidate_count"] = "0"
            out["hunt_code_mapping_status"] = status
            out["expanded_candidate_index"] = ""
            dedupe = (
                out.get("source_lane", ""),
                out.get("species", ""),
                out.get("unit_name", ""),
                out.get("average_harvest_age", ""),
                out["hunt_code_mapping_status"],
            )
            if dedupe not in seen:
                seen.add(dedupe)
                expanded.append(out)
            continue

        for idx, code in enumerate(candidates, start=1):
            out = dict(r)
            out["hunt_code"] = code
            out["candidate_hunt_code"] = ";".join(candidates)
            out["hunt_code_candidate_count"] = str(len(candidates))
            out["hunt_code_mapping_status"] = status
            out["expanded_candidate_index"] = f"{idx}/{len(candidates)}"
            dedupe = (
                out.get("source_lane", ""),
                code,
                out.get("species", ""),
                out.get("unit_name", ""),
                out.get("average_harvest_age", ""),
                out["hunt_code_mapping_status"],
            )
            if dedupe in seen:
                continue
            seen.add(dedupe)
            expanded.append(out)

    return pd.DataFrame(expanded).fillna("")


def build_complete(base_df: pd.DataFrame, expanded_df: pd.DataFrame) -> pd.DataFrame:
    out = base_df.copy()
    out["average_harvest_age_2023"] = ""
    out["average_harvest_age_3yr_2023"] = ""
    out["percent_mature_or_5_plus_2023"] = ""
    out["percent_mature_or_5_plus_3yr_2023"] = ""
    out["age_data_available_2023"] = "false"
    out["age_source_package_2023"] = ""
    out["age_mapping_status_2023"] = ""
    out["age_match_confidence_2023"] = ""
    out["age_candidate_count_2023"] = ""

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

        # Prefer latest_only lane values; if multiple unique ages remain, keep blank for manual resolution.
        latest_hits = [h for h in hits if h.get("source_lane") == "latest_only"]
        effective_hits = latest_hits if latest_hits else hits

        age_vals = sorted({str(h.get("average_harvest_age", "")).strip() for h in effective_hits if str(h.get("average_harvest_age", "")).strip()})
        age3_vals = sorted({str(h.get("average_harvest_age_3yr", "")).strip() for h in effective_hits if str(h.get("average_harvest_age_3yr", "")).strip()})
        p5_vals = sorted({str(h.get("percent_mature_or_5_plus", "")).strip() for h in effective_hits if str(h.get("percent_mature_or_5_plus", "")).strip()})
        p53_vals = sorted(
            {str(h.get("percent_mature_or_5_plus_3yr", "")).strip() for h in effective_hits if str(h.get("percent_mature_or_5_plus_3yr", "")).strip()}
        )
        statuses = sorted({str(h.get("hunt_code_mapping_status", "")).strip() for h in effective_hits if str(h.get("hunt_code_mapping_status", "")).strip()})
        confs = sorted({str(h.get("age_match_confidence", "")).strip() for h in effective_hits if str(h.get("age_match_confidence", "")).strip()})
        cand_counts = sorted({str(h.get("hunt_code_candidate_count", "")).strip() for h in effective_hits if str(h.get("hunt_code_candidate_count", "")).strip()})

        out.at[i, "average_harvest_age_2023"] = age_vals[0] if len(age_vals) == 1 else ""
        out.at[i, "average_harvest_age_3yr_2023"] = age3_vals[0] if len(age3_vals) == 1 else ""
        out.at[i, "percent_mature_or_5_plus_2023"] = p5_vals[0] if len(p5_vals) == 1 else ""
        out.at[i, "percent_mature_or_5_plus_3yr_2023"] = p53_vals[0] if len(p53_vals) == 1 else ""
        out.at[i, "age_data_available_2023"] = "true" if len(age_vals) == 1 else "false"
        out.at[i, "age_source_package_2023"] = "big_game_2023_for_2024_harvest_age_database_package"
        out.at[i, "age_mapping_status_2023"] = ";".join(statuses)
        out.at[i, "age_match_confidence_2023"] = ";".join(confs)
        out.at[i, "age_candidate_count_2023"] = ";".join(cand_counts)

    return out


def main() -> None:
    for p in [BASE_PATH, AGE_LATEST, AGE_ALL]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required source: {p}")

    base = pd.read_csv(BASE_PATH, dtype=str, low_memory=False).fillna("")
    base_2023 = base[base["reported_hunt_year"].astype(str).str.strip() == "2023"].copy()
    age_raw = load_age_rows()
    by_species_unit, valid_codes = build_base_index(base_2023)
    age_expanded = expand_age_rows(age_raw, by_species_unit, valid_codes)
    complete = build_complete(base_2023, age_expanded)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    age_expanded.to_csv(OUT_EXPANDED, index=False, encoding="utf-8-sig")
    complete.to_csv(OUT_COMPLETE, index=False, encoding="utf-8-sig")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_file": str(BASE_PATH).replace("\\", "/"),
        "base_rows_2023": int(len(base_2023)),
        "age_rows_raw_2023": int(len(age_raw)),
        "age_rows_raw_by_species": age_raw["species"].value_counts().to_dict() if not age_raw.empty else {},
        "age_rows_expanded": int(len(age_expanded)),
        "age_mapping_status_counts": age_expanded["hunt_code_mapping_status"].value_counts().to_dict() if not age_expanded.empty else {},
        "complete_rows": int(len(complete)),
        "complete_rows_with_age": int((complete["average_harvest_age_2023"].astype(str).str.strip() != "").sum()),
        "complete_rows_with_age_by_species": complete[
            complete["average_harvest_age_2023"].astype(str).str.strip() != ""
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
