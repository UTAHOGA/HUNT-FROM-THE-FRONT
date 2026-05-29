from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
DATABASE_CSV = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
PERMIT_DIR = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/2026 Permits"
PUBLIC_XLSX_DIR = ROOT / "processed_data/hard_data_exports/hunt_tables/2026/XLXS"
AUDIT_DIR = ROOT / "processed_data/audits"


CANONICAL_COLUMNS = [
    "hunt_name",
    "hunt_code",
    "boundary_id",
    "hunt_code_mapping_status",
    "boundary_id_mapping_status",
    "candidate_hunt_code",
    "candidate_boundary_id",
    "sex_type",
    "species",
    "weapon",
    "hunt_type",
    "season",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
    "permit_count_status",
    "source_file",
    "source_row_number",
]


FAMILY_CONFIGS = [
    {
        "family": "BLACK_BEAR",
        "output": "2026 black bear permits reviewed res-nr-total.csv",
        "sources": ["2026 BLACK BEAR DRAW.xlsx"],
        "code_prefixes": ("BR",),
        "species": ("Black Bear",),
    },
    {
        "family": "BUCK_DEER",
        "output": "2026 buck deer all reviewed res-nr-total.csv",
        "sources": ["2026 DEER BUCK DRAW.xlsx"],
        "code_prefixes": ("DB", "LD", "LO"),
        "species": ("Deer",),
        "sex_type": ("Buck",),
    },
    {
        "family": "ELK_ANTLERLESS",
        "output": "2026 elk antlerless all reviewed res-nr-total.csv",
        "sources": ["2026 ELK ANTLERLESS DRAW.xlsx"],
        "code_prefixes": ("EA",),
        "species": ("Elk",),
        "sex_type": ("Antlerless",),
    },
    {
        "family": "ELK_BULL",
        "output": "2026 elk bull all reviewed res-nr-total.csv",
        "sources": ["2026 ELK BULL ALL HUNTS.xlsx"],
        "code_prefixes": ("EB", "EL", "LO"),
        "species": ("Elk",),
        "sex_type": ("Bull",),
    },
    {
        "family": "MOOSE_BULL",
        "output": "2026 moose bull all reviewed res-nr-total.csv",
        "sources": ["2026 MOOSE BULL O.I.L.xlsx"],
        "code_prefixes": ("MB",),
        "species": ("Moose",),
        "sex_type": ("Bull",),
    },
    {
        "family": "PRONGHORN_BUCK",
        "output": "2026 pronghorn buck all reviewed res-nr-total.csv",
        "sources": [
            "2026 PRONGHORN BUCK STATEWIDE.xlsx",
            "2026 PRONGHORN BUCK L.E.xlsx",
            "2026 PRONGHORN BUCK L.E PRIVATE LANDS ONLY.xlsx",
            "2026 PRONGHORN BUCK CWMU.xlsx",
        ],
        "code_prefixes": ("PB", "LP"),
        "species": ("Pronghorn",),
        "sex_type": ("Buck",),
    },
    {
        "family": "PRONGHORN_DOE",
        "output": "2026 pronghorn doe all reviewed res-nr-total.csv",
        "sources": [
            "2026 PRONGHORN DOE GENERAL SEASON.xlsx",
            "2026 PRONGHORN DOE CWMU.xlsx",
        ],
        "code_prefixes": ("PD",),
        "species": ("Pronghorn",),
        "sex_type": ("Doe",),
    },
    {
        "family": "TURKEY_BEARDED",
        "output": "2026 turkey bearded all reviewed total.csv",
        "sources": ["2026 TURKEY BEARDED DRAW.xlsx"],
        "code_prefixes": ("TK",),
        "species": ("Turkey",),
        "sex_type": ("Bearded",),
    },
]


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", text(value)).casefold()


