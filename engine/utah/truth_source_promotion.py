"""Promote 2026 RAC truth-source permit values into runtime CSV surfaces."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
TRUTH_SOURCE_LABEL = "2026_RAC_TRUTH_SOURCE"
TRUTH_SOURCE_AUTHORITY = "2026 RAC truth-source permit table"

REFERENCE_FILE = "hunt_unit_reference_linked.csv"
MASTER_FILE = "hunt_master_enriched.csv"
LADDER_FILE = "point_ladder_view.csv"
DRAW_REALITY_FILE = "draw_reality_engine.csv"
SUMMARY_FILE = "truth_source_promotion_summary.json"

METADATA_COLUMNS = [
    "permit_source",
    "quota_source",
    "truth_source_file",
    "truth_source_status",
    "data_quality_grade",
    "reason_codes",
    "hunt_category",
    "draw_model_class",
    "probability_model",
    "availability_status",
    "new_this_year",
]

RUNTIME_REASON_PROMOTED = "TRUTH_SOURCE_PROMOTED"
RUNTIME_REASON_ADDED = "TRUTH_SOURCE_ADDED_MISSING_RUNTIME_ROW"
RUNTIME_REASON_REPLACED = "TRUTH_SOURCE_REPLACED_STALE_RUNTIME_VALUE"
RUNTIME_REASON_AVAILABILITY_ONLY = "AVAILABILITY_ONLY_NO_DRAW_PROBABILITY"
RUNTIME_REASON_CONTROL_UNRESOLVED = "CONTROL_UNIT_NO_MATCHING_2026_PERMIT_ROW"


@dataclass(frozen=True)
class FamilyConfig:
    name: str
    truth_filename: str
    audit_csv: str
    audit_json: str
    mode: str
    species: str
    hunt_type: str
    access_type: str = "Public"
    hunt_category: str = ""
    points_max: int | None = None
    master_point_expanded: bool = True
    uses_split: bool = False
    official_lookup: str | None = None


FAMILY_CONFIGS: dict[str, FamilyConfig] = {
    "doe_pronghorn": FamilyConfig(
        name="doe_pronghorn",
        truth_filename="2026_rac_doe_pronghorn_permits.csv",
        audit_csv="doe_pronghorn_truth_source_audit.csv",
        audit_json="doe_pronghorn_truth_source_audit.json",
        mode="total_with_residency_split",
        species="Pronghorn",
        hunt_type="General Season",
        hunt_category="DOE_PRONGHORN",
        points_max=32,
        master_point_expanded=True,
        uses_split=True,
        official_lookup="data/pronghorn_hunt_table_official.json",
    ),
    "antlerless_deer": FamilyConfig(
        name="antlerless_deer",
        truth_filename="2026_rac_antlerless_deer_permits.csv",
        audit_csv="antlerless_deer_truth_source_audit.csv",
        audit_json="antlerless_deer_truth_source_audit.json",
        mode="modeled_total_only",
        species="Deer",
        hunt_type="General Season",
        hunt_category="ANTLERLESS_DEER",
        points_max=19,
        master_point_expanded=True,
    ),
    "standard_antlerless_elk": FamilyConfig(
        name="standard_antlerless_elk",
        truth_filename="2026_rac_antlerless_elk_permits.csv",
        audit_csv="antlerless_elk_truth_source_audit.csv",
        audit_json="antlerless_elk_truth_source_audit.json",
        mode="total_with_residency_split",
        species="Elk",
        hunt_type="General Season",
        hunt_category="ANTLERLESS_ELK",
        points_max=32,
        master_point_expanded=True,
        uses_split=True,
        official_lookup="data/elk_antlerless_hunt_table_official.json",
    ),
    "private_lands_antlerless_elk": FamilyConfig(
        name="private_lands_antlerless_elk",
        truth_filename="2026_rac_private_lands_only_antlerless_elk_permits.csv",
        audit_csv="private_lands_antlerless_elk_truth_source_audit.csv",
        audit_json="private_lands_antlerless_elk_truth_source_audit.json",
        mode="availability_total_only",
        species="Elk",
        hunt_type="Private Lands Only",
        hunt_category="PRIVATE_LANDS_ONLY_ANTLERLESS_ELK",
        points_max=32,
        master_point_expanded=False,
        official_lookup="data/elk_antlerless_hunt_table_official.json",
    ),
    "antlerless_elk_control_units": FamilyConfig(
        name="antlerless_elk_control_units",
        truth_filename="2026_rac_antlerless_elk_control_units.csv",
        audit_csv="antlerless_elk_control_unit_audit.csv",
        audit_json="antlerless_elk_control_unit_audit.json",
        mode="control_overlay",
        species="Elk",
        hunt_type="Control Unit Overlay",
        hunt_category="ANTLERLESS_ELK_CONTROL_UNIT",
        official_lookup="data/elk_antlerless_hunt_table_official.json",
    ),
    "antlerless_moose": FamilyConfig(
        name="antlerless_moose",
        truth_filename="2026_rac_antlerless_moose_permits.csv",
        audit_csv="antlerless_moose_truth_source_audit.csv",
        audit_json="antlerless_moose_truth_source_audit.json",
        mode="total_with_residency_split",
        species="Moose",
        hunt_type="Once-in-a-Lifetime",
        hunt_category="ANTLERLESS_MOOSE",
        points_max=32,
        master_point_expanded=True,
        uses_split=True,
    ),
    "ewe_rocky_sheep": FamilyConfig(
        name="ewe_rocky_sheep",
        truth_filename="2026_rac_ewe_rocky_mountain_bighorn_sheep_permits.csv",
        audit_csv="ewe_rocky_sheep_truth_source_audit.csv",
        audit_json="ewe_rocky_sheep_truth_source_audit.json",
        mode="total_with_residency_split",
        species="Bighorn Sheep",
        hunt_type="Once-in-a-Lifetime",
        hunt_category="EWE_ROCKY_MOUNTAIN_BIGHORN_SHEEP",
        points_max=32,
        master_point_expanded=True,
        uses_split=True,
    ),
}


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def normalize_code(value: object) -> str:
    return clean(value).upper()


def normalize_residency(value: object) -> str:
    return "Nonresident" if clean(value).lower() == "nonresident" else "Resident"


def normalize_draw_pool(value: object) -> str:
    return clean(value).lower() or "standard"


def normalize_int_text(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def normalize_dash_to_zero_for_delta(value: object) -> int:
    text = clean(value)
    if not text or text in {"-", "–", "—"}:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
        return list(reader.fieldnames or []), rows


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def ensure_columns(headers: list[str], required: Iterable[str]) -> list[str]:
    output = list(headers)
    for field in required:
        if field not in output:
            output.append(field)
    return output


def append_reason_codes(existing: str, *codes: str) -> str:
    current = [code for code in clean(existing).split("|") if code]
    for code in codes:
        if code and code not in current:
            current.append(code)
    return "|".join(current)


def make_group_key(code: str, residency: str, draw_pool: str = "standard") -> tuple[str, str, str]:
    return normalize_code(code), normalize_residency(residency), normalize_draw_pool(draw_pool)


def make_point_key(code: str, residency: str, points: object, draw_pool: str = "standard") -> tuple[str, str, str, str]:
    return normalize_code(code), normalize_residency(residency), clean(points), normalize_draw_pool(draw_pool)


def make_draw_key(code: str, residency: str, year: object, points: object, draw_pool: str = "standard") -> tuple[str, str, str, str, str]:
    return normalize_code(code), clean(year), normalize_residency(residency), clean(points), normalize_draw_pool(draw_pool)


def load_truth_source_csvs(truth_root: Path, families: list[str]) -> dict[str, list[dict[str, str]]]:
    truth = {}
    for family in families:
        config = FAMILY_CONFIGS[family]
        _, rows = read_csv(truth_root / config.truth_filename)
        truth[family] = rows
    return truth


def load_runtime_reference(processed_root: Path) -> tuple[list[str], list[dict[str, str]]]:
    return read_csv(processed_root / REFERENCE_FILE)


def load_runtime_master(processed_root: Path) -> tuple[list[str], list[dict[str, str]]]:
    return read_csv(processed_root / MASTER_FILE)


def load_runtime_ladder(processed_root: Path) -> tuple[list[str], list[dict[str, str]]]:
    return read_csv(processed_root / LADDER_FILE)


def load_runtime_draw_reality(processed_root: Path) -> tuple[list[str], list[dict[str, str]]]:
    return read_csv(processed_root / DRAW_REALITY_FILE)


def _load_official_lookup(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data.get("features", []) if isinstance(data, dict) else []
    lookup: dict[str, dict[str, str]] = {}
    for feature in features:
        attrs = feature.get("attributes", {})
        code = normalize_code(attrs.get("HUNT_NUMBER"))
        if not code:
            continue
        lookup[code] = {
            "boundary_id": clean(attrs.get("BOUNDARYID")),
            "hunt_name": clean(attrs.get("BOUNDARY_NAME")),
        }
    return lookup


def _load_hunt_planner_lookup(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        code = normalize_code(row.get("huntCode") or row.get("hunt_code"))
        if not code:
            continue
        lookup[code] = {
            "boundary_id": clean(row.get("boundaryId") or row.get("boundary_id")),
            "hunt_name": clean(row.get("unitName") or row.get("hunt_name")),
            "species": clean(row.get("species")),
            "weapon": clean(row.get("weapon")),
            "hunt_type": clean(row.get("huntType") or row.get("hunt_type")),
            "hunt_category": clean(row.get("huntCategory") or row.get("hunt_category")),
            "season_dates_2026": clean(row.get("seasonLabel") or row.get("season_dates_2026")),
        }
    return lookup


def _load_database_lookup(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    _, rows = read_csv(path)
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        code = normalize_code(row.get("hunt_code"))
        if not code:
            continue
        lookup[code] = {
            "boundary_id": clean(row.get("boundary_id")),
            "hunt_name": clean(row.get("hunt_name")),
            "species": clean(row.get("species")),
            "weapon": clean(row.get("weapon")),
            "hunt_type": clean(row.get("hunt_type")),
            "season_dates_2026": clean(row.get("season")),
        }
    return lookup


def build_hunt_metadata_lookup(processed_root: Path) -> dict[str, dict[str, str]]:
    database_lookup = _load_database_lookup(REPO_ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv")
    planner_lookup = _load_hunt_planner_lookup(REPO_ROOT / "utah-hunt-planner-master-all.md.txt")
    pronghorn_lookup = _load_official_lookup(REPO_ROOT / "data/pronghorn_hunt_table_official.json")
    elk_lookup = _load_official_lookup(REPO_ROOT / "data/elk_antlerless_hunt_table_official.json")

    metadata: dict[str, dict[str, str]] = {}
    for lookup in (planner_lookup, database_lookup, pronghorn_lookup, elk_lookup):
        for code, values in lookup.items():
            metadata.setdefault(code, {})
            for key, value in values.items():
                if clean(value) and not clean(metadata[code].get(key)):
                    metadata[code][key] = clean(value)

    for runtime_name in (REFERENCE_FILE, MASTER_FILE, LADDER_FILE, DRAW_REALITY_FILE):
        _, rows = read_csv(processed_root / runtime_name)
        for row in rows:
            code = normalize_code(row.get("hunt_code"))
            if not code:
                continue
            metadata.setdefault(code, {})
            for key in ("boundary_id", "hunt_name", "species", "weapon", "hunt_type", "access_type"):
                if clean(row.get(key)) and not clean(metadata[code].get(key)):
                    metadata[code][key] = clean(row.get(key))
    return metadata


def _is_normalized_zero_only(row: dict[str, str]) -> bool:
    note = f"{clean(row.get('source_note'))} {clean(row.get('source_document'))}".lower()
    return "normalized to zero" in note or "normalized from zero" in note or "normalized to zero for audit use" in note


def _truth_2025_fields(config: FamilyConfig, row: dict[str, str]) -> dict[str, str]:
    if _is_normalized_zero_only(row):
        return {"permits_2025_res": "", "permits_2025_nr": "", "permits_2025_total": ""}
    if config.uses_split:
        return {
            "permits_2025_res": normalize_int_text(row.get("permits_2025_res")),
            "permits_2025_nr": normalize_int_text(row.get("permits_2025_nr")),
            "permits_2025_total": normalize_int_text(row.get("permits_2025_total")),
        }
    return {
        "permits_2025_res": "",
        "permits_2025_nr": "",
        "permits_2025_total": normalize_int_text(row.get("permits_2025_total")),
    }


def _new_this_year_value(config: FamilyConfig, row: dict[str, str]) -> str:
    if config.mode == "control_overlay":
        return "YES" if clean(row.get("new_this_year")).upper() == "YES" else "NO"
    permits_2025_total = normalize_dash_to_zero_for_delta(
        row.get("permits_2025_total")
        or row.get("permits_2025_total_main")
        or row.get("permits_2025_res")
    )
    permits_2026_total = normalize_dash_to_zero_for_delta(row.get("permits_2026_total"))
    return "YES" if permits_2025_total == 0 and permits_2026_total > 0 else "NO"


def _truth_runtime_payload(config: FamilyConfig, row: dict[str, str], residency: str) -> dict[str, str]:
    permits_2025 = _truth_2025_fields(config, row)
    payload = {
        "hunt_code": normalize_code(row.get("hunt_code")),
        "hunt_name": clean(row.get("hunt_name") or row.get("permit_group")),
        "weapon": clean(row.get("weapon")),
        "season_dates_2026": clean(row.get("season_dates_2026")),
        "residency": normalize_residency(residency),
        "permits_2025_res": permits_2025["permits_2025_res"],
        "permits_2025_nr": permits_2025["permits_2025_nr"],
        "permits_2025_total": permits_2025["permits_2025_total"],
        "new_this_year": _new_this_year_value(config, row),
        "source_document": clean(row.get("source_document")),
        "source_note": clean(row.get("source_note")),
    }
    if config.mode == "total_with_residency_split":
        permits_2026_res = normalize_int_text(row.get("permits_2026_res"))
        permits_2026_nr = normalize_int_text(row.get("permits_2026_nr"))
        public = permits_2026_nr if residency == "Nonresident" else permits_2026_res
        payload.update(
            {
                "public_permits_2026": public,
                "permits_2026_res": permits_2026_res,
                "permits_2026_nr": permits_2026_nr,
                "permits_2026_total": normalize_int_text(row.get("permits_2026_total")),
                "permit_status": "FULL_SPLIT",
                "permit_allocation_type": "FULL_SPLIT",
            }
        )
    elif config.mode == "modeled_total_only":
        total = normalize_int_text(row.get("permits_2026_total"))
        payload.update(
            {
                "public_permits_2026": total,
                "permits_2026_res": "",
                "permits_2026_nr": "",
                "permits_2026_total": total,
                "permit_status": "TOTAL_ONLY",
                "permit_allocation_type": "TOTAL_ONLY",
            }
        )
    elif config.mode == "availability_total_only":
        total = normalize_int_text(row.get("permits_2026_total"))
        payload.update(
            {
                "public_permits_2026": "",
                "permits_2026_res": "",
                "permits_2026_nr": "",
                "permits_2026_total": total,
                "permit_status": "TOTAL_ONLY",
                "permit_allocation_type": "TOTAL_ONLY",
                "hunt_category": "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK",
                "draw_model_class": "AVAILABILITY_ONLY",
                "probability_model": "NONE",
                "availability_status": "AVAILABLE",
            }
        )
    else:
        raise ValueError(f"Unsupported truth payload mode for {config.name}: {config.mode}")
    return payload


def _family_truth_rows(config: FamilyConfig, truth_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if config.mode == "control_overlay":
        return [dict(row) for row in truth_rows]
    expanded: list[dict[str, str]] = []
    for row in truth_rows:
        for residency in ("Resident", "Nonresident"):
            expanded.append(_truth_runtime_payload(config, row, residency))
    return expanded


def _base_metadata_for_row(
    config: FamilyConfig,
    truth_row: dict[str, str],
    metadata_lookup: dict[str, dict[str, str]],
) -> dict[str, str]:
    code = truth_row["hunt_code"]
    metadata = dict(metadata_lookup.get(code, {}))
    hunt_name = clean(metadata.get("hunt_name")) or clean(truth_row.get("hunt_name"))
    return {
        "boundary_id": clean(metadata.get("boundary_id")),
        "hunt_name": hunt_name,
        "species": clean(metadata.get("species")) or config.species,
        "weapon": clean(truth_row.get("weapon")) or clean(metadata.get("weapon")),
        "hunt_type": clean(metadata.get("hunt_type")) or config.hunt_type,
        "access_type": clean(metadata.get("access_type")) or config.access_type,
        "season_dates_2026": clean(truth_row.get("season_dates_2026")) or clean(metadata.get("season_dates_2026")),
    }


def _apply_truth_metadata(
    row: dict[str, str],
    config: FamilyConfig,
    truth_row: dict[str, str],
    truth_file: str,
    reason_code: str,
) -> None:
    row["permit_source"] = TRUTH_SOURCE_LABEL
    row["quota_source"] = TRUTH_SOURCE_LABEL
    row["truth_source_file"] = truth_file
    row["truth_source_status"] = "MATCHED"
    row["data_quality_grade"] = "A"
    row["reason_codes"] = append_reason_codes(row.get("reason_codes", ""), reason_code)
    if config.hunt_category:
        row["hunt_category"] = clean(row.get("hunt_category")) or config.hunt_category
    if config.mode == "availability_total_only":
        row["draw_model_class"] = "AVAILABILITY_ONLY"
        row["probability_model"] = "NONE"
        row["availability_status"] = clean(row.get("availability_status")) or "AVAILABLE"
        row["reason_codes"] = append_reason_codes(row["reason_codes"], RUNTIME_REASON_AVAILABILITY_ONLY)
    row["new_this_year"] = clean(truth_row.get("new_this_year")) or clean(row.get("new_this_year"))


def _update_runtime_permit_fields(row: dict[str, str], truth_row: dict[str, str], truth_file: str) -> None:
    row["public_permits_2026"] = clean(truth_row.get("public_permits_2026"))
    row["public_permits_2026_source"] = TRUTH_SOURCE_LABEL
    row["permits_2026_res"] = clean(truth_row.get("permits_2026_res"))
    row["permits_2026_nr"] = clean(truth_row.get("permits_2026_nr"))
    row["permits_2026_total"] = clean(truth_row.get("permits_2026_total"))
    row["permits_2026_source"] = TRUTH_SOURCE_LABEL
    row["permits_year_res"] = clean(truth_row.get("permits_2026_res"))
    row["permits_year_nr"] = clean(truth_row.get("permits_2026_nr"))
    row["permits_year_total"] = clean(truth_row.get("permits_2026_total"))
    row["permit_status"] = clean(truth_row.get("permit_status"))
    row["permit_allocation_type"] = clean(truth_row.get("permit_allocation_type"))
    row["permit_source_authority"] = TRUTH_SOURCE_AUTHORITY
    row["permit_overlay_source"] = truth_file
    row["data_status"] = "COMPLETE"
    row["permit_source"] = TRUTH_SOURCE_LABEL
    row["quota_source"] = TRUTH_SOURCE_LABEL
    if "availability_status" in row and clean(truth_row.get("availability_status")):
        row["availability_status"] = clean(truth_row.get("availability_status"))
    if "permits_2025_res" in row and clean(truth_row.get("permits_2025_res")):
        row["permits_2025_res"] = clean(truth_row.get("permits_2025_res"))
    if "permits_2025_nr" in row and clean(truth_row.get("permits_2025_nr")):
        row["permits_2025_nr"] = clean(truth_row.get("permits_2025_nr"))
    if "permits_2025_total" in row and clean(truth_row.get("permits_2025_total")):
        row["permits_2025_total"] = clean(truth_row.get("permits_2025_total"))


def _matches_truth(row: dict[str, str], truth_row: dict[str, str], config: FamilyConfig) -> bool:
    checks = [
        clean(row.get("permits_2026_res")) == clean(truth_row.get("permits_2026_res")),
        clean(row.get("permits_2026_nr")) == clean(truth_row.get("permits_2026_nr")),
        clean(row.get("permits_2026_total")) == clean(truth_row.get("permits_2026_total")),
        clean(row.get("permit_status")) == clean(truth_row.get("permit_status")),
        clean(row.get("permit_allocation_type")) == clean(truth_row.get("permit_allocation_type")),
    ]
    if config.mode == "availability_total_only":
        checks.extend(
            [
                clean(row.get("public_permits_2026")) == "",
                clean(row.get("draw_model_class")) == "AVAILABILITY_ONLY",
                clean(row.get("probability_model")) == "NONE",
            ]
        )
    else:
        checks.append(clean(row.get("public_permits_2026")) == clean(truth_row.get("public_permits_2026")))
    return all(checks)


def _make_blank_row(headers: list[str]) -> dict[str, str]:
    return {header: "" for header in headers}


def _apply_common_runtime_identity(
    row: dict[str, str],
    config: FamilyConfig,
    truth_row: dict[str, str],
    metadata: dict[str, str],
) -> None:
    row["hunt_code"] = truth_row["hunt_code"]
    row["hunt_name"] = metadata["hunt_name"]
    row["weapon"] = metadata["weapon"]
    row["hunt_type"] = metadata["hunt_type"]
    if "species" in row:
        row["species"] = metadata["species"]
    if "access_type" in row:
        row["access_type"] = metadata["access_type"]
    if "boundary_id" in row:
        row["boundary_id"] = metadata["boundary_id"]
    if "draw_pool" in row:
        row["draw_pool"] = "standard"
    if "season" in row and metadata["season_dates_2026"]:
        row["season"] = metadata["season_dates_2026"]


def _build_reference_row(
    headers: list[str],
    config: FamilyConfig,
    truth_row: dict[str, str],
    metadata: dict[str, str],
    truth_file: str,
) -> dict[str, str]:
    row = _make_blank_row(headers)
    _apply_common_runtime_identity(row, config, truth_row, metadata)
    row["residency"] = truth_row["residency"]
    _update_runtime_permit_fields(row, truth_row, truth_file)
    if "access_type" in row and not clean(row.get("access_type")):
        row["access_type"] = config.access_type
    return row


def _build_master_rows(
    headers: list[str],
    config: FamilyConfig,
    truth_row: dict[str, str],
    metadata: dict[str, str],
    truth_file: str,
) -> list[dict[str, str]]:
    points = [""] if not config.master_point_expanded else [str(value) for value in range((config.points_max or 0) + 1)]
    rows: list[dict[str, str]] = []
    for point in points:
        row = _make_blank_row(headers)
        _apply_common_runtime_identity(row, config, truth_row, metadata)
        row["residency"] = truth_row["residency"]
        if "points" in row:
            row["points"] = point
        _update_runtime_permit_fields(row, truth_row, truth_file)
        if "missing_permits" in row:
            row["missing_permits"] = "FALSE"
        if point:
            if "missing_draw_data" in row:
                row["missing_draw_data"] = "TRUE"
            if "missing_projection" in row:
                row["missing_projection"] = "TRUE"
        rows.append(row)
    return rows


def _build_ladder_rows(
    headers: list[str],
    config: FamilyConfig,
    truth_row: dict[str, str],
    metadata: dict[str, str],
    truth_file: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for point in range((config.points_max or 0) + 1):
        row = _make_blank_row(headers)
        _apply_common_runtime_identity(row, config, truth_row, metadata)
        row["residency"] = truth_row["residency"]
        row["points"] = str(point)
        _update_runtime_permit_fields(row, truth_row, truth_file)
        if "missing_permits" in row:
            row["missing_permits"] = "FALSE"
        rows.append(row)
    return rows


def _build_draw_row(
    headers: list[str],
    config: FamilyConfig,
    truth_row: dict[str, str],
    metadata: dict[str, str],
    truth_file: str,
) -> dict[str, str]:
    row = _make_blank_row(headers)
    row["hunt_code"] = truth_row["hunt_code"]
    row["year"] = "2026"
    row["residency"] = truth_row["residency"]
    row["points"] = "0"
    row["hunt_name"] = metadata["hunt_name"]
    if "boundary_id" in row:
        row["boundary_id"] = metadata["boundary_id"]
    row["source_file"] = Path(truth_file).name
    row["draw_pool"] = "standard"
    row["status"] = "NO_DRAW_ODDS_SOURCE"
    _update_runtime_permit_fields(row, truth_row, truth_file)
    return row


def _promote_rows_by_key(
    rows: list[dict[str, str]],
    key_to_truth: dict[tuple[str, str, str], dict[str, str]],
    config: FamilyConfig,
    truth_file: str,
) -> tuple[int, int]:
    corrected = 0
    unchanged = 0
    for row in rows:
        key = make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool"))
        truth_row = key_to_truth.get(key)
        if not truth_row:
            continue
        if _matches_truth(row, truth_row, config):
            _apply_truth_metadata(row, config, truth_row, truth_file, RUNTIME_REASON_PROMOTED)
            unchanged += 1
            continue
        _update_runtime_permit_fields(row, truth_row, truth_file)
        _apply_truth_metadata(row, config, truth_row, truth_file, RUNTIME_REASON_REPLACED)
        corrected += 1
    return corrected, unchanged


def _promote_point_rows_by_key(
    rows: list[dict[str, str]],
    key_to_truth: dict[tuple[str, str, str], dict[str, str]],
    config: FamilyConfig,
    truth_file: str,
) -> tuple[int, int]:
    corrected = 0
    unchanged = 0
    for row in rows:
        key = make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool"))
        truth_row = key_to_truth.get(key)
        if not truth_row:
            continue
        if _matches_truth(row, truth_row, config):
            _apply_truth_metadata(row, config, truth_row, truth_file, RUNTIME_REASON_PROMOTED)
            unchanged += 1
            continue
        _update_runtime_permit_fields(row, truth_row, truth_file)
        _apply_truth_metadata(row, config, truth_row, truth_file, RUNTIME_REASON_REPLACED)
        corrected += 1
    return corrected, unchanged


def _promote_draw_rows(
    rows: list[dict[str, str]],
    key_to_truth: dict[tuple[str, str, str], dict[str, str]],
    config: FamilyConfig,
    truth_file: str,
) -> tuple[int, int]:
    corrected = 0
    unchanged = 0
    for row in rows:
        key = make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool"))
        truth_row = key_to_truth.get(key)
        if not truth_row:
            continue
        if _matches_truth(row, truth_row, config):
            _apply_truth_metadata(row, config, truth_row, truth_file, RUNTIME_REASON_PROMOTED)
            unchanged += 1
            continue
        _update_runtime_permit_fields(row, truth_row, truth_file)
        _apply_truth_metadata(row, config, truth_row, truth_file, RUNTIME_REASON_REPLACED)
        if not clean(row.get("status")):
            row["status"] = "NO_DRAW_ODDS_SOURCE"
        corrected += 1
    return corrected, unchanged


def _add_missing_reference_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    key_to_truth: dict[tuple[str, str, str], dict[str, str]],
    config: FamilyConfig,
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> int:
    existing = {make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool")) for row in rows}
    added = 0
    for key, truth_row in key_to_truth.items():
        if key in existing:
            continue
        metadata = _base_metadata_for_row(config, truth_row, metadata_lookup)
        new_row = _build_reference_row(headers, config, truth_row, metadata, truth_file)
        _apply_truth_metadata(new_row, config, truth_row, truth_file, RUNTIME_REASON_ADDED)
        rows.append(new_row)
        added += 1
    return added


def _add_missing_master_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    key_to_truth: dict[tuple[str, str, str], dict[str, str]],
    config: FamilyConfig,
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> int:
    added = 0
    if config.master_point_expanded:
        existing = {make_point_key(row.get("hunt_code"), row.get("residency"), row.get("points"), row.get("draw_pool")) for row in rows}
        for key, truth_row in key_to_truth.items():
            metadata = _base_metadata_for_row(config, truth_row, metadata_lookup)
            for new_row in _build_master_rows(headers, config, truth_row, metadata, truth_file):
                point_key = make_point_key(new_row.get("hunt_code"), new_row.get("residency"), new_row.get("points"), new_row.get("draw_pool"))
                if point_key in existing:
                    continue
                _apply_truth_metadata(new_row, config, truth_row, truth_file, RUNTIME_REASON_ADDED)
                rows.append(new_row)
                existing.add(point_key)
                added += 1
    else:
        existing = {make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool")) for row in rows}
        for key, truth_row in key_to_truth.items():
            if key in existing:
                continue
            metadata = _base_metadata_for_row(config, truth_row, metadata_lookup)
            for new_row in _build_master_rows(headers, config, truth_row, metadata, truth_file):
                _apply_truth_metadata(new_row, config, truth_row, truth_file, RUNTIME_REASON_ADDED)
                rows.append(new_row)
                added += 1
    return added


def _add_missing_ladder_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    key_to_truth: dict[tuple[str, str, str], dict[str, str]],
    config: FamilyConfig,
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> int:
    existing = {make_point_key(row.get("hunt_code"), row.get("residency"), row.get("points"), row.get("draw_pool")) for row in rows}
    added = 0
    for key, truth_row in key_to_truth.items():
        metadata = _base_metadata_for_row(config, truth_row, metadata_lookup)
        for new_row in _build_ladder_rows(headers, config, truth_row, metadata, truth_file):
            point_key = make_point_key(new_row.get("hunt_code"), new_row.get("residency"), new_row.get("points"), new_row.get("draw_pool"))
            if point_key in existing:
                continue
            _apply_truth_metadata(new_row, config, truth_row, truth_file, RUNTIME_REASON_ADDED)
            rows.append(new_row)
            existing.add(point_key)
            added += 1
    return added


def _add_missing_draw_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    key_to_truth: dict[tuple[str, str, str], dict[str, str]],
    config: FamilyConfig,
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> int:
    existing_groups = {make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool")) for row in rows}
    added = 0
    for key, truth_row in key_to_truth.items():
        if key in existing_groups:
            continue
        metadata = _base_metadata_for_row(config, truth_row, metadata_lookup)
        new_row = _build_draw_row(headers, config, truth_row, metadata, truth_file)
        _apply_truth_metadata(new_row, config, truth_row, truth_file, RUNTIME_REASON_ADDED)
        rows.append(new_row)
        existing_groups.add(key)
        added += 1
    return added


def promote_truth_to_runtime_reference(
    headers: list[str],
    rows: list[dict[str, str]],
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> dict[str, int]:
    key_to_truth = {make_group_key(row["hunt_code"], row["residency"]): row for row in truth_rows}
    corrected, unchanged = _promote_rows_by_key(rows, key_to_truth, config, truth_file)
    added = _add_missing_reference_rows(headers, rows, key_to_truth, config, metadata_lookup, truth_file)
    return {"corrected": corrected, "added": added, "unchanged": unchanged}


def promote_truth_to_hunt_master(
    headers: list[str],
    rows: list[dict[str, str]],
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> dict[str, int]:
    key_to_truth = {make_group_key(row["hunt_code"], row["residency"]): row for row in truth_rows}
    corrected, unchanged = _promote_point_rows_by_key(rows, key_to_truth, config, truth_file)
    added = _add_missing_master_rows(headers, rows, key_to_truth, config, metadata_lookup, truth_file)
    return {"corrected": corrected, "added": added, "unchanged": unchanged}


def promote_truth_to_point_ladder(
    headers: list[str],
    rows: list[dict[str, str]],
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> dict[str, int]:
    key_to_truth = {make_group_key(row["hunt_code"], row["residency"]): row for row in truth_rows}
    corrected, unchanged = _promote_point_rows_by_key(rows, key_to_truth, config, truth_file)
    added = _add_missing_ladder_rows(headers, rows, key_to_truth, config, metadata_lookup, truth_file)
    return {"corrected": corrected, "added": added, "unchanged": unchanged}


def promote_truth_to_draw_reality(
    headers: list[str],
    rows: list[dict[str, str]],
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
    metadata_lookup: dict[str, dict[str, str]],
    truth_file: str,
) -> dict[str, int]:
    key_to_truth = {make_group_key(row["hunt_code"], row["residency"]): row for row in truth_rows}
    corrected, unchanged = _promote_draw_rows(rows, key_to_truth, config, truth_file)
    added = _add_missing_draw_rows(headers, rows, key_to_truth, config, metadata_lookup, truth_file)
    return {"corrected": corrected, "added": added, "unchanged": unchanged}


def _audit_runtime_surface(
    rows: list[dict[str, str]],
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
    point_expanded: bool,
) -> tuple[int, list[str]]:
    mismatches = 0
    mismatch_codes: list[str] = []
    if point_expanded:
        grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool"))].append(row)
        for truth_row in truth_rows:
            key = make_group_key(truth_row["hunt_code"], truth_row["residency"])
            group_rows = grouped.get(key, [])
            if not group_rows or any(not _matches_truth(row, truth_row, config) for row in group_rows):
                mismatches += 1
                mismatch_codes.append(truth_row["hunt_code"])
    else:
        indexed = {make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool")): row for row in rows}
        for truth_row in truth_rows:
            row = indexed.get(make_group_key(truth_row["hunt_code"], truth_row["residency"]))
            if row is None or not _matches_truth(row, truth_row, config):
                mismatches += 1
                mismatch_codes.append(truth_row["hunt_code"])
    return mismatches, sorted(set(mismatch_codes))


def _audit_draw_reality_surface(
    rows: list[dict[str, str]],
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
) -> tuple[int, list[str]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool"))].append(row)
    mismatches = 0
    mismatch_codes: list[str] = []
    for truth_row in truth_rows:
        group = grouped.get(make_group_key(truth_row["hunt_code"], truth_row["residency"]))
        if not group or any(not _matches_truth(row, truth_row, config) for row in group):
            mismatches += 1
            mismatch_codes.append(truth_row["hunt_code"])
    return mismatches, sorted(set(mismatch_codes))


def _structural_duplicate_errors(
    reference_rows: list[dict[str, str]],
    master_rows: list[dict[str, str]],
    ladder_rows: list[dict[str, str]],
    draw_rows: list[dict[str, str]],
    truth_rows: list[dict[str, str]],
) -> int:
    truth_by_code = {row["hunt_code"]: row for row in truth_rows if row["residency"] == "Resident"}

    def count_errors(rows: list[dict[str, str]], point_expanded: bool) -> int:
        grouped: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            code = normalize_code(row.get("hunt_code"))
            if code in truth_by_code:
                grouped[code][normalize_residency(row.get("residency"))].append(row)
        errors = 0
        for code, by_residency in grouped.items():
            truth_total = clean(truth_by_code[code].get("permits_2026_total"))
            resident_rows = by_residency.get("Resident", [])
            nonresident_rows = by_residency.get("Nonresident", [])
            if not resident_rows or not nonresident_rows:
                continue
            if any(clean(row.get("public_permits_2026")) == truth_total for row in resident_rows + nonresident_rows if truth_total):
                errors += 1
        return errors

    return (
        count_errors(reference_rows, False)
        + count_errors(master_rows, False)
        + count_errors(ladder_rows, True)
        + count_errors(draw_rows, False)
    )


def compare_truth_to_runtime(
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
    reference_rows: list[dict[str, str]],
    master_rows: list[dict[str, str]],
    ladder_rows: list[dict[str, str]],
    draw_rows: list[dict[str, str]],
) -> dict[str, object]:
    if config.mode == "control_overlay":
        return {}
    reference_mismatches, reference_codes = _audit_runtime_surface(reference_rows, config, truth_rows, False)
    master_mismatches, master_codes = _audit_runtime_surface(master_rows, config, truth_rows, config.master_point_expanded)
    ladder_mismatches, ladder_codes = _audit_runtime_surface(ladder_rows, config, truth_rows, True)
    draw_mismatches, draw_codes = _audit_draw_reality_surface(draw_rows, config, truth_rows)
    mismatch_codes = sorted(set(reference_codes + master_codes + ladder_codes + draw_codes))
    summary: dict[str, object] = {
        "all_2026_repo_matches_truth": not mismatch_codes,
        "repo_mismatch_row_count": len(mismatch_codes),
        "repo_mismatch_hunt_codes": mismatch_codes,
        "surface_mismatch_counts": {
            "reference": reference_mismatches,
            "master": master_mismatches,
            "ladder": ladder_mismatches,
            "draw_reality": draw_mismatches,
        },
    }
    if config.mode == "availability_total_only":
        summary["structural_duplicated_by_residency_errors"] = _structural_duplicate_errors(
            reference_rows,
            master_rows,
            ladder_rows,
            draw_rows,
            truth_rows,
        )
    return summary


def _significance_label(delta: int) -> str:
    absolute = abs(delta)
    if absolute > 20:
        return "MAJOR"
    if absolute > 10:
        return "SIGNIFICANT"
    if absolute > 0:
        return "MINOR"
    return "UNCHANGED"


def write_audit_csv(
    output_path: Path,
    config: FamilyConfig,
    truth_rows: list[dict[str, str]],
    reference_rows: list[dict[str, str]],
    master_rows: list[dict[str, str]],
    ladder_rows: list[dict[str, str]],
    draw_rows: list[dict[str, str]],
) -> None:
    if config.mode == "control_overlay":
        return
    reference_index = {make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool")): row for row in reference_rows}
    master_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    ladder_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    draw_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for collection, target in ((master_rows, master_groups), (ladder_rows, ladder_groups), (draw_rows, draw_groups)):
        for row in collection:
            target[make_group_key(row.get("hunt_code"), row.get("residency"), row.get("draw_pool"))].append(row)

    headers = [
        "family",
        "hunt_code",
        "residency",
        "hunt_name",
        "weapon",
        "season_dates_2026",
        "permits_2025_total",
        "permits_2026_total",
        "permit_delta_total",
        "significance",
        "reference_match",
        "master_match",
        "ladder_match",
        "draw_reality_match",
        "repo_public_permits_2026",
        "repo_permits_2026_total",
        "source_document",
        "source_note",
    ]
    audit_rows: list[dict[str, str]] = []
    for truth_row in truth_rows:
        key = make_group_key(truth_row["hunt_code"], truth_row["residency"])
        reference_row = reference_index.get(key)
        master_match = bool(master_groups.get(key)) and all(_matches_truth(row, truth_row, config) for row in master_groups[key])
        ladder_match = bool(ladder_groups.get(key)) and all(_matches_truth(row, truth_row, config) for row in ladder_groups[key])
        draw_match = bool(draw_groups.get(key)) and all(_matches_truth(row, truth_row, config) for row in draw_groups[key])
        reference_match = reference_row is not None and _matches_truth(reference_row, truth_row, config)
        delta = normalize_dash_to_zero_for_delta(truth_row.get("permits_2026_total")) - normalize_dash_to_zero_for_delta(
            truth_row.get("permits_2025_total")
        )
        audit_rows.append(
            {
                "family": config.name,
                "hunt_code": truth_row["hunt_code"],
                "residency": truth_row["residency"],
                "hunt_name": truth_row["hunt_name"],
                "weapon": truth_row["weapon"],
                "season_dates_2026": truth_row["season_dates_2026"],
                "permits_2025_total": truth_row["permits_2025_total"],
                "permits_2026_total": truth_row["permits_2026_total"],
                "permit_delta_total": str(delta),
                "significance": _significance_label(delta),
                "reference_match": "TRUE" if reference_match else "FALSE",
                "master_match": "TRUE" if master_match else "FALSE",
                "ladder_match": "TRUE" if ladder_match else "FALSE",
                "draw_reality_match": "TRUE" if draw_match else "FALSE",
                "repo_public_permits_2026": clean(reference_row.get("public_permits_2026")) if reference_row else "",
                "repo_permits_2026_total": clean(reference_row.get("permits_2026_total")) if reference_row else "",
                "source_document": truth_row.get("source_document", ""),
                "source_note": truth_row.get("source_note", ""),
            }
        )
    write_csv(output_path, headers, audit_rows)


def write_audit_json(
    output_path: Path,
    config: FamilyConfig,
    source_file: Path,
    truth_source_rows: list[dict[str, str]],
    truth_rows: list[dict[str, str]],
    comparison: dict[str, object],
) -> None:
    if config.mode == "control_overlay":
        return
    group_changes = []
    notable_findings = []
    grouped = defaultdict(lambda: {"permit_group": "", "permits_2025_total": 0, "permits_2026_total": 0})
    for row in truth_source_rows:
        name = clean(row.get("hunt_name") or row.get("permit_group"))
        grouped[name]["permit_group"] = name
        grouped[name]["permits_2025_total"] += normalize_dash_to_zero_for_delta(row.get("permits_2025_total"))
        grouped[name]["permits_2026_total"] += normalize_dash_to_zero_for_delta(row.get("permits_2026_total"))
    for values in grouped.values():
        delta = values["permits_2026_total"] - values["permits_2025_total"]
        values["permit_delta_total"] = delta
        values["significance"] = _significance_label(delta)
        group_changes.append(values)
        if values["significance"] != "UNCHANGED":
            notable_findings.append(
                f"{values['permit_group']} changed from {values['permits_2025_total']} to {values['permits_2026_total']} total permits."
            )

    summary: dict[str, object] = {
        "source_file": source_file.as_posix(),
        "truth_rows": len(truth_source_rows),
        "unique_hunt_codes": len({normalize_code(row.get('hunt_code')) for row in truth_source_rows}),
        "grand_total_2025": sum(normalize_dash_to_zero_for_delta(row.get("permits_2025_total")) for row in truth_source_rows),
        "grand_total_2026": sum(normalize_dash_to_zero_for_delta(row.get("permits_2026_total")) for row in truth_source_rows),
        "grand_total_delta": sum(normalize_dash_to_zero_for_delta(row.get("permits_2026_total")) for row in truth_source_rows)
        - sum(normalize_dash_to_zero_for_delta(row.get("permits_2025_total")) for row in truth_source_rows),
        "group_changes": sorted(group_changes, key=lambda item: abs(item["permit_delta_total"]), reverse=True),
        "notable_findings": notable_findings,
        **comparison,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_control_unit_audits(
    processed_root: Path,
    truth_rows: list[dict[str, str]],
    standard_truth_source_rows: list[dict[str, str]],
    private_truth_source_rows: list[dict[str, str]],
) -> dict[str, object]:
    standard_by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    private_by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in standard_truth_source_rows:
        standard_by_name[clean(row.get("hunt_name"))].append(row)
    for row in private_truth_source_rows:
        private_by_name[clean(row.get("hunt_name"))].append(row)

    matches = []
    unmatched = []
    for row in truth_rows:
        control_unit = clean(row.get("control_unit"))
        standard_matches = standard_by_name.get(control_unit, [])
        private_matches = private_by_name.get(control_unit, [])
        match_record = {
            "control_unit": control_unit,
            "new_this_year": "YES" if clean(row.get("new_this_year")).upper() == "YES" else "NO",
            "matched_any_truth_rows": bool(standard_matches or private_matches),
            "standard_hunt_code_count": len({normalize_code(item.get("hunt_code")) for item in standard_matches}),
            "private_lands_hunt_code_count": len({normalize_code(item.get("hunt_code")) for item in private_matches}),
            "matched_hunt_codes": sorted(
                {normalize_code(item.get("hunt_code")) for item in standard_matches + private_matches}
            ),
            "standard_hunt_codes": sorted({normalize_code(item.get("hunt_code")) for item in standard_matches}),
            "private_lands_hunt_codes": sorted({normalize_code(item.get("hunt_code")) for item in private_matches}),
            "season_examples": sorted(
                {
                    clean(item.get("season_dates_2026"))
                    for item in standard_matches + private_matches
                    if clean(item.get("season_dates_2026"))
                }
            ),
            "truth_permits_2026_total_across_matches": sum(
                normalize_dash_to_zero_for_delta(item.get("permits_2026_total"))
                for item in standard_matches + private_matches
            ),
        }
        if not match_record["matched_any_truth_rows"]:
            unmatched.append(control_unit)
        matches.append(match_record)

    csv_headers = [
        "control_unit",
        "new_this_year",
        "matched_any_truth_rows",
        "standard_hunt_code_count",
        "private_lands_hunt_code_count",
        "matched_hunt_codes",
        "standard_hunt_codes",
        "private_lands_hunt_codes",
        "season_examples",
        "truth_permits_2026_total_across_matches",
    ]
    csv_rows = []
    for match in matches:
        csv_rows.append(
            {
                **match,
                "matched_any_truth_rows": "TRUE" if match["matched_any_truth_rows"] else "FALSE",
                "matched_hunt_codes": "|".join(match["matched_hunt_codes"]),
                "standard_hunt_codes": "|".join(match["standard_hunt_codes"]),
                "private_lands_hunt_codes": "|".join(match["private_lands_hunt_codes"]),
                "season_examples": "|".join(match["season_examples"]),
            }
        )
    write_csv(processed_root / "antlerless_elk_control_unit_audit.csv", csv_headers, csv_rows)

    summary = {
        "source_file": "pipeline/RAW/hunt_unit_database/2026/csv/2026_rac_antlerless_elk_control_units.csv",
        "control_unit_count": len(truth_rows),
        "matched_control_unit_count": sum(1 for match in matches if match["matched_any_truth_rows"]),
        "unmatched_control_units": unmatched,
        "new_this_year_control_units": [match["control_unit"] for match in matches if match["new_this_year"] == "YES"],
        "control_unit_matches": matches,
        "notable_findings": [
            "Box Elder, Grouse Creek maps to standard antlerless elk hunt code EA1287 and is marked new this year.",
            "Henry Mtns does not map to any currently normalized 2026 antlerless elk or private-lands-only antlerless elk truth rows.",
        ],
    }
    (processed_root / "antlerless_elk_control_unit_audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def write_runtime_outputs(
    processed_root: Path,
    reference_headers: list[str],
    reference_rows: list[dict[str, str]],
    master_headers: list[str],
    master_rows: list[dict[str, str]],
    ladder_headers: list[str],
    ladder_rows: list[dict[str, str]],
    draw_headers: list[str],
    draw_rows: list[dict[str, str]],
) -> None:
    write_csv(processed_root / REFERENCE_FILE, reference_headers, sorted(reference_rows, key=lambda row: (normalize_code(row.get("hunt_code")), normalize_residency(row.get("residency")), normalize_draw_pool(row.get("draw_pool")))))
    write_csv(processed_root / MASTER_FILE, master_headers, sorted(master_rows, key=lambda row: (normalize_code(row.get("hunt_code")), normalize_residency(row.get("residency")), clean(row.get("points")), normalize_draw_pool(row.get("draw_pool")))))
    write_csv(processed_root / LADDER_FILE, ladder_headers, sorted(ladder_rows, key=lambda row: (normalize_code(row.get("hunt_code")), normalize_residency(row.get("residency")), clean(row.get("points")), normalize_draw_pool(row.get("draw_pool")))))
    write_csv(processed_root / DRAW_REALITY_FILE, draw_headers, sorted(draw_rows, key=lambda row: (normalize_code(row.get("hunt_code")), clean(row.get("year")), normalize_residency(row.get("residency")), clean(row.get("points")), normalize_draw_pool(row.get("draw_pool")))))


def write_summary_report(output_path: Path, summary: dict[str, object]) -> None:
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _prepare_headers(*headers: list[str]) -> list[list[str]]:
    required = METADATA_COLUMNS + ["public_permits_2026_source", "permits_2026_source"]
    return [ensure_columns(header_list, required) for header_list in headers]


def _family_truth_file(truth_root: Path, config: FamilyConfig) -> Path:
    return truth_root / config.truth_filename


def _locked_family_summary(processed_root: Path, family: str) -> dict[str, object]:
    config = FAMILY_CONFIGS[family]
    path = processed_root / config.audit_json
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_promotion(
    truth_root: Path,
    processed_root: Path,
    families: list[str],
    promote: bool,
    write_audits: bool,
) -> tuple[int, dict[str, object]]:
    reference_headers, reference_rows = load_runtime_reference(processed_root)
    master_headers, master_rows = load_runtime_master(processed_root)
    ladder_headers, ladder_rows = load_runtime_ladder(processed_root)
    draw_headers, draw_rows = load_runtime_draw_reality(processed_root)
    reference_headers, master_headers, ladder_headers, draw_headers = _prepare_headers(
        reference_headers, master_headers, ladder_headers, draw_headers
    )

    metadata_lookup = build_hunt_metadata_lookup(processed_root)
    truth_sources = load_truth_source_csvs(truth_root, families)

    family_summaries: dict[str, object] = {}
    exit_code = 0

    standard_truth_source_rows = truth_sources.get("standard_antlerless_elk", [])
    private_truth_source_rows = truth_sources.get("private_lands_antlerless_elk", [])

    for family in families:
        config = FAMILY_CONFIGS[family]
        truth_source_rows = truth_sources[family]
        if config.mode == "control_overlay":
            summary = _write_control_unit_audits(processed_root, truth_source_rows, standard_truth_source_rows, private_truth_source_rows)
            family_summaries[family] = {
                "truth_rows": len(truth_source_rows),
                "runtime_rows_corrected": 0,
                "runtime_rows_added": 0,
                "runtime_rows_unchanged": 0,
                "mismatch_rows_before_promotion": 0,
                "mismatch_rows_after_promotion": 0,
                "availability_only_rows": 0,
                "unresolved_overlay_rows": len(summary["unmatched_control_units"]),
                "warnings": summary["unmatched_control_units"],
            }
            continue

        truth_rows = _family_truth_rows(config, truth_source_rows)
        truth_file = _family_truth_file(truth_root, config).as_posix()
        before = compare_truth_to_runtime(config, truth_rows, reference_rows, master_rows, ladder_rows, draw_rows)

        corrected = {"reference": 0, "master": 0, "ladder": 0, "draw_reality": 0}
        added = {"reference": 0, "master": 0, "ladder": 0, "draw_reality": 0}
        unchanged = {"reference": 0, "master": 0, "ladder": 0, "draw_reality": 0}

        if promote:
            reference_result = promote_truth_to_runtime_reference(reference_headers, reference_rows, config, truth_rows, metadata_lookup, truth_file)
            master_result = promote_truth_to_hunt_master(master_headers, master_rows, config, truth_rows, metadata_lookup, truth_file)
            ladder_result = promote_truth_to_point_ladder(ladder_headers, ladder_rows, config, truth_rows, metadata_lookup, truth_file)
            draw_result = promote_truth_to_draw_reality(draw_headers, draw_rows, config, truth_rows, metadata_lookup, truth_file)
            corrected.update(
                {
                    "reference": reference_result["corrected"],
                    "master": master_result["corrected"],
                    "ladder": ladder_result["corrected"],
                    "draw_reality": draw_result["corrected"],
                }
            )
            added.update(
                {
                    "reference": reference_result["added"],
                    "master": master_result["added"],
                    "ladder": ladder_result["added"],
                    "draw_reality": draw_result["added"],
                }
            )
            unchanged.update(
                {
                    "reference": reference_result["unchanged"],
                    "master": master_result["unchanged"],
                    "ladder": ladder_result["unchanged"],
                    "draw_reality": draw_result["unchanged"],
                }
            )

        after = compare_truth_to_runtime(config, truth_rows, reference_rows, master_rows, ladder_rows, draw_rows)
        if write_audits:
            write_audit_csv(processed_root / config.audit_csv, config, truth_rows, reference_rows, master_rows, ladder_rows, draw_rows)
            write_audit_json(processed_root / config.audit_json, config, _family_truth_file(truth_root, config), truth_source_rows, truth_rows, after)

        warnings: list[str] = []
        if config.mode == "availability_total_only" and int(after.get("structural_duplicated_by_residency_errors", 0)) > 0:
            warnings.append("duplicated_by_residency_errors")

        family_summaries[family] = {
            "truth_rows": len(truth_source_rows),
            "runtime_rows_corrected": sum(corrected.values()),
            "runtime_rows_added": sum(added.values()),
            "runtime_rows_unchanged": sum(unchanged.values()),
            "mismatch_rows_before_promotion": before.get("repo_mismatch_row_count", 0),
            "mismatch_rows_after_promotion": after.get("repo_mismatch_row_count", 0),
            "availability_only_rows": len(truth_rows) if config.mode == "availability_total_only" else 0,
            "unresolved_overlay_rows": 0,
            "warnings": warnings,
        }
        family_summaries[family]["surface_mismatch_counts"] = after.get("surface_mismatch_counts", {})
        if config.mode == "availability_total_only":
            family_summaries[family]["structural_duplicated_by_residency_errors"] = after.get(
                "structural_duplicated_by_residency_errors", 0
            )

        if after.get("repo_mismatch_row_count", 0) > 0:
            exit_code = 1
        if config.mode == "availability_total_only" and int(after.get("structural_duplicated_by_residency_errors", 0)) > 0:
            exit_code = 1

    if promote:
        write_runtime_outputs(
            processed_root,
            reference_headers,
            reference_rows,
            master_headers,
            master_rows,
            ladder_headers,
            ladder_rows,
            draw_headers,
            draw_rows,
        )

    summary = {
        "truth_root": truth_root.as_posix(),
        "processed_root": processed_root.as_posix(),
        "families": family_summaries,
    }
    write_summary_report(processed_root / SUMMARY_FILE, summary)
    return exit_code, summary


def _print_summary(summary: dict[str, object]) -> None:
    families = summary.get("families", {})
    for family, values in families.items():
        print(
            f"{family}: truth_rows={values.get('truth_rows', 0)} "
            f"corrected={values.get('runtime_rows_corrected', 0)} "
            f"added={values.get('runtime_rows_added', 0)} "
            f"unchanged={values.get('runtime_rows_unchanged', 0)} "
            f"before={values.get('mismatch_rows_before_promotion', 0)} "
            f"after={values.get('mismatch_rows_after_promotion', 0)} "
            f"availability_only={values.get('availability_only_rows', 0)} "
            f"unresolved={values.get('unresolved_overlay_rows', 0)} "
            f"warnings={','.join(values.get('warnings', [])) or 'none'}"
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote 2026 RAC truth-source permit values into runtime CSVs.")
    parser.add_argument("--truth-root", required=True, help="Directory containing normalized 2026 RAC truth-source CSVs.")
    parser.add_argument("--processed-root", required=True, help="Directory containing runtime processed CSVs.")
    parser.add_argument("--families", nargs="+", required=True, choices=sorted(FAMILY_CONFIGS), help="Families to audit or promote.")
    parser.add_argument("--promote", action="store_true", help="Write corrected runtime rows.")
    parser.add_argument("--write-audits", action="store_true", help="Rewrite audit CSV/JSON outputs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    truth_root = Path(args.truth_root)
    processed_root = Path(args.processed_root)
    if not truth_root.exists():
        print(f"Missing truth root: {truth_root}")
        return 1
    for runtime_file in (REFERENCE_FILE, MASTER_FILE, LADDER_FILE, DRAW_REALITY_FILE):
        if not (processed_root / runtime_file).exists():
            print(f"Missing runtime file: {processed_root / runtime_file}")
            return 1
    for family in args.families:
        if not (truth_root / FAMILY_CONFIGS[family].truth_filename).exists():
            print(f"Missing truth source file: {truth_root / FAMILY_CONFIGS[family].truth_filename}")
            return 1
    exit_code, summary = run_promotion(truth_root, processed_root, args.families, args.promote, args.write_audits)
    _print_summary(summary)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
