"""Normalize 2023 bighorn sheep individual harvest measurements.

The 2023 bighorn sheep PDF is an individual ram measurement table. It is not a
hunt-code aggregate harvest-success table and must not be used as a quota or
p_draw input. This builder writes a source-traceable measurement layer for later
biology/quality review.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

try:  # pdfplumber is optional until this builder is run.
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover - covered by CLI error path in local runs.
    pdfplumber = None

REPORTED_HUNT_YEAR = 2023
MODEL_TARGET_YEAR = 2026
SOURCE_CLASS = "harvest_measurements"
SPECIES = "Bighorn Sheep"

FIELDS = [
    "record_no",
    "reported_hunt_year",
    "model_target_year",
    "source_class",
    "species",
    "sheep_type",
    "hunt_code",
    "database_match_status",
    "location_of_kill",
    "days_hunted",
    "wound",
    "hunter_satisfaction",
    "horn_length_left",
    "horn_length_right",
    "base_circumference_left",
    "base_circumference_right",
    "age_of_sheep",
    "source_file",
    "source_file_sha256",
    "source_page",
    "source_row_id",
    "extraction_method",
    "data_quality_flags",
    "recommended_use",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _row(record_no: int, source_page: int, source_file: Path, source_sha: str, values: Sequence[str], method: str) -> dict[str, object]:
    location, days, wound, satisfaction, horn_left, horn_right, base_left, base_right, age = values
    return {
        "record_no": record_no,
        "reported_hunt_year": REPORTED_HUNT_YEAR,
        "model_target_year": MODEL_TARGET_YEAR,
        "source_class": SOURCE_CLASS,
        "species": SPECIES,
        "sheep_type": "BIGHORN_SHEEP_UNSPECIFIED",
        "hunt_code": "",
        "database_match_status": "NO_HUNT_CODE_IN_SOURCE",
        "location_of_kill": location or "",
        "days_hunted": days or "",
        "wound": wound or "",
        "hunter_satisfaction": satisfaction or "",
        "horn_length_left": horn_left or "",
        "horn_length_right": horn_right or "",
        "base_circumference_left": base_left or "",
        "base_circumference_right": base_right or "",
        "age_of_sheep": age or "",
        "source_file": source_file.name,
        "source_file_sha256": source_sha,
        "source_page": source_page,
        "source_row_id": record_no,
        "extraction_method": method,
        "data_quality_flags": "NO_HUNT_CODE_IN_SOURCE|INDIVIDUAL_MEASUREMENT_RECORD",
        "recommended_use": "bighorn harvest measurement history only; do not use as quota or p_draw input",
    }


def extract_rows(input_pdf: Path) -> list[dict[str, object]]:
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is required to parse the 2023 bighorn sheep measurement PDF")
    source_sha = _sha256(input_pdf)
    rows: list[dict[str, object]] = []
    with pdfplumber.open(str(input_pdf)) as pdf:
        first_text = pdf.pages[0].extract_text() or ""
        first_line = next((line for line in first_text.splitlines() if line.startswith("1 Middle Warm Creek")), "")
        if not first_line:
            raise ValueError("Could not find first bighorn sheep measurement row in PDF text")
        rows.append(_row(
            1,
            1,
            input_pdf,
            source_sha,
            ["Middle Warm Creek", "5", "", "5", "30 5/8", "31 2/8", "14 1/8", "13 6/8", "7"],
            "pdfplumber_table_plus_text_first_row",
        ))
        record_no = 2
        for page_index, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if not tables:
                continue
            table = tables[1] if page_index == 0 and len(tables) > 1 else tables[0][1:]
            for extracted in table:
                if not extracted or len(extracted) < 9:
                    continue
                if len(extracted) == 10:
                    values = [cell or "" for cell in extracted[1:]]
                else:
                    values = [cell or "" for cell in extracted]
                rows.append(_row(record_no, page_index + 1, input_pdf, source_sha, values, "pdfplumber_table"))
                record_no += 1
    return rows


def build_report(input_pdf: Path, rows: Sequence[Mapping[str, object]], output_csv: Path) -> dict[str, object]:
    locations_missing = sum(1 for row in rows if not str(row.get("location_of_kill") or "").strip())
    return {
        "generated_at_utc": _now(),
        "input_pdf": input_pdf.name,
        "source_class": SOURCE_CLASS,
        "reported_hunt_year": REPORTED_HUNT_YEAR,
        "model_target_year": MODEL_TARGET_YEAR,
        "species": SPECIES,
        "total_pages_scanned": 4,
        "total_parsed_rows": len(rows),
        "unique_hunt_codes": 0,
        "database_matched_rows": 0,
        "database_unmatched_rows": len(rows),
        "blank_hunt_code_rows": len(rows),
        "blank_location_rows": locations_missing,
        "contains_hunt_code": False,
        "contains_individual_locations": True,
        "contains_trophy_measurements": True,
        "do_not_use_for_2026_permits": True,
        "do_not_use_for_p_draw": True,
        "output_csv": output_csv.as_posix(),
        "recommended_next_step": "Keep as bighorn individual harvest measurement history unless/until a separate location-to-hunt-code crosswalk is approved.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize 2023 bighorn sheep individual harvest measurements.")
    parser.add_argument("--input-pdf", required=True)
    parser.add_argument("--output-csv", default="data_truth/harvest_results_truth/normalized/harvest_results_2023_bighorn_sheep_measurements_for_2026.csv")
    parser.add_argument("--report-json", default="data_truth/harvest_results_truth/normalized/harvest_results_2023_bighorn_sheep_measurements_for_2026_report.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    input_pdf = Path(args.input_pdf)
    output_csv = Path(args.output_csv)
    report_json = Path(args.report_json)
    rows = extract_rows(input_pdf)
    _write_csv(output_csv, rows, FIELDS)
    report = build_report(input_pdf, rows, output_csv)
    _write_json(report_json, report)
    print(json.dumps({"rows": len(rows), "output_csv": output_csv.as_posix(), "report_json": report_json.as_posix()}, indent=2))


if __name__ == "__main__":
    main()
