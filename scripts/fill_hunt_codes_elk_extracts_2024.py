from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


BASE = Path(r"pipeline/RAW/hunt_unit_database/2025/formatted_tables")
DB_PATH = Path(r"pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv")


def norm(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("&", " and ").replace("/", " ")
    s = s.replace("mtns", "mountains").replace("mtn", "mountain")
    s = s.replace("mt ", "mount ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


UNIT_ALIAS: dict[str, list[str]] = {
    "beaver": ["beaver"],
    "book cliffs": ["book cliffs"],
    "book cliffs south": ["book cliffs"],
    "book cliffs bitter creek little creek": ["book cliffs", "bitter creek"],
    "boulder kaiparowits": ["boulder", "kaiparowits"],
    "box elder": ["box elder"],
    "box elder west": ["box elder"],
    "cache": ["cache"],
    "chalk creek": ["chalk creek"],
    "diamond mtn": ["diamond mountain", "diamond mtn"],
    "diamond mtn vernal bonanza": ["diamond mountain", "vernal", "bonanza"],
    "east canyon": ["east canyon"],
    "fillmore": ["fillmore"],
    "fillmore pahvant": ["fillmore", "pahvant"],
    "fishlake thousand lakes": ["fishlake", "thousand lakes"],
    "henry mtns": ["henry mountains", "henry mtns"],
    "kamas": ["kamas"],
    "la sal dolores triangle": ["la sal dolores triangle"],
    "la sal la sal mtns": ["la sal la sal mountains", "la sal la sal mtns"],
    "manti": ["manti"],
    "monroe": ["monroe"],
    "morgan south rich": ["morgan south rich"],
    "mt dutton": ["mount dutton", "mt dutton"],
    "nebo": ["nebo"],
    "nine mile anthro": ["nine mile west anthro", "nine mile anthro"],
    "nine mile range creek": ["nine mile range creek"],
    "north slope summit": ["north slope summit"],
    "north slope three corners": ["north slope three corners"],
    "north slope west daggett": ["north slope west daggett"],
    "ogden": ["ogden"],
    "oquirrh stansbury": ["oquirrh stansbury"],
    "panguitch lake": ["panguitch lake"],
    "paunsaugunt": ["paunsaugunt"],
    "pine valley": ["pine valley"],
    "san juan": ["san juan"],
    "san rafael": ["san rafael"],
    "southwest desert": ["southwest desert"],
    "vernal bonanza": ["vernal bonanza", "bonanza vernal"],
    "wasatch mtns": ["wasatch mountains", "wasatch mtns"],
    "west desert": ["west desert"],
    "yellowstone": ["yellowstone"],
    "zion": ["zion"],
}


def load_db() -> list[dict[str, str]]:
    with DB_PATH.open(newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        return list(rd)


def split_codes(value: str) -> list[str]:
    if not value:
        return []
    return sorted(set(re.findall(r"[A-Za-z]{2}\d{4}", str(value).upper())))


def filter_candidates(rows: list[dict[str, str]], cfg: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in rows:
        if (r.get("species") or "").strip().lower() != "elk":
            continue

        hunt_type = (r.get("hunt_type") or "").strip().lower()
        hunt_name = (r.get("hunt_name") or "").strip().lower()
        weapon = (r.get("weapon") or "").strip().lower()
        sex = (r.get("sex_type") or "").strip().lower()

        if cfg.get("exclude_cwmu_conservation_expo", False):
            if "cwmu" in hunt_type or "conservation" in hunt_type or "expo" in hunt_type or "expo" in hunt_name:
                continue

        include_sex = cfg.get("include_sex")
        if include_sex and sex not in include_sex:
            continue

        include_hunt_type_contains = cfg.get("include_hunt_type_contains")
        if include_hunt_type_contains and not any(term in hunt_type for term in include_hunt_type_contains):
            continue

        include_weapon_contains = cfg.get("include_weapon_contains")
        if include_weapon_contains and not any(term in weapon for term in include_weapon_contains):
            continue

        out.append(
            {
                "hunt_code": (r.get("hunt_code") or "").strip(),
                "hunt_name": (r.get("hunt_name") or "").strip(),
                "norm_hunt_name": norm(r.get("hunt_name") or ""),
                "hunt_type": (r.get("hunt_type") or "").strip(),
                "weapon": (r.get("weapon") or "").strip(),
                "sex_type": (r.get("sex_type") or "").strip(),
            }
        )
    return out


def match_by_unit(unit_name: str, candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    n = norm(unit_name)
    keys = UNIT_ALIAS.get(n, [n])
    matched: list[dict[str, str]] = []
    for c in candidates:
        nh = c["norm_hunt_name"]
        if any(k and k in nh for k in keys):
            matched.append(c)
    # de-dupe by hunt_code
    uniq: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in sorted(matched, key=lambda x: x["hunt_code"]):
        if m["hunt_code"] in seen:
            continue
        seen.add(m["hunt_code"])
        uniq.append(m)
    return uniq


def apply_direct_hunt_number(path: Path, db_by_code: dict[str, dict[str, str]]) -> dict[str, Any]:
    df = pd.read_csv(path, dtype=str).fillna("")
    rows = df.to_dict(orient="records")
    match_rows = 0
    for r in rows:
        code = (r.get("Hunt number") or "").strip().upper()
        hit = db_by_code.get(code)
        if hit:
            r["hunt_codes_2026_elk"] = code
            r["hunt_code_count_2026"] = "1"
            r["matched_hunt_names_2026"] = hit.get("hunt_name", "")
            r["match_basis"] = "direct_hunt_number_match"
            r["mapping_status"] = "mapped_to_2026_codes"
            match_rows += 1
        else:
            r["hunt_codes_2026_elk"] = ""
            r["hunt_code_count_2026"] = "0"
            r["matched_hunt_names_2026"] = ""
            r["match_basis"] = "direct_hunt_number_match"
            r["mapping_status"] = "historical_only"
    out = pd.DataFrame(rows)
    out.to_csv(path, index=False, encoding="utf-8-sig")
    out.to_excel(path.with_suffix(".xlsx"), index=False)
    return {"rows": len(rows), "rows_matched": match_rows, "rows_zero": len(rows) - match_rows}


def apply_code_column(path: Path, db_by_code: dict[str, dict[str, str]], code_col: str, basis: str) -> dict[str, Any]:
    df = pd.read_csv(path, dtype=str).fillna("")
    rows = df.to_dict(orient="records")
    match_rows = 0
    for r in rows:
        codes = split_codes(r.get(code_col, ""))
        matched = [c for c in codes if c in db_by_code]
        matched_names = [db_by_code[c].get("hunt_name", "") for c in matched]
        r["hunt_codes_2026_elk"] = ";".join(matched)
        r["hunt_code_count_2026"] = str(len(matched))
        r["matched_hunt_names_2026"] = " | ".join(n for n in matched_names if n)
        r["match_basis"] = basis
        r["mapping_status"] = "mapped_to_2026_codes" if matched else "historical_only"
        if matched:
            match_rows += 1
    out = pd.DataFrame(rows)
    out.to_csv(path, index=False, encoding="utf-8-sig")
    out.to_excel(path.with_suffix(".xlsx"), index=False)
    return {"rows": len(rows), "rows_matched": match_rows, "rows_zero": len(rows) - match_rows}


def apply_unit_match(
    path: Path,
    candidates: list[dict[str, str]],
    cfg_name: str,
    fallback_candidates: list[dict[str, str]] | None = None,
    fallback_name: str | None = None,
) -> dict[str, Any]:
    df = pd.read_csv(path, dtype=str).fillna("")
    rows = df.to_dict(orient="records")
    match_rows = 0
    unit_col = "Unit name"
    if unit_col not in rows[0]:
        # for winter trend this is still Unit name; keep fallback minimal
        unit_col = "Unit name"
    for r in rows:
        unit_name = (r.get(unit_col) or "").strip()
        if not unit_name:
            r["hunt_codes_2026_elk"] = ""
            r["hunt_code_count_2026"] = "0"
            r["matched_hunt_names_2026"] = ""
            r["match_basis"] = f"{cfg_name};missing_unit_name"
            r["mapping_status"] = "historical_only"
            continue
        matches = match_by_unit(unit_name, candidates)
        used_fallback = False
        if not matches and fallback_candidates:
            matches = match_by_unit(unit_name, fallback_candidates)
            used_fallback = bool(matches)
        r["hunt_codes_2026_elk"] = ";".join(m["hunt_code"] for m in matches)
        r["hunt_code_count_2026"] = str(len(matches))
        r["matched_hunt_names_2026"] = " | ".join(m["hunt_name"] for m in matches)
        r["match_basis"] = f"{cfg_name} -> {fallback_name}" if used_fallback and fallback_name else cfg_name
        r["mapping_status"] = "mapped_to_2026_codes" if matches else "historical_only"
        if matches:
            match_rows += 1
    out = pd.DataFrame(rows)
    out.to_csv(path, index=False, encoding="utf-8-sig")
    out.to_excel(path.with_suffix(".xlsx"), index=False)
    return {"rows": len(rows), "rows_matched": match_rows, "rows_zero": len(rows) - match_rows}


def apply_no_unit(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path, dtype=str).fillna("")
    rows = df.to_dict(orient="records")
    for r in rows:
        r["hunt_codes_2026_elk"] = ""
        r["hunt_code_count_2026"] = "0"
        r["matched_hunt_names_2026"] = ""
        r["match_basis"] = "statewide_aggregate_no_unit"
        r["mapping_status"] = "historical_only"
    out = pd.DataFrame(rows)
    out.to_csv(path, index=False, encoding="utf-8-sig")
    out.to_excel(path.with_suffix(".xlsx"), index=False)
    return {"rows": len(rows), "rows_matched": 0, "rows_zero": len(rows)}


def normalize_antlerless_column(path: Path) -> None:
    df = pd.read_csv(path, dtype=str).fillna("")
    if "hunt_codes_2026_elk" in df.columns:
        return
    if "hunt_codes_2026_antlerless_elk" in df.columns:
        df["hunt_codes_2026_elk"] = df["hunt_codes_2026_antlerless_elk"]
        df.to_csv(path, index=False, encoding="utf-8-sig")
        df.to_excel(path.with_suffix(".xlsx"), index=False)


def main() -> None:
    db = load_db()
    db_by_code = {(r.get("hunt_code") or "").strip().upper(): r for r in db if (r.get("hunt_code") or "").strip()}

    normalize_antlerless_column(
        BASE / "elk_antlerless_by_unit_2015_2024_extract/ELK_ANTLERLESS_BY_UNIT_2015_2024.csv"
    )

    configs = [
        {
            "path": BASE / "elk_general_season_2024_extract/ELK_GENERAL_SEASON.csv",
            "mode": "code_col",
            "code_col": "hunt_code",
            "basis": "existing_hunt_code_column",
        },
        {
            "path": BASE / "limited_entry_elk_harvest_2024_extract/LIMITED_ENTRY_ELK_HARVEST_2024_STANDARDIZED.csv",
            "mode": "code_col",
            "code_col": "Hunt number",
            "basis": "existing_hunt_number_column",
        },
        {
            "path": BASE / "elk_average_age_2024_extract/ELK_AVERAGE_AGE_HARVEST_2024.csv",
            "mode": "code_col",
            "code_col": "hunt_code",
            "basis": "existing_hunt_code_column",
        },
        {
            "path": BASE / "elk_by_unit_historical_2015_2024_extract/ELK_BULL_BY_UNIT_2015_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;sex=bull;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {"exclude_cwmu_conservation_expo": True, "include_sex": {"bull"}},
        },
        {
            "path": BASE / "elk_bull_by_unit_2024_extract/ELK_TOTAL_HARVEST_BY_UNIT_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {"exclude_cwmu_conservation_expo": True},
        },
        {
            "path": BASE / "elk_bull_by_unit_2024_extract/ELK_GENERAL_SEASON_ARCHERY_HARVEST_BY_UNIT_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;hunt_type~general season;weapon~archery;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {
                "exclude_cwmu_conservation_expo": True,
                "include_hunt_type_contains": {"general season"},
                "include_weapon_contains": {"archery"},
            },
            "fallback_filter": {
                "exclude_cwmu_conservation_expo": True,
                "include_hunt_type_contains": {"general season"},
            },
            "fallback_name": "species=elk;hunt_type~general season;exclude=cwmu+conservation+expo;unit_name_contains",
        },
        {
            "path": BASE / "elk_cwmu_bull_harvest_2024_extract/ELK_CWMU_BULL_HARVEST_2024.csv",
            "mode": "direct",
        },
        {
            "path": BASE / "elk_general_extended_archery_2024_extract/ELK_GENERAL_EXTENDED_ARCHERY_HARVEST_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;hunt_type~extended archery;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {
                "exclude_cwmu_conservation_expo": True,
                "include_hunt_type_contains": {"extended archery"},
            },
            "fallback_filter": {
                "exclude_cwmu_conservation_expo": True,
                "include_hunt_type_contains": {"general season"},
            },
            "fallback_name": "species=elk;hunt_type~general season;exclude=cwmu+conservation+expo;unit_name_contains",
        },
        {
            "path": BASE / "elk_limited_antlerless_2024_extract/ELK_LIMITED_ANTLERLESS_HARVEST_2024.csv",
            "mode": "direct",
        },
        {
            "path": BASE / "elk_youth_any_bull_hunters_choice_2024_extract/ELK_YOUTH_ANY_BULL_HUNTERS_CHOICE_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;hunt_type~youth|any bull;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {
                "exclude_cwmu_conservation_expo": True,
                "include_hunt_type_contains": {"youth", "any bull"},
            },
            "fallback_filter": {"exclude_cwmu_conservation_expo": True},
            "fallback_name": "species=elk;exclude=cwmu+conservation+expo;unit_name_contains",
        },
        {
            "path": BASE / "elk_statewide_stats_1931_2024_extract/ELK_STATEWIDE_HARVEST_STATS_1931_2024.csv",
            "mode": "none",
        },
        {
            "path": BASE / "elk_winter_population_2020_2024_extract/ELK_WINTER_POPULATION_ESTIMATES_2020_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {"exclude_cwmu_conservation_expo": True},
        },
        {
            "path": BASE / "elk_preseason_calf_per_100_cows_2015_2024_extract/ELK_PRESEASON_CALF_PER_100_COWS_2015_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {"exclude_cwmu_conservation_expo": True},
        },
        {
            "path": BASE / "elk_winter_trend_2015_2024_extract/ELK_WINTER_TREND_2015_2024.csv",
            "mode": "unit",
            "cfg_name": "species=elk;exclude=cwmu+conservation+expo;unit_name_contains",
            "filter": {"exclude_cwmu_conservation_expo": True},
        },
    ]

    results: list[dict[str, Any]] = []
    for cfg in configs:
        path: Path = cfg["path"]
        if not path.exists():
            results.append({"file": str(path).replace("\\", "/"), "status": "missing_file"})
            continue

        try:
            if cfg["mode"] == "direct":
                stats = apply_direct_hunt_number(path, db_by_code)
                results.append({"file": str(path).replace("\\", "/"), "mode": "direct_hunt_number", **stats})
                continue

            if cfg["mode"] == "code_col":
                stats = apply_code_column(path, db_by_code, cfg["code_col"], cfg["basis"])
                results.append({"file": str(path).replace("\\", "/"), "mode": "existing_code_column", **stats})
                continue

            if cfg["mode"] == "none":
                stats = apply_no_unit(path)
                results.append({"file": str(path).replace("\\", "/"), "mode": "statewide_no_unit", **stats})
                continue

            candidates = filter_candidates(db, cfg["filter"])
            fallback_candidates = None
            if cfg.get("fallback_filter"):
                fallback_candidates = filter_candidates(db, cfg["fallback_filter"])
            stats = apply_unit_match(path, candidates, cfg["cfg_name"], fallback_candidates, cfg.get("fallback_name"))
            results.append(
                {
                    "file": str(path).replace("\\", "/"),
                    "mode": "unit_name_matching",
                    "candidate_pool_size": len(candidates),
                    "fallback_candidate_pool_size": len(fallback_candidates) if fallback_candidates else 0,
                    **stats,
                }
            )
        except PermissionError:
            results.append(
                {
                    "file": str(path).replace("\\", "/"),
                    "status": "skipped_locked_file",
                    "rows": None,
                    "rows_matched": None,
                    "rows_zero": None,
                }
            )

    report_csv = BASE / "elk_extracts_hunt_code_fill_20260510.csv"
    report_json = BASE / "elk_extracts_hunt_code_fill_20260510.json"

    pd.DataFrame(results).to_csv(report_csv, index=False, encoding="utf-8-sig")
    report_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "database_source": str(DB_PATH).replace("\\", "/"),
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {report_csv}")
    print(f"Wrote {report_json}")
    for r in results:
        print(r.get("file"), r.get("rows"), r.get("rows_matched"), r.get("rows_zero"))


if __name__ == "__main__":
    main()
