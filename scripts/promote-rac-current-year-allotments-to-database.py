"""Promote direct RAC current-year allotments into DATABASE and feeder files."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRUTH_ROOT = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv"
PROCESSED_ROOT = ROOT / "processed_data"
DATABASE_PATH = TRUTH_ROOT / "DATABASE.csv"

RAC_SOURCE_LABEL = "2026_RAC_CURRENT_YEAR_ALLOTMENT"
RAC_SOURCE_STATUS = "RAC_CURRENT_YEAR_SPLIT"
RAC_TOTAL_ONLY_STATUS = "RAC_CURRENT_YEAR_TOTAL_ONLY"

EXCLUDED_PROMOTION_TOKENS = (
    "metadata",
    "comparison",
    "verification",
    "control_units",
    "supplemental",
    "permit_rows_from_pdf",
)

CSV_FEEDER_PATHS = [
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
]

JSON_FEEDER_PATHS = [
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.json",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.json",
    ROOT / "canonical" / "hunt-planner-2026.json",
]

ALLOTMENT_FIELDS = [
    "permit_allotment_2026_res",
    "permit_allotment_2026_nr",
    "permit_allotment_2026_total",
    "permit_allotment_2026_source",
    "permit_allotment_2026_source_file",
    "permit_allotment_2026_status",
]

SOURCE_FIELDS = ["permits_2026_source"]


@dataclass(frozen=True)
class RacRow:
    hunt_code: str
    hunt_name: str
    species: str
    sex_type: str
    weapon: str
    hunt_type: str
    hunt_class: str
    season: str
    permits_2026_res: str
    permits_2026_nr: str
    permits_2026_total: str
    source_file: str
    source_row_number: int
    source_document: str
    family: str

    @property
    def has_split(self) -> bool:
        return bool(self.permits_2026_res or self.permits_2026_nr)

    @property
    def allotment_status(self) -> str:
        return RAC_SOURCE_STATUS if self.has_split else RAC_TOTAL_ONLY_STATUS


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    if text in {"-", "–", "—"}:
        return ""
    return text


def to_int_text(value: object) -> str:
    text = clean(value).replace(",", "")
    if text == "":
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def family_from_file(path: Path) -> str:
    name = path.stem
    if name.startswith("2026_rac_"):
        name = name.removeprefix("2026_rac_")
    return name.removesuffix("_permits")


def species_for_family(family: str, row: dict[str, str]) -> str:
    explicit = clean(row.get("species"))
    if explicit:
        return explicit
    mapping = [
        ("antlerless_deer", "Deer"),
        ("buck_deer", "Deer"),
        ("doe_pronghorn", "Pronghorn"),
        ("buck_pronghorn", "Pronghorn"),
        ("antlerless_elk", "Elk"),
        ("bull_elk", "Elk"),
        ("antlerless_moose", "Moose"),
        ("bull_moose", "Moose"),
        ("mountain_goat", "Mountain Goat"),
        ("desert_bighorn_sheep", "Desert Bighorn Sheep"),
        ("rocky_mountain_bighorn_sheep", "Rocky Mountain Bighorn Sheep"),
        ("ewe_rocky", "Rocky Mountain Bighorn Sheep"),
        ("bison", "Bison"),
    ]
    for token, species in mapping:
        if token in family:
            return species
    return ""


def sex_type_for_family(family: str, row: dict[str, str]) -> str:
    explicit = clean(row.get("sex_type"))
    if explicit:
        return explicit.replace("Hunter’s", "Hunters")
    if "antlerless" in family:
        return "Antlerless"
    if "doe_pronghorn" in family:
        return "Doe"
    if "buck_deer" in family or "buck_pronghorn" in family:
        return "Buck"
    if "bull_elk" in family or "bull_moose" in family:
        return "Bull"
    return "Either Sex"


def hunt_type_for_family(family: str, row: dict[str, str]) -> str:
    if "private_lands_only" in family:
        return "Private Lands Only"
    if "oial" in family:
        return "Once-in-a-lifetime"
    if "premium" in family:
        return "Premium Limited Entry"
    if "limited_entry" in family or "buck_pronghorn" in family:
        return "Limited Entry"
    return "General Season"


def derive_hunt_name(row: dict[str, str]) -> str:
    return clean(row.get("hunt_name")) or clean(row.get("permit_group")) or clean(row.get("category"))


def source_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(TRUTH_ROOT.glob("2026_rac_*.csv")):
        lower = path.name.lower()
        if any(token in lower for token in EXCLUDED_PROMOTION_TOKENS):
            continue
        files.append(path)
    return files


def choose(existing: RacRow | None, candidate: RacRow) -> RacRow:
    if existing is None:
        return candidate
    if candidate.has_split and not existing.has_split:
        return candidate
    if candidate.permits_2026_total and not existing.permits_2026_total:
        return candidate
    return existing


def load_direct_rac_rows() -> dict[str, RacRow]:
    direct: dict[str, RacRow] = {}
    for path in source_files():
        family = family_from_file(path)
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "hunt_code" not in reader.fieldnames:
                continue
            for row_number, row in enumerate(reader, start=2):
                hunt_code = clean(row.get("hunt_code")).upper()
                if not hunt_code:
                    continue
                res = to_int_text(row.get("permits_2026_res"))
                nr = to_int_text(row.get("permits_2026_nr"))
                total = to_int_text(row.get("permits_2026_total"))
                if not total and (res or nr):
                    total = str(int(res or 0) + int(nr or 0))
                if not (res or nr or total):
                    continue
                candidate = RacRow(
                    hunt_code=hunt_code,
                    hunt_name=derive_hunt_name(row),
                    species=species_for_family(family, row),
                    sex_type=sex_type_for_family(family, row),
                    weapon=clean(row.get("weapon")),
                    hunt_type=hunt_type_for_family(family, row),
                    hunt_class=hunt_type_for_family(family, row),
                    season=clean(row.get("season_dates_2026")),
                    permits_2026_res=res,
                    permits_2026_nr=nr,
                    permits_2026_total=total,
                    source_file=path.relative_to(ROOT).as_posix(),
                    source_row_number=row_number,
                    source_document=clean(row.get("source_document")),
                    family=family,
                )
                direct[hunt_code] = choose(direct.get(hunt_code), candidate)
    return direct


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def ensure_fields(fields: list[str], extra_fields: list[str]) -> list[str]:
    output = list(fields)
    for field in extra_fields:
        if field not in output:
            output.append(field)
    return output


def apply_rac_to_record(record: dict[str, Any], rac: RacRow, *, preserve_name: bool = False) -> int:
    changed = 0

    def set_value(field: str, value: str, *, allow_blank: bool = False) -> None:
        nonlocal changed
        if value == "" and not allow_blank:
            return
        if field in record or value != "":
            before = clean(record.get(field))
            if before != value:
                record[field] = value
                changed += 1

    if not preserve_name:
        set_value("hunt_name", rac.hunt_name)
        set_value("title", rac.hunt_name)
        set_value("unitName", rac.hunt_name)
    set_value("species", rac.species)
    set_value("sex_type", rac.sex_type)
    set_value("weapon", rac.weapon)
    set_value("hunt_type", rac.hunt_type)
    set_value("hunt_class", rac.hunt_class)
    set_value("season", rac.season)
    set_value("permits_2026_res", rac.permits_2026_res, allow_blank=True)
    set_value("permits_2026_nr", rac.permits_2026_nr, allow_blank=True)
    set_value("permits_2026_total", rac.permits_2026_total, allow_blank=True)
    set_value("permits_2026_source", RAC_SOURCE_LABEL)
    set_value("permit_overlay_source", rac.source_file)
    set_value("permit_source_authority", "2026 RAC current-year allotment")
    set_value("data_status", "RAC_CURRENT_YEAR_ALLOTMENT_VERIFIED")
    set_value("permit_allotment_2026_res", rac.permits_2026_res, allow_blank=True)
    set_value("permit_allotment_2026_nr", rac.permits_2026_nr, allow_blank=True)
    set_value("permit_allotment_2026_total", rac.permits_2026_total, allow_blank=True)
    set_value("permit_allotment_2026_source", RAC_SOURCE_LABEL)
    set_value("permit_allotment_2026_source_file", rac.source_file)
    set_value("permit_allotment_2026_status", rac.allotment_status)
    return changed


def new_database_row(fieldnames: list[str], rac: RacRow) -> dict[str, str]:
    row = {field: "" for field in fieldnames}
    row["hunt_code"] = rac.hunt_code
    row["hunt_name"] = rac.hunt_name
    row["sex_type"] = rac.sex_type
    row["species"] = rac.species
    row["weapon"] = rac.weapon
    row["hunt_type"] = rac.hunt_type
    row["season"] = rac.season
    row["NOTES"] = "Added from direct 2026 RAC current-year allotment row."
    apply_rac_to_record(row, rac)
    return row


def new_canonical_record(fieldnames: list[str], rac: RacRow) -> dict[str, str]:
    row = {field: "" for field in fieldnames}
    row["hunt_code"] = rac.hunt_code
    row["huntCode"] = rac.hunt_code
    row["code"] = rac.hunt_code
    row["title"] = rac.hunt_name
    row["hunt_name"] = rac.hunt_name
    row["unitName"] = rac.hunt_name
    row["species"] = rac.species
    row["sex_type"] = rac.sex_type
    row["weapon"] = rac.weapon
    row["hunt_type"] = rac.hunt_type
    row["hunt_class"] = rac.hunt_class
    row["draw_family"] = "NONE"
    row["season"] = rac.season
    row["youth_flag"] = "FALSE"
    row["eligibility_class"] = "STANDARD"
    row["access_type"] = "Public"
    row["source_file"] = rac.source_file
    row["source_authority"] = "2026 RAC current-year allotment"
    row["data_status"] = "RAC_CURRENT_YEAR_ALLOTMENT_VERIFIED"
    apply_rac_to_record(row, rac)
    return row


def backup(path: Path, backup_dir: Path) -> str:
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest.relative_to(ROOT).as_posix()


def promote_csv(path: Path, rac_rows: dict[str, RacRow], backup_dir: Path, *, database: bool = False) -> dict[str, Any]:
    fields, rows = read_csv(path)
    fields = ensure_fields(fields, SOURCE_FIELDS + ALLOTMENT_FIELDS)
    by_code = {clean(row.get("hunt_code")).upper(): row for row in rows if clean(row.get("hunt_code"))}
    changed_cells = 0
    corrected = 0
    added = 0
    for code, rac in rac_rows.items():
        row = by_code.get(code)
        if row is None:
            row = new_database_row(fields, rac) if database else new_canonical_record(fields, rac)
            rows.append(row)
            by_code[code] = row
            added += 1
            changed_cells += 1
            continue
        before_changes = apply_rac_to_record(row, rac, preserve_name=False)
        if before_changes:
            corrected += 1
            changed_cells += before_changes
    backup_path = ""
    if changed_cells:
        backup_path = backup(path, backup_dir)
        write_csv(path, fields, rows)
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "kind": "csv",
        "rows_after": len(rows),
        "corrected_rows": corrected,
        "added_rows": added,
        "changed_cells": changed_cells,
        "backup_path": backup_path,
    }


def json_records(data: Any) -> tuple[list[dict[str, Any]], str]:
    if isinstance(data, list):
        return data, "root_list"
    if isinstance(data, dict):
        for key in ("hunt_catalog", "hunts", "records"):
            if isinstance(data.get(key), list):
                return data[key], key
    raise ValueError("Unsupported JSON catalog shape")


def promote_json(path: Path, rac_rows: dict[str, RacRow], backup_dir: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records, shape = json_records(data)
    field_order = list(dict.fromkeys(key for record in records for key in record.keys()))
    field_order = ensure_fields(field_order, SOURCE_FIELDS + ALLOTMENT_FIELDS)
    by_code = {clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper(): row for row in records}
    corrected = 0
    added = 0
    changed_cells = 0
    for code, rac in rac_rows.items():
        row = by_code.get(code)
        if row is None:
            row = new_canonical_record(field_order, rac)
            records.append(row)
            by_code[code] = row
            added += 1
            changed_cells += 1
            continue
        before_changes = apply_rac_to_record(row, rac)
        if before_changes:
            corrected += 1
            changed_cells += before_changes
    if isinstance(data, dict) and shape == "hunt_catalog":
        data.setdefault("metadata", {})["rac_current_year_allotment_promoted_at"] = datetime.now(timezone.utc).isoformat()
        data.setdefault("metadata", {})["rac_current_year_allotment_source"] = RAC_SOURCE_LABEL
    backup_path = ""
    if changed_cells:
        backup_path = backup(path, backup_dir)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "kind": f"json:{shape}",
        "rows_after": len(records),
        "corrected_rows": corrected,
        "added_rows": added,
        "changed_cells": changed_cells,
        "backup_path": backup_path,
    }


def validate_database(path: Path, rac_rows: dict[str, RacRow]) -> dict[str, Any]:
    _, rows = read_csv(path)
    by_code = {clean(row.get("hunt_code")).upper(): row for row in rows if clean(row.get("hunt_code"))}
    mismatches: list[dict[str, str]] = []
    missing: list[str] = []
    for code, rac in rac_rows.items():
        row = by_code.get(code)
        if row is None:
            missing.append(code)
            continue
        fields = {
            "permits_2026_res": rac.permits_2026_res,
            "permits_2026_nr": rac.permits_2026_nr,
            "permits_2026_total": rac.permits_2026_total,
        }
        if rac.season:
            fields["season"] = rac.season
        for field, expected in fields.items():
            if clean(row.get(field)) != expected:
                mismatches.append(
                    {
                        "hunt_code": code,
                        "field": field,
                        "expected": expected,
                        "actual": clean(row.get(field)),
                    }
                )
    return {
        "database_rows": len(rows),
        "database_unique_hunt_codes": len(by_code),
        "rac_direct_hunt_code_count": len(rac_rows),
        "missing_after_promotion": missing,
        "mismatch_count_after_promotion": len(mismatches),
        "mismatches_after_promotion": mismatches[:100],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write files. Default is dry-run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = "write" if args.write else "dry_run"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = PROCESSED_ROOT / "backups" / f"rac_current_year_database_promotion_{timestamp}"
    rac_rows = load_direct_rac_rows()
    report_rows: list[dict[str, Any]] = []

    if args.write:
        report_rows.append(promote_csv(DATABASE_PATH, rac_rows, backup_dir, database=True))
        for path in CSV_FEEDER_PATHS:
            if path.exists():
                report_rows.append(promote_csv(path, rac_rows, backup_dir))
        for path in JSON_FEEDER_PATHS:
            if path.exists():
                report_rows.append(promote_json(path, rac_rows, backup_dir))
    else:
        _, db_rows = read_csv(DATABASE_PATH)
        db_codes = {clean(row.get("hunt_code")).upper() for row in db_rows if clean(row.get("hunt_code"))}
        report_rows.append(
            {
                "file": DATABASE_PATH.relative_to(ROOT).as_posix(),
                "kind": "csv",
                "rows_after": len(db_rows),
                "corrected_rows": "dry_run",
                "added_rows": len(set(rac_rows) - db_codes),
                "changed_cells": "dry_run",
                "backup_path": "",
            }
        )

    validation = validate_database(DATABASE_PATH, rac_rows) if args.write else {}
    source_counts = Counter(rac.family for rac in rac_rows.values())
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "rac_current_year_allotment_source": RAC_SOURCE_LABEL,
        "excluded_promotion_tokens": list(EXCLUDED_PROMOTION_TOKENS),
        "rac_direct_hunt_code_count": len(rac_rows),
        "rac_family_hunt_code_counts": dict(sorted(source_counts.items())),
        "files": report_rows,
        "validation": validation,
    }
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = PROCESSED_ROOT / f"rac_current_year_database_promotion_{mode}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if args.write and validation.get("mismatch_count_after_promotion"):
        return 1
    if args.write and validation.get("missing_after_promotion"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
