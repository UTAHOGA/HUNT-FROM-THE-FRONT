"""Target-scope draw-system classifier and coverage audit for Utah predictive draws."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Mapping

from . import (
    ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW,
    ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
    ALGORITHM_STATUS_MODELED_ALLOCATION,
    ALGORITHM_STATUS_MODELED_BONUS,
    ALGORITHM_STATUS_MODELED_PREFERENCE,
    ALGORITHM_STATUS_MODELED_RANDOM_ONLY,
    ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET,
    ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW,
    TARGET_SCOPE_OUT_OF_SCOPE,
    TARGET_SCOPE_TARGET,
)
from .bonus import STRATEGY_SPECS as BONUS_SPECS
from .dedicated_hunter import STRATEGY_SPECS as DEDICATED_SPECS
from .exclusions import STRATEGY_SPECS as EXCLUSION_SPECS
from .preference_antlerless import STRATEGY_SPECS as PREFERENCE_ANTLERLESS_SPECS, is_modeled_antlerless_row
from .preference_general_deer import STRATEGY_SPECS as PREFERENCE_GENERAL_DEER_SPECS, is_modeled_general_deer_row
from .private_lands_antlerless_elk import STRATEGY_SPECS as PRIVATE_LANDS_ANTLERLESS_ELK_SPECS
from .random_only import STRATEGY_SPECS as RANDOM_ONLY_SPECS
from .youth import STRATEGY_SPECS as YOUTH_SPECS


REPO = Path(__file__).resolve().parents[2]
OBSERVED_RUNTIME_PATH = REPO / "processed_data" / "draw_reality_engine_v2.csv"
PREDICTIVE_PATH = REPO / "processed_data" / "draw_reality_engine_predictive_v2.csv"

ALL_SPECS = (
    BONUS_SPECS
    + PREFERENCE_GENERAL_DEER_SPECS
    + PREFERENCE_ANTLERLESS_SPECS
    + DEDICATED_SPECS
    + YOUTH_SPECS
    + PRIVATE_LANDS_ANTLERLESS_ELK_SPECS
    + RANDOM_ONLY_SPECS
    + EXCLUSION_SPECS
)
REGISTRY = {spec.draw_system_type: spec for spec in ALL_SPECS}
DRAW_SYSTEM_ORDER = [spec.draw_system_type for spec in ALL_SPECS]

OUT_OF_SCOPE_TOKENS = (
    "swan",
    "sandhill crane",
    "crane",
    "sharp-tailed grouse",
    "sharp tailed grouse",
    "sage-grouse",
    "sage grouse",
    "greater sage grouse",
    "grouse",
    "waterfowl",
    "duck",
    "goose",
    "geese",
    "small game",
    "fishing",
    "fish",
    "upland game",
)
BIG_GAME_TOKENS = (
    "deer",
    "elk",
    "pronghorn",
    "moose",
    "bison",
    "mountain goat",
    "goat",
    "bighorn sheep",
    "desert bighorn",
    "rocky mountain bighorn",
    "sheep",
)
TARGET_OTHER_TOKENS = ("turkey", "black bear", "bear", "mountain lion", "lion", "cougar")
TARGET_DRAW_SYSTEM_TYPES = {
    "BONUS_OIL_BIG_GAME",
    "BONUS_LE_BIG_GAME",
    "BONUS_PLE_BIG_GAME",
    "BONUS_CWMU_BIG_GAME",
    "BONUS_ANTLERLESS_MOOSE",
    "BONUS_EWE_BIGHORN",
    "BONUS_TURKEY",
    "PREFERENCE_GENERAL_SEASON_BUCK_DEER",
    "PREFERENCE_DEDICATED_HUNTER_DEER",
    "PREFERENCE_ANTLERLESS_DEER",
    "PREFERENCE_ANTLERLESS_ELK",
    "PREFERENCE_DOE_PRONGHORN",
    "GENERAL_BIG_GAME_OTHER",
    "BEAR_DRAW",
    "MOUNTAIN_LION_DRAW",
    "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK",
    "RANDOM_ONLY_TARGET",
    "OTC_OR_REMAINING_TARGET",
    "LANDOWNER_BIG_GAME",
    "MITIGATION_OR_DEPREDATION_BIG_GAME",
    "UNKNOWN_TARGET",
}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _clean_lower(value: object) -> str:
    return _clean(value).lower()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _safe_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _joined_text(row: Mapping[str, object]) -> str:
    parts = [
        row.get("hunt_code"),
        row.get("hunt_name"),
        row.get("species"),
        row.get("sex_type"),
        row.get("hunt_type"),
        row.get("hunt_class"),
        row.get("weapon"),
        row.get("draw_pool"),
        row.get("source_file"),
        row.get("NOTES"),
    ]
    return " ".join(_clean_lower(part) for part in parts if _clean(part))


def is_out_of_scope_non_target(row: Mapping[str, object]) -> bool:
    text = _joined_text(row)
    return any(token in text for token in OUT_OF_SCOPE_TOKENS) and "turkey" not in text


def is_target_scope(row: Mapping[str, object]) -> bool:
    text = _joined_text(row)
    if is_out_of_scope_non_target(row):
        return False
    if any(token in text for token in TARGET_OTHER_TOKENS):
        return True
    if any(token in text for token in BIG_GAME_TOKENS):
        return True
    return False


def classify_draw_system_type(row: Mapping[str, object]) -> str:
    text = _joined_text(row)
    hunt_type = _clean_lower(row.get("hunt_type"))
    hunt_class = _clean_lower(row.get("hunt_class"))
    species = _clean_lower(row.get("species"))
    sex_type = _clean_lower(row.get("sex_type"))
    draw_pool = _clean_lower(row.get("draw_pool"))

    if is_out_of_scope_non_target(row):
        return "OUT_OF_SCOPE_NON_TARGET"

    if "mitigation" in text or "depredation" in text:
        return "MITIGATION_OR_DEPREDATION_BIG_GAME"
    if "private land only" in text and "elk" in text and "antlerless" in text:
        return "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK"
    if any(token in text for token in ("conservation", "expo", "sportsman")):
        return "OTC_OR_REMAINING_TARGET"
    if "landowner" in text or "private land only" in text or hunt_class == "private":
        return "LANDOWNER_BIG_GAME"
    if "remaining permit" in text or " otc" in f" {text}" or "over the counter" in text:
        return "OTC_OR_REMAINING_TARGET"
    if "restricted pursuit" in text or "extended archery" in text:
        return "RANDOM_ONLY_TARGET"

    if "black bear" in text or species == "bear" or (" bear " in f" {text} " and "bighorn" not in text):
        return "BEAR_DRAW"
    if "mountain lion" in text or "cougar" in text:
        return "MOUNTAIN_LION_DRAW"
    if "turkey" in text:
        return "BONUS_TURKEY"

    if "moose" in text and ("antlerless" in text or sex_type in {"antlerless", "cow", "cow only"}):
        return "BONUS_ANTLERLESS_MOOSE"
    if "bighorn" in text and ("ewe" in text or sex_type == "ewe"):
        return "BONUS_EWE_BIGHORN"

    if "cwmu" in text:
        return "BONUS_CWMU_BIG_GAME"

    if draw_pool == "dedicated_hunter" or draw_pool == "youth_dedicated_hunter" or "dedicated hunter" in text:
        return "PREFERENCE_DEDICATED_HUNTER_DEER"

    if ("doe" in text or sex_type == "doe") and "pronghorn" in text:
        return "PREFERENCE_DOE_PRONGHORN"
    if "antlerless" in text and "deer" in text:
        return "PREFERENCE_ANTLERLESS_DEER"
    if "antlerless" in text and "elk" in text:
        return "PREFERENCE_ANTLERLESS_ELK"

    if "general season" in text or "general-season" in text or "management buck deer" in text or "cactus buck" in text:
        if "deer" in text and "buck" in text:
            return "PREFERENCE_GENERAL_SEASON_BUCK_DEER"
        return "GENERAL_BIG_GAME_OTHER"

    if "premium limited entry" in text or "premium limited-entry" in text:
        return "BONUS_PLE_BIG_GAME"
    if "once-in-a-lifetime" in text or "once in a lifetime" in text or "o.i.l." in text or "oial" in text:
        return "BONUS_OIL_BIG_GAME"
    if any(token in text for token in BIG_GAME_TOKENS):
        if "limited entry" in text or "limited-entry" in text:
            return "BONUS_LE_BIG_GAME"
        if species in {"bison", "mountain goat"}:
            return "BONUS_OIL_BIG_GAME"
        if "bighorn sheep" in text and "ewe" not in text:
            return "BONUS_OIL_BIG_GAME"
        if species == "moose" and "antlerless" not in text:
            return "BONUS_OIL_BIG_GAME"
        return "GENERAL_BIG_GAME_OTHER"

    if is_target_scope(row):
        return "UNKNOWN_TARGET"
    return "OUT_OF_SCOPE_NON_TARGET"


def resolve_algorithm_status(row: Mapping[str, object], draw_system_type: str | None = None) -> str:
    draw_system_type = draw_system_type or classify_draw_system_type(row)
    if draw_system_type == "PREFERENCE_GENERAL_SEASON_BUCK_DEER":
        return ALGORITHM_STATUS_MODELED_PREFERENCE if is_modeled_general_deer_row(row) else ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING
    if draw_system_type in {"PREFERENCE_ANTLERLESS_DEER", "PREFERENCE_ANTLERLESS_ELK", "PREFERENCE_DOE_PRONGHORN"}:
        return ALGORITHM_STATUS_MODELED_PREFERENCE if is_modeled_antlerless_row(row) else ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING
    return REGISTRY[draw_system_type].algorithm_status


def target_scope_label(row: Mapping[str, object], draw_system_type: str | None = None) -> str:
    draw_system_type = draw_system_type or classify_draw_system_type(row)
    return REGISTRY[draw_system_type].target_scope


def modeled_by_engine(row: Mapping[str, object], draw_system_type: str | None = None, algorithm_status: str | None = None) -> bool:
    draw_system_type = draw_system_type or classify_draw_system_type(row)
    algorithm_status = algorithm_status or resolve_algorithm_status(row, draw_system_type)
    if algorithm_status not in {
        ALGORITHM_STATUS_MODELED_ALLOCATION,
        ALGORITHM_STATUS_MODELED_BONUS,
        ALGORITHM_STATUS_MODELED_PREFERENCE,
        ALGORITHM_STATUS_MODELED_RANDOM_ONLY,
    }:
        return False
    source_dataset = _clean_lower(row.get("source_dataset"))
    return source_dataset == "predictive"


def classification_reason(row: Mapping[str, object], draw_system_type: str | None = None, algorithm_status: str | None = None) -> str:
    draw_system_type = draw_system_type or classify_draw_system_type(row)
    algorithm_status = algorithm_status or resolve_algorithm_status(row, draw_system_type)
    spec = REGISTRY[draw_system_type]
    if modeled_by_engine(row, draw_system_type, algorithm_status):
        return f"Modeled by {spec.module_name}."
    return spec.reason


def classify_runtime_row(row: Mapping[str, object]) -> dict[str, object]:
    draw_system_type = classify_draw_system_type(row)
    algorithm_status = resolve_algorithm_status(row, draw_system_type)
    target_scope = target_scope_label(row, draw_system_type)
    is_modeled = modeled_by_engine(row, draw_system_type, algorithm_status)
    reason = classification_reason(row, draw_system_type, algorithm_status)
    return {
        "draw_system_type": draw_system_type,
        "algorithm_status": algorithm_status,
        "target_scope": target_scope,
        "modeled_by_engine": is_modeled,
        "reason": reason,
    }


def sanitize_modeled_probability_fields(row: dict[str, object]) -> dict[str, object]:
    classification = classify_runtime_row(row)
    row.update(classification)
    if classification["algorithm_status"] in {
        ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING,
        ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW,
        ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET,
        ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW,
    }:
        for key in ("p_draw", "p_draw_pct", "p_bonus_pool", "p_random_pool", "p_bonus_pool_pct", "p_random_pool_pct"):
            row[key] = ""
        if classification["algorithm_status"] == ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET:
            row["draw_outlook"] = "OUT OF SCOPE"
        else:
            row["draw_outlook"] = "MODEL PENDING" if classification["algorithm_status"] == ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING else "NOT MODELED"
    return row


def _coverage_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for source_dataset, path in (("observed_runtime", OBSERVED_RUNTIME_PATH), ("predictive", PREDICTIVE_PATH)):
        for raw in _read_csv(path):
            row = dict(raw)
            row["source_dataset"] = source_dataset
            classification = classify_runtime_row(row)
            sanitized = sanitize_modeled_probability_fields(row)
            rows.append(
                {
                    "hunt_code": _clean(raw.get("hunt_code")).upper(),
                    "hunt_name": _clean(raw.get("hunt_name")),
                    "species": _clean(raw.get("species")),
                    "hunt_type": _clean(raw.get("hunt_type")),
                    "residency": _clean(raw.get("residency")),
                    "year": _clean(raw.get("year")),
                    "draw_system_type": classification["draw_system_type"],
                    "algorithm_status": classification["algorithm_status"],
                    "target_scope": classification["target_scope"],
                    "modeled_by_engine": "True" if classification["modeled_by_engine"] else "False",
                    "reason": classification["reason"],
                    "source_file": _clean(raw.get("source_file")),
                    "source_years_used": _clean(raw.get("source_years_used")),
                    "source_dataset": source_dataset,
                    "draw_pool": _clean(raw.get("draw_pool")),
                    "hunt_class": _clean(raw.get("hunt_class")),
                    "sex_type": _clean(raw.get("sex_type")),
                    "weapon": _clean(raw.get("weapon")),
                    "p_draw": _clean(sanitized.get("p_draw")),
                    "p_draw_pct": _clean(sanitized.get("p_draw_pct")),
                    "p_bonus_pool": _clean(sanitized.get("p_bonus_pool")),
                    "p_random_pool": _clean(sanitized.get("p_random_pool")),
                    "draw_outlook": _clean(sanitized.get("draw_outlook")),
                }
            )
    return rows


def _distinct_count(rows: list[dict[str, object]], predicate, field: str = "hunt_code") -> int:
    return len({str(row.get(field, "")).strip().upper() for row in rows if predicate(row) and str(row.get(field, "")).strip()})


def _counter(rows: list[dict[str, object]], field: str, predicate=lambda row: True) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        if not predicate(row):
            continue
        key = _clean(row.get(field)) or "(blank)"
        counts[key] += 1
    return dict(sorted(counts.items()))


def build_draw_system_coverage_report(
    output_dir: Path,
    forecast_year: int = 2026,
    history_years: list[int] | None = None,
) -> dict[str, Path]:
    history_years = history_years or [2021, 2022, 2023, 2024, 2025]
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _coverage_rows()

    detail_csv = output_dir / "draw_system_coverage_report.csv"
    _write_csv(
        detail_csv,
        rows,
        [
            "hunt_code",
            "hunt_name",
            "species",
            "hunt_type",
            "residency",
            "year",
            "draw_system_type",
            "algorithm_status",
            "target_scope",
            "modeled_by_engine",
            "reason",
            "source_file",
            "source_years_used",
            "source_dataset",
            "draw_pool",
            "hunt_class",
            "sex_type",
            "weapon",
            "p_draw",
            "p_draw_pct",
            "p_bonus_pool",
            "p_random_pool",
            "draw_outlook",
        ],
    )

    target_predicate = lambda row: row["target_scope"] == TARGET_SCOPE_TARGET
    modeled_predicate = lambda row: target_predicate(row) and str(row["modeled_by_engine"]) == "True"
    unmodeled_predicate = lambda row: target_predicate(row) and str(row["modeled_by_engine"]) != "True"
    out_of_scope_predicate = lambda row: row["algorithm_status"] == ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET
    unknown_target_predicate = lambda row: row["algorithm_status"] == ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW

    counts_by_draw_system_type = _counter(rows, "draw_system_type")
    counts_by_draw_system_type_hunt_codes = {
        draw_system_type: _distinct_count(rows, lambda row, dst=draw_system_type: row["draw_system_type"] == dst)
        for draw_system_type in DRAW_SYSTEM_ORDER
    }

    summary_rows = []
    for draw_system_type in DRAW_SYSTEM_ORDER:
        algorithm_status = REGISTRY[draw_system_type].algorithm_status
        modeled_engine_rows = sum(
            1 for row in rows if row["draw_system_type"] == draw_system_type and str(row["modeled_by_engine"]) == "True"
        )
        summary_rows.append(
            {
                "draw_system_type": draw_system_type,
                "row_count": counts_by_draw_system_type.get(draw_system_type, 0),
                "hunt_code_count": counts_by_draw_system_type_hunt_codes.get(draw_system_type, 0),
                "algorithm_status": algorithm_status,
            }
        )

    answers = {
        "is_general_season_buck_deer_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "PREFERENCE_GENERAL_SEASON_BUCK_DEER" and str(row["modeled_by_engine"]) == "True") > 0,
        "is_dedicated_hunter_deer_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "PREFERENCE_DEDICATED_HUNTER_DEER" and str(row["modeled_by_engine"]) == "True") > 0,
        "is_antlerless_deer_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "PREFERENCE_ANTLERLESS_DEER" and str(row["modeled_by_engine"]) == "True") > 0,
        "is_antlerless_elk_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "PREFERENCE_ANTLERLESS_ELK" and str(row["modeled_by_engine"]) == "True") > 0,
        "is_doe_pronghorn_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "PREFERENCE_DOE_PRONGHORN" and str(row["modeled_by_engine"]) == "True") > 0,
        "are_antlerless_moose_and_ewe_sheep_modeled_under_bonus_rules": False,
        "are_all_oil_big_game_categories_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "BONUS_OIL_BIG_GAME") == _distinct_count(rows, lambda row: row["draw_system_type"] == "BONUS_OIL_BIG_GAME" and str(row["modeled_by_engine"]) == "True"),
        "are_all_le_big_game_categories_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "BONUS_LE_BIG_GAME") == _distinct_count(rows, lambda row: row["draw_system_type"] == "BONUS_LE_BIG_GAME" and str(row["modeled_by_engine"]) == "True"),
        "are_all_ple_big_game_categories_modeled": _distinct_count(rows, lambda row: row["draw_system_type"] == "BONUS_PLE_BIG_GAME") == _distinct_count(rows, lambda row: row["draw_system_type"] == "BONUS_PLE_BIG_GAME" and str(row["modeled_by_engine"]) == "True"),
        "is_turkey_modeled": False,
        "is_bear_modeled": False,
        "is_mountain_lion_cougar_modeled": False,
    }

    report = {
        "forecast_year": forecast_year,
        "history_years": history_years,
        "total_rows_seen": len(rows),
        "total_hunt_codes_seen": _distinct_count(rows, lambda row: True),
        "target_scope_rows": sum(1 for row in rows if target_predicate(row)),
        "target_scope_hunt_codes": _distinct_count(rows, target_predicate),
        "out_of_scope_rows": sum(1 for row in rows if out_of_scope_predicate(row)),
        "out_of_scope_hunt_codes": _distinct_count(rows, out_of_scope_predicate),
        "unknown_target_rows": sum(1 for row in rows if unknown_target_predicate(row)),
        "unknown_target_hunt_codes": _distinct_count(rows, unknown_target_predicate),
        "counts_by_draw_system_type": counts_by_draw_system_type,
        "counts_by_draw_system_type_hunt_codes": counts_by_draw_system_type_hunt_codes,
        "counts_by_algorithm_status": _counter(rows, "algorithm_status"),
        "counts_by_species": _counter(rows, "species"),
        "counts_by_residency": _counter(rows, "residency"),
        "counts_by_year": _counter(rows, "year"),
        "modeled_target_rows": sum(1 for row in rows if modeled_predicate(row)),
        "unmodeled_target_rows": sum(1 for row in rows if unmodeled_predicate(row)),
        "modeled_target_hunt_codes": _distinct_count(rows, modeled_predicate),
        "unmodeled_target_hunt_codes": _distinct_count(rows, unmodeled_predicate),
        "out_of_scope_non_target_rows": sum(1 for row in rows if out_of_scope_predicate(row)),
        "out_of_scope_non_target_hunt_codes": _distinct_count(rows, out_of_scope_predicate),
        "answers": answers,
        "currently_production_modeled_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_MODELED_BONUS],
        "modeled_bonus_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_MODELED_BONUS],
        "modeled_preference_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_MODELED_PREFERENCE],
        "modeled_allocation_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_MODELED_ALLOCATION],
        "modeled_random_only_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_MODELED_RANDOM_ONLY],
        "in_scope_model_pending_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING],
        "excluded_not_predictive_draw_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW],
        "out_of_scope_non_target_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_OUT_OF_SCOPE_NON_TARGET],
        "unknown_target_categories": [draw_system_type for draw_system_type, spec in REGISTRY.items() if spec.algorithm_status == ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW],
        "target_categories_only_in_scope_model_pending": sorted(
            {row["draw_system_type"] for row in rows if row["algorithm_status"] == ALGORITHM_STATUS_IN_SCOPE_MODEL_PENDING}
        ),
        "target_categories_excluded_not_predictive_draw": sorted(
            {row["draw_system_type"] for row in rows if row["algorithm_status"] == ALGORITHM_STATUS_EXCLUDED_NOT_PREDICTIVE_DRAW}
        ),
        "target_categories_unknown_needs_review": sorted(
            {row["draw_system_type"] for row in rows if row["algorithm_status"] == ALGORITHM_STATUS_UNKNOWN_TARGET_NEEDS_REVIEW}
        ),
        "summary_by_draw_system_type": summary_rows,
        "source_files": {
            "observed_runtime": _safe_relative(OBSERVED_RUNTIME_PATH),
            "predictive_runtime": _safe_relative(PREDICTIVE_PATH),
            "detail_csv": _safe_relative(detail_csv),
        },
    }
    json_path = output_dir / "draw_system_coverage_report.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"csv": detail_csv, "json": json_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO / "processed_data"))
    parser.add_argument("--forecast-year", type=int, default=2026)
    parser.add_argument("--history-years", default="2021,2022,2023,2024,2025")
    args = parser.parse_args()
    history_years = [int(token.strip()) for token in str(args.history_years).split(",") if token.strip()]
    artifacts = build_draw_system_coverage_report(Path(args.output_dir), forecast_year=args.forecast_year, history_years=history_years)
    print(json.dumps({key: str(value) for key, value in artifacts.items()}, indent=2))


if __name__ == "__main__":
    main()
