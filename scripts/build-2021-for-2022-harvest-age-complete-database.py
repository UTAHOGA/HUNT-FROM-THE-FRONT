from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2022" / "csv" / "harvest_results_2021_for_2022_hunt_code_keyed.csv"
SPECIES_FEATURES = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2022"
    / "average_harvest_age_2021_for_2022_species_crosswalk_package"
    / "average_harvest_age_2021_for_2022_features_by_hunt_code.csv"
)
BLACK_BEAR_FEATURES = (
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2022"
    / "black_bear_2021_for_2022_age_crosswalk_package"
    / "black_bear_2021_for_2022_age_features_by_hunt_code.csv"
)

OUT_DIR = ROOT / "data_model" / "harvest_quality"
OUT_COMPLETE = OUT_DIR / "harvest_results_2021_for_2022_complete_database.csv"
OUT_SUMMARY = OUT_DIR / "harvest_results_2021_for_2022_complete_database_summary.json"


def norm_code(value: str) -> str:
    return "".join(ch for ch in str(value or "").upper().strip() if ch.isalnum())


def parse_age(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        num = float(text)
    except ValueError:
        return ""
    if num <= 0 or num >= 30:
        return ""
    return f"{num:.2f}".rstrip("0").rstrip(".")


def confidence_rank(value: str) -> int:
    text = str(value or "").strip().lower()
    if text == "high":
        return 3
    if text == "medium":
        return 2
    if text == "low":
        return 1
    return 0


def load_age_candidates() -> pd.DataFrame:
    species = pd.read_csv(SPECIES_FEATURES, dtype=str, low_memory=False).fillna("")
    bear = pd.read_csv(BLACK_BEAR_FEATURES, dtype=str, low_memory=False).fillna("")
    rows: list[dict[str, str]] = []

    for _, row in species.iterrows():
        code = norm_code(row.get("hunt_code", ""))
        if not code:
            continue
        age = parse_age(row.get("average_harvest_age", ""))
        if not age:
            continue
        rows.append(
            {
                "hunt_code": code,
                "species": str(row.get("species", "")).strip(),
                "reported_hunt_year": str(row.get("reported_hunt_year", "")).strip(),
                "model_target_year": str(row.get("model_target_year", "")).strip(),
                "average_harvest_age": age,
                "crosswalk_confidence": str(row.get("crosswalk_confidence", "")).strip(),
                "source_package": "average_harvest_age_2021_for_2022_species_crosswalk_package",
            }
        )

    for _, row in bear.iterrows():
        code = norm_code(row.get("hunt_code", ""))
        if not code:
            continue
        age = parse_age(row.get("average_harvest_age", ""))
        if not age:
            continue
        rows.append(
            {
                "hunt_code": code,
                "species": str(row.get("species", "")).strip(),
                "reported_hunt_year": str(row.get("reported_hunt_year", "")).strip(),
                "model_target_year": str(row.get("model_target_year", "")).strip(),
                "average_harvest_age": age,
                "crosswalk_confidence": str(row.get("crosswalk_confidence", "")).strip(),
                "source_package": "black_bear_2021_for_2022_age_crosswalk_package",
            }
        )

    return pd.DataFrame(rows).fillna("")


def select_age_by_code(age_df: pd.DataFrame) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for _, row in age_df.iterrows():
        by_code[row["hunt_code"]].append(row.to_dict())

    resolved: dict[str, dict[str, str]] = {}
    conflicts: dict[str, list[str]] = {}
    for code, items in by_code.items():
        values = sorted({str(item.get("average_harvest_age", "")).strip() for item in items if str(item.get("average_harvest_age", "")).strip()})
        if len(values) > 1:
            ranked = sorted(items, key=lambda i: confidence_rank(i.get("crosswalk_confidence", "")), reverse=True)
            top_rank = confidence_rank(ranked[0].get("crosswalk_confidence", ""))
            top_values = sorted(
                {
                    str(i.get("average_harvest_age", "")).strip()
                    for i in ranked
                    if confidence_rank(i.get("crosswalk_confidence", "")) == top_rank and str(i.get("average_harvest_age", "")).strip()
                }
            )
            if len(top_values) == 1:
                chosen = top_values[0]
                selected = ranked[0]
                resolved[code] = {
                    "average_harvest_age": chosen,
                    "crosswalk_confidence": selected.get("crosswalk_confidence", ""),
                    "source_package": selected.get("source_package", ""),
                    "mapping_status": "resolved_by_confidence_rank",
                }
                continue
            conflicts[code] = values
            continue

        if not values:
            continue
        selected = max(items, key=lambda i: confidence_rank(i.get("crosswalk_confidence", "")))
        resolved[code] = {
            "average_harvest_age": values[0],
            "crosswalk_confidence": selected.get("crosswalk_confidence", ""),
            "source_package": selected.get("source_package", ""),
            "mapping_status": "direct_or_single_value",
        }
    return resolved, conflicts


def main() -> None:
    if not BASE_PATH.exists():
        raise FileNotFoundError(f"Missing base file: {BASE_PATH}")
    for src in [SPECIES_FEATURES, BLACK_BEAR_FEATURES]:
        if not src.exists():
            raise FileNotFoundError(f"Missing required source: {src}")

    base = pd.read_csv(BASE_PATH, dtype=str, low_memory=False).fillna("")
    base_2021 = base[base["reported_hunt_year"].astype(str).str.strip() == "2021"].copy()
    age_candidates = load_age_candidates()
    resolved, conflicts = select_age_by_code(age_candidates)

    out = base_2021.copy()
    out["average_harvest_age_2021"] = ""
    out["age_data_available_2021"] = "false"
    out["age_source_package_2021"] = ""
    out["age_mapping_status_2021"] = ""
    out["age_match_confidence_2021"] = ""

    rows_with_age = 0
    for idx, row in out.iterrows():
        code = norm_code(row.get("hunt_code", ""))
        hit = resolved.get(code)
        if not hit:
            continue
        out.at[idx, "average_harvest_age_2021"] = hit.get("average_harvest_age", "")
        out.at[idx, "age_data_available_2021"] = "true"
        out.at[idx, "age_source_package_2021"] = hit.get("source_package", "")
        out.at[idx, "age_mapping_status_2021"] = hit.get("mapping_status", "")
        out.at[idx, "age_match_confidence_2021"] = hit.get("crosswalk_confidence", "")
        rows_with_age += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_COMPLETE, index=False, encoding="utf-8-sig")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_file": str(BASE_PATH).replace("\\", "/"),
        "base_rows_2021": int(len(base_2021)),
        "age_candidate_rows_total": int(len(age_candidates)),
        "age_candidate_rows_by_package": age_candidates["source_package"].value_counts().to_dict() if not age_candidates.empty else {},
        "age_candidate_rows_by_species": age_candidates["species"].value_counts().to_dict() if not age_candidates.empty else {},
        "resolved_hunt_codes": len(resolved),
        "conflict_hunt_codes": len(conflicts),
        "rows_with_age_in_complete_database": rows_with_age,
        "rows_without_age_in_complete_database": int(len(base_2021) - rows_with_age),
        "conflict_sample": dict(list(conflicts.items())[:20]),
        "outputs": {
            "complete_database": str(OUT_COMPLETE).replace("\\", "/"),
        },
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
