"""Rebuild the processed Utah CSV contract from fixture inputs.

This module keeps the current frontend/data contract reproducible without
introducing a new architecture. It reads the small synthetic fixture tables in
``data/utah/fixtures`` and emits the processed CSVs consumed by the research UI.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .constants import DEFAULT_PREDICTION_YEAR, MODEL_VERSION, RULE_VERSION
from .materialize import materialize_rows
from .models import normalize_residency


DEFAULT_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "data" / "utah" / "fixtures"
DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "processed_data"

DRAW_REALITY_FILENAME = "draw_reality_engine.csv"
POINT_LADDER_FILENAME = "point_ladder_view.csv"
HUNT_MASTER_FILENAME = "hunt_master_enriched.csv"
HUNT_REFERENCE_FILENAME = "hunt_unit_reference_linked.csv"

POINT_LADDER_HEADER = [
    "hunt_code",
    "residency",
    "points",
    "public_permits_2025",
    "public_permits_2026",
    "public_permits_2026_source",
    "max_point_permits_2025",
    "max_point_permits_2026",
    "random_permits_2025",
    "random_permits_2026",
    "guaranteed_at_2025",
    "guaranteed_at_2026",
    "permit_delta_2025_to_2026",
    "projected_applicants_2026_source",
    "guaranteed_delta_2025_to_2026",
    "applicants_above",
    "applicants_at_level",
    "random_draw_odds_2026",
    "gap",
    "delta_gap",
    "status",
    "trend",
    "draw_outlook",
]

HUNT_MASTER_HEADER = [
    "hunt_code",
    "species",
    "hunt_name",
    "weapon",
    "hunt_type",
    "access_type",
    "residency",
    "points",
    "public_permits_2025",
    "public_permits_2026",
    "public_permits_2026_source",
    "applicants_2025",
    "projected_applicants_2026",
    "projected_applicants_2026_source",
    "odds_2025",
    "odds_2026_projected",
    "max_point_permits_2026",
    "random_permits_2026",
    "success_hunters",
    "success_harvest",
    "success_percent",
    "missing_draw_data",
    "missing_projection",
    "missing_permits",
]

HUNT_REFERENCE_HEADER = [
    "hunt_code",
    "residency",
    "hunt_name",
    "species",
    "weapon",
    "hunt_type",
    "access_type",
    "public_permits_2025",
    "public_permits_2026",
    "permits_2025_res",
    "permits_2025_nr",
    "permits_2025_total",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "applicants_2025",
    "projected_applicants_2026",
    "max_point_permits_2026",
    "random_permits_2026",
    "guaranteed_at_2026",
    "delta_gap",
    "trend",
    "coverage_status",
    "coverage_reason",
    "bg_odds_pdf_page_index",
    "bg_odds_printed_page",
    "bg_odds_hunt_title",
    "has_bg_odds_page",
    "rac_page",
    "rac_section",
    "source_pdf",
    "harvest_hunters_2025",
    "harvest_2025",
    "harvest_success_percent_2025",
    "harvest_average_days_2025",
    "harvest_satisfaction_2025",
    "source_file_2026",
    "link_key",
    "antlerless_odds_sheet",
    "antlerless_odds_row_start",
    "antlerless_odds_title",
    "has_antlerless_odds_page",
    "has_any_odds_source",
]


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _value(value: object) -> object:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.3f}"
        return value

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _value(row.get(name, "")) for name in fieldnames})


def _num(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _fmt3(value: object) -> str:
    number = _num(value)
    if number is None:
        return ""
    return f"{number:.3f}"


def _fmt_int(value: object) -> str:
    number = _num(value)
    if number is None:
        return ""
    return str(int(round(number)))


def _fmt_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _fmt_bool(value: object) -> str:
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "y"}:
            return "TRUE"
        if text in {"false", "0", "no", "n"}:
            return "FALSE"
    return "TRUE" if bool(value) else "FALSE"


def _read_fixture_tables(source_root: Path) -> dict[str, list[dict[str, str]]]:
    filenames = {
        "seed_predictions": DRAW_REALITY_FILENAME,
        "applications": "applications_raw.csv",
        "applicants": "applicants_raw.csv",
        "groups": "groups_raw.csv",
        "points": "points_raw.csv",
        "quotas": "quotas_raw.csv",
        "draw_results": "draw_results_raw.csv",
        "hunt_metadata": "hunt_metadata_raw.csv",
        "harvest_quality": "harvest_quality_raw.csv",
    }
    tables: dict[str, list[dict[str, str]]] = {}
    for key, filename in filenames.items():
        path = source_root / filename
        if path.exists():
            tables[key] = _load_csv(path)
            continue
        if key == "seed_predictions":
            raise FileNotFoundError(path)
        tables[key] = []
    return tables


def _group_by(rows: Iterable[Mapping[str, str]], key_fields: Sequence[str]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = tuple(_fmt_text(row.get(field)).upper() if field == "hunt_code" else _fmt_text(row.get(field)) for field in key_fields)
        grouped[key].append(dict(row))
    return grouped


def _hunt_key(hunt_code: object, residency: object = "") -> tuple[str, str]:
    return _fmt_text(hunt_code).upper(), normalize_residency(residency)


def _selected_quota_row(quotas_by_hunt: dict[str, dict[str, str]], hunt_code: str) -> dict[str, str]:
    return dict(quotas_by_hunt.get(hunt_code.upper(), {}))


def _output_residencies(quota_row: Mapping[str, str]) -> list[str]:
    residencies: list[str] = []
    if _num(quota_row.get("resident_quota")) is None or (_num(quota_row.get("resident_quota")) or 0) > 0:
        residencies.append("Resident")
    if (_num(quota_row.get("nonresident_quota")) or 0) > 0:
        residencies.append("Nonresident")
    return residencies or ["Resident"]


def _application_counts(applications: Sequence[Mapping[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in applications:
        counts[_fmt_text(row.get("hunt_code")).upper()] += 1
    return counts


def _harvest_lookup(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        out[_fmt_text(row.get("hunt_code")).upper()] = dict(row)
    return out


def _metadata_lookup(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        out[_fmt_text(row.get("hunt_code")).upper()] = dict(row)
    return out


def _prediction_rows(seed_rows: Sequence[Mapping[str, str]]) -> list[dict[str, object]]:
    predictions = materialize_rows(seed_rows, legacy_rows=seed_rows)
    predictions.sort(key=lambda row: (_fmt_text(row.get("hunt_code")).upper(), _fmt_text(row.get("residency")), int(_num(row.get("points")) or 0)))
    return predictions


def _build_point_ladder_rows(
    predictions: Sequence[Mapping[str, object]],
    quotas_by_hunt: Mapping[str, Mapping[str, str]],
    application_counts: Mapping[str, int],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in predictions:
        hunt_code = _fmt_text(row.get("hunt_code")).upper()
        quota = dict(quotas_by_hunt.get(hunt_code, {}))
        points = int(_num(row.get("points")) or 0)
        expected_cutoff = _num(row.get("expected_cutoff_points"))
        gap = int(round((expected_cutoff if expected_cutoff is not None else float(points)) - points))
        row_out = {
            "hunt_code": hunt_code,
            "residency": _fmt_text(row.get("residency"), "Resident"),
            "points": str(points),
            "public_permits_2025": _fmt_int(quota.get("total_public_permits")),
            "public_permits_2026": _fmt_int(quota.get("total_public_permits")),
            "public_permits_2026_source": _fmt_text(row.get("quota_source") or quota.get("quota_source"), "fixture"),
            "max_point_permits_2025": _fmt_int(quota.get("reserved_quota")),
            "max_point_permits_2026": _fmt_int(quota.get("reserved_quota")),
            "random_permits_2025": _fmt_int(quota.get("random_quota")),
            "random_permits_2026": _fmt_int(quota.get("random_quota")),
            "guaranteed_at_2025": _fmt_int(expected_cutoff if expected_cutoff is not None else points),
            "guaranteed_at_2026": _fmt_int(expected_cutoff if expected_cutoff is not None else points),
            "permit_delta_2025_to_2026": "0",
            "projected_applicants_2026_source": _fmt_text(row.get("applicant_pool_source"), "fixture"),
            "guaranteed_delta_2025_to_2026": "0",
            "applicants_above": "0",
            "applicants_at_level": str(application_counts.get(hunt_code, 0)),
            "random_draw_odds_2026": _fmt3(row.get("random_draw_odds_2026")),
            "gap": str(gap),
            "delta_gap": str(gap),
            "status": _fmt_text(row.get("status"), "NO MODEL").upper(),
            "trend": _fmt_text(row.get("trend"), "YELLOW").upper(),
            "draw_outlook": _fmt_text(row.get("draw_outlook"), "NOT AVAILABLE").upper(),
        }
        rows.append(row_out)
    rows.sort(key=lambda row: (row["hunt_code"], row["residency"], int(row["points"])))
    return rows


def _build_hunt_master_rows(
    predictions: Sequence[Mapping[str, object]],
    metadata_by_hunt: Mapping[str, Mapping[str, str]],
    quotas_by_hunt: Mapping[str, Mapping[str, str]],
    applications_by_hunt: Mapping[str, int],
    harvest_by_hunt: Mapping[str, Mapping[str, str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in predictions:
        hunt_code = _fmt_text(row.get("hunt_code")).upper()
        meta = dict(metadata_by_hunt.get(hunt_code, {}))
        quota = dict(quotas_by_hunt.get(hunt_code, {}))
        harvest = dict(harvest_by_hunt.get(hunt_code, {}))
        species = _fmt_text(meta.get("species") or row.get("species"), "Unknown")
        hunt_name = _fmt_text(meta.get("unit_name") or meta.get("hunt_name") or f"{species} Fixture Hunt", "Fixture Hunt")
        weapon = _fmt_text(meta.get("weapon"), "Unknown")
        hunt_type = _fmt_text(meta.get("hunt_type"), "other")
        access_type = "Public" if _fmt_text(meta.get("permit_type"), "public").lower() == "public" else _fmt_text(meta.get("permit_type"), "Public")
        success_hunters = harvest.get("permits_afield", harvest.get("harvest_hunters", ""))
        success_harvest = harvest.get("harvest", "")
        success_percent = _fmt3((_num(harvest.get("harvest_success")) or 0) * 100 if _num(harvest.get("harvest_success")) is not None else "")
        rows.append(
            {
                "hunt_code": hunt_code,
                "species": species,
                "hunt_name": hunt_name,
                "weapon": weapon,
                "hunt_type": hunt_type,
                "access_type": access_type,
                "residency": _fmt_text(row.get("residency"), "Resident"),
                "points": str(int(_num(row.get("points")) or 0)),
                "public_permits_2025": _fmt_int(quota.get("total_public_permits")),
                "public_permits_2026": _fmt_int(quota.get("total_public_permits")),
                "public_permits_2026_source": _fmt_text(quota.get("quota_source"), "fixture"),
                "applicants_2025": str(applications_by_hunt.get(hunt_code, 0)),
                "projected_applicants_2026": str(applications_by_hunt.get(hunt_code, 0)),
                "projected_applicants_2026_source": _fmt_text(row.get("applicant_pool_source"), "fixture"),
                "odds_2025": "",
                "odds_2026_projected": _fmt3(row.get("display_odds_pct")),
                "max_point_permits_2026": _fmt_int(quota.get("reserved_quota")),
                "random_permits_2026": _fmt_int(quota.get("random_quota")),
                "success_hunters": _fmt_int(success_hunters),
                "success_harvest": _fmt_int(success_harvest),
                "success_percent": success_percent,
                "missing_draw_data": "FALSE",
                "missing_projection": "FALSE",
                "missing_permits": "FALSE",
            }
        )
    rows.sort(key=lambda row: (row["hunt_code"], row["residency"], int(row["points"])))
    return rows


def _build_hunt_reference_rows(
    predictions: Sequence[Mapping[str, object]],
    metadata_by_hunt: Mapping[str, Mapping[str, str]],
    quotas_by_hunt: Mapping[str, Mapping[str, str]],
    applications_by_hunt: Mapping[str, int],
    harvest_by_hunt: Mapping[str, Mapping[str, str]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for row in predictions:
        grouped[_hunt_key(row.get("hunt_code"), row.get("residency"))].append(row)

    rows: list[dict[str, object]] = []
    for (hunt_code, residency), prediction_rows in grouped.items():
        pred = max(prediction_rows, key=lambda row: int(_num(row.get("points")) or 0))
        meta = dict(metadata_by_hunt.get(hunt_code, {}))
        quota = dict(quotas_by_hunt.get(hunt_code, {}))
        harvest = dict(harvest_by_hunt.get(hunt_code, {}))
        species = _fmt_text(meta.get("species") or pred.get("species"), "Unknown")
        hunt_name = _fmt_text(meta.get("unit_name") or meta.get("hunt_name") or f"{species} Fixture Hunt", "Fixture Hunt")
        weapon = _fmt_text(meta.get("weapon"), "Unknown")
        hunt_type = _fmt_text(meta.get("hunt_type"), "other")
        access_type = "Public" if _fmt_text(meta.get("permit_type"), "public").lower() == "public" else _fmt_text(meta.get("permit_type"), "Public")
        resident_quota = _fmt_int(quota.get("resident_quota"))
        nonresident_quota = _fmt_int(quota.get("nonresident_quota"))
        total_quota = _fmt_int(quota.get("total_public_permits"))
        guarantees = _fmt_int(pred.get("expected_cutoff_points") if _num(pred.get("expected_cutoff_points")) is not None else pred.get("points"))
        success_percent = _fmt3((_num(harvest.get("harvest_success")) or 0) * 100 if _num(harvest.get("harvest_success")) is not None else "")
        row = {
            "hunt_code": hunt_code,
            "residency": residency,
            "hunt_name": hunt_name,
            "species": species,
            "weapon": weapon,
            "hunt_type": hunt_type,
            "access_type": access_type,
            "public_permits_2025": total_quota,
            "public_permits_2026": total_quota,
            "permits_2025_res": resident_quota,
            "permits_2025_nr": nonresident_quota,
            "permits_2025_total": total_quota,
            "permits_2026_res": resident_quota,
            "permits_2026_nr": nonresident_quota,
            "permits_2026_total": total_quota,
            "applicants_2025": str(applications_by_hunt.get(hunt_code, 0)),
            "projected_applicants_2026": str(applications_by_hunt.get(hunt_code, 0)),
            "max_point_permits_2026": _fmt_int(quota.get("reserved_quota")),
            "random_permits_2026": _fmt_int(quota.get("random_quota")),
            "guaranteed_at_2026": guarantees,
            "delta_gap": "0",
            "trend": _fmt_text(pred.get("trend"), "YELLOW").upper(),
            "coverage_status": "FIXTURE",
            "coverage_reason": "fixture_rebuild",
            "bg_odds_pdf_page_index": "",
            "bg_odds_printed_page": "",
            "bg_odds_hunt_title": hunt_name,
            "has_bg_odds_page": "TRUE" if hunt_type != "other" else "FALSE",
            "rac_page": "",
            "rac_section": "",
            "source_pdf": "fixture",
            "harvest_hunters_2025": _fmt_int(harvest.get("permits_afield")),
            "harvest_2025": _fmt_int(harvest.get("harvest")),
            "harvest_success_percent_2025": success_percent,
            "harvest_average_days_2025": _fmt3(harvest.get("avg_days_hunted")),
            "harvest_satisfaction_2025": _fmt3(harvest.get("hunter_satisfaction")),
            "source_file_2026": "fixture",
            "link_key": f"{hunt_code}_{residency.upper()}",
            "antlerless_odds_sheet": "",
            "antlerless_odds_row_start": "",
            "antlerless_odds_title": "",
            "has_antlerless_odds_page": "TRUE" if "antlerless" in hunt_type.lower() else "FALSE",
            "has_any_odds_source": "TRUE",
        }
        rows.append(row)
    rows.sort(key=lambda row: (row["hunt_code"], row["residency"]))
    return rows


def rebuild_fixture_processed_csvs(
    source_root: Path | str = DEFAULT_FIXTURE_ROOT,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    draw_year: int = DEFAULT_PREDICTION_YEAR,
    iterations: int = 10000,
    seed: int = 2026,
    model_version: str = MODEL_VERSION,
    rule_version: str = RULE_VERSION,
    quota_source: str = "fixture",
    applicant_pool_source: str = "fixture",
) -> dict[str, Path]:
    source_root = Path(source_root)
    output_root = Path(output_root)
    tables = _read_fixture_tables(source_root)

    seed_rows = _prediction_rows(tables["seed_predictions"])
    quota_rows = tables["quotas"]
    metadata_rows = tables["hunt_metadata"]
    harvest_rows = tables["harvest_quality"]
    applications_rows = tables["applications"]

    quotas_by_hunt = { _fmt_text(row.get("hunt_code")).upper(): dict(row) for row in quota_rows }
    metadata_by_hunt = _metadata_lookup(metadata_rows)
    harvest_by_hunt = _harvest_lookup(harvest_rows)
    applications_by_hunt = _application_counts(applications_rows)

    draw_reality_path = output_root / DRAW_REALITY_FILENAME
    point_ladder_path = output_root / POINT_LADDER_FILENAME
    hunt_master_path = output_root / HUNT_MASTER_FILENAME
    hunt_reference_path = output_root / HUNT_REFERENCE_FILENAME

    draw_reality_path.parent.mkdir(parents=True, exist_ok=True)
    _ = iterations, seed
    write_materialized_rows = materialize_rows(
        seed_rows,
        legacy_rows=seed_rows,
        prediction_year=draw_year,
        model_version=model_version,
        rule_version=rule_version,
        quota_source=quota_source,
        applicant_pool_source=applicant_pool_source,
    )
    write_materialized_rows.sort(key=lambda row: (_fmt_text(row.get("hunt_code")).upper(), _fmt_text(row.get("residency")), int(_num(row.get("points")) or 0)))
    _write_csv(draw_reality_path, write_materialized_rows, list(write_materialized_rows[0].keys()) if write_materialized_rows else [])

    point_rows = _build_point_ladder_rows(write_materialized_rows, quotas_by_hunt, applications_by_hunt)
    _write_csv(point_ladder_path, point_rows, POINT_LADDER_HEADER)

    master_rows = _build_hunt_master_rows(write_materialized_rows, metadata_by_hunt, quotas_by_hunt, applications_by_hunt, harvest_by_hunt)
    _write_csv(hunt_master_path, master_rows, HUNT_MASTER_HEADER)

    reference_rows = _build_hunt_reference_rows(write_materialized_rows, metadata_by_hunt, quotas_by_hunt, applications_by_hunt, harvest_by_hunt)
    _write_csv(hunt_reference_path, reference_rows, HUNT_REFERENCE_HEADER)

    return {
        DRAW_REALITY_FILENAME: draw_reality_path,
        POINT_LADDER_FILENAME: point_ladder_path,
        HUNT_MASTER_FILENAME: hunt_master_path,
        HUNT_REFERENCE_FILENAME: hunt_reference_path,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild the Utah processed CSV contract from fixtures.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_FIXTURE_ROOT, help="Path to data/utah/fixtures")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Directory to write processed CSVs")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    outputs = rebuild_fixture_processed_csvs(args.source_root, args.output_root)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