def code(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", text(value).upper())


def numeric(value: object) -> str:
    raw = text(value)
    if not raw:
        return ""
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return ""
    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else str(number)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{k: text(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def read_database_map() -> dict[str, dict[str, str]]:
    rows = read_csv_rows(DATABASE_CSV)
    return {code(row.get("hunt_code")): row for row in rows if code(row.get("hunt_code"))}


def read_xlsx_rows(path: Path) -> list[dict[str, object]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [text(value) for value in rows[0]]
    output: list[dict[str, object]] = []
    for values in rows[1:]:
        row = dict(zip(headers, values))
        if text(row.get("hunt_code")):
            output.append(row)
    return output


def permit_status(res: str, nr: str, total: str) -> str:
    if res and nr and total:
        return "FULL_SPLIT"
    if total and not res and not nr:
        return "TOTAL_ONLY"
    if not total and not res and not nr:
        return "NO_PUBLISHED_NUMERIC_PERMIT"
    return "PARTIAL_PERMIT_FIELDS_REVIEW"


def row_allowed(row: dict[str, object], config: dict[str, object]) -> bool:
    hunt_code = code(row.get("hunt_code"))
    prefixes = tuple(config.get("code_prefixes", ()))
    if prefixes and not hunt_code.startswith(prefixes):
        return False
    species = tuple(norm(v) for v in config.get("species", ()))
    if species and norm(row.get("species")) not in species:
        return False
    sex_types = tuple(norm(v) for v in config.get("sex_type", ()))
    if sex_types and norm(row.get("sex_type")) not in sex_types:
        return False
    return True


def canonicalize_row(
    row: dict[str, object],
    source_file: str,
    source_row_number: int,
    database: dict[str, dict[str, str]],
) -> dict[str, str]:
    hunt_code = code(row.get("hunt_code"))
    database_row = database.get(hunt_code, {})
    boundary_id = text(database_row.get("boundary_id") or database_row.get("BOUNDARY_ID"))

    res = numeric(row.get("permits_2026_res"))
    nr = numeric(row.get("permits_2026_nr"))
    total = numeric(row.get("permits_2026_total"))
    if not total and res and nr:
        total = str(int(res) + int(nr))

    return {
        "hunt_name": text(row.get("hunt_name")),
        "hunt_code": hunt_code,
        "boundary_id": boundary_id,
        "hunt_code_mapping_status": "REVIEWED_CURRENT_HUNT_CODE",
        "boundary_id_mapping_status": "DATABASE_BOUNDARY_ID" if boundary_id else "MISSING_BOUNDARY_ID_REVIEW",
        "candidate_hunt_code": hunt_code,
        "candidate_boundary_id": boundary_id,
        "sex_type": text(row.get("sex_type")),
        "species": text(row.get("species")),
        "weapon": text(row.get("weapon")),
        "hunt_type": text(row.get("hunt_type")),
        "season": text(row.get("season")),
        "permits_2026_res": res,
        "permits_2026_nr": nr,
        "permits_2026_total": total,
        "permit_count_status": permit_status(res, nr, total),
        "source_file": source_file,
        "source_row_number": str(source_row_number),
        "_source_file": source_file,
        "_source_row_number": str(source_row_number),
    }


def sort_key(row: dict[str, str]) -> tuple[str, int, str]:
    hunt_code = row["hunt_code"]
    match = re.match(r"([A-Z]+)(\d+)", hunt_code)
    if not match:
        return (hunt_code, 0, hunt_code)
    return (match.group(1), int(match.group(2)), hunt_code)


def write_truth_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CANONICAL_COLUMNS})


def validate_family(rows: list[dict[str, str]]) -> dict[str, object]:
    codes = [row["hunt_code"] for row in rows]
    duplicates = sorted(code for code, count in Counter(codes).items() if count > 1)
    bad_totals = []
    for row in rows:
        res = numeric(row.get("permits_2026_res"))
        nr = numeric(row.get("permits_2026_nr"))
        total = numeric(row.get("permits_2026_total"))
        if res and nr and total and int(res) + int(nr) != int(total):
            bad_totals.append(row["hunt_code"])

    status_counts = Counter(row["permit_count_status"] for row in rows)
    hunt_type_counts = Counter(row["hunt_type"] for row in rows)
    weapon_counts = Counter(row["weapon"] for row in rows)
    source_counts = Counter(row["_source_file"] for row in rows)
    missing_source_rows = [
        row["hunt_code"] for row in rows if not row.get("source_file") or not row.get("source_row_number")
    ]
    return {
        "rows": len(rows),
        "duplicate_hunt_codes": duplicates,
        "bad_split_totals": bad_totals,
        "missing_source_rows": missing_source_rows,
        "permit_status_counts": dict(status_counts),
        "hunt_type_counts": dict(hunt_type_counts),
        "weapon_counts": dict(weapon_counts),
        "source_counts": dict(source_counts),
    }


def main() -> None:
    PERMIT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    database = read_database_map()

    audit_rows = []
    audit_json = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "pasted-aligned public hunt table workbooks",
        "families": {},
    }

    for config in FAMILY_CONFIGS:
        family = str(config["family"])
        all_rows: list[dict[str, str]] = []
        for source in config["sources"]:
            source_path = PUBLIC_XLSX_DIR / source
            rows = read_xlsx_rows(source_path)
            for index, row in enumerate(rows, start=2):
                if not row_allowed(row, config):
                    continue
                all_rows.append(canonicalize_row(row, source, index, database))

        all_rows.sort(key=sort_key)
        output_path = PERMIT_DIR / str(config["output"])
        write_truth_csv(output_path, all_rows)

        validation = validate_family(all_rows)
        validation["output"] = str(output_path)
        audit_json["families"][family] = validation
        audit_rows.append(
            {
                "family": family,
                "output": str(output_path),
                "rows": validation["rows"],
                "full_split": validation["permit_status_counts"].get("FULL_SPLIT", 0),
                "total_only": validation["permit_status_counts"].get("TOTAL_ONLY", 0),
                "blank_no_published_numeric": validation["permit_status_counts"].get(
                    "NO_PUBLISHED_NUMERIC_PERMIT", 0
                ),
                "partial": validation["permit_status_counts"].get("PARTIAL_PERMIT_FIELDS_REVIEW", 0),
                "duplicate_hunt_codes": len(validation["duplicate_hunt_codes"]),
                "bad_split_totals": len(validation["bad_split_totals"]),
                "missing_source_rows": len(validation["missing_source_rows"]),
                "source_counts": json.dumps(validation["source_counts"], sort_keys=True),
            }
        )

    audit_csv_path = AUDIT_DIR / "reviewed_permit_truth_sources_2026_audit.csv"
    with audit_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0].keys()))
        writer.writeheader()
        writer.writerows(audit_rows)

    audit_json_path = AUDIT_DIR / "reviewed_permit_truth_sources_2026_audit.json"
    audit_json["outputs"] = {
        "audit_csv": str(audit_csv_path),
        "audit_json": str(audit_json_path),
    }
    with audit_json_path.open("w", encoding="utf-8") as handle:
        json.dump(audit_json, handle, indent=2)

    print(json.dumps(audit_json, indent=2))


if __name__ == "__main__":
    main()
