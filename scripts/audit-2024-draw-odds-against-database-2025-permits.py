"""Audit 2024 draw-odds permit totals against DATABASE 2025 permit fields.

The 24-series draw-odds PDFs are historical draw evidence used for the 2025
model target. This audit intentionally does not overwrite DATABASE.csv because
many current 2025 permit fields already carry reviewed 2025 source lineage.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/comprehensive_2024/2024_DRAW_RESULTS_COMPREHENSIVE.csv"
)
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
NORMALIZED_OUT = (
    ROOT / "data_truth/draw_results_truth/normalized/draw_odds_2024_model_target_2025_permit_totals.csv"
)
VALIDATION_OUT = (
    ROOT / "data_truth/draw_results_truth/validation/draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits.csv"
)
SUMMARY_OUT = (
    ROOT / "data_truth/draw_results_truth/validation/draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits_summary.json"
)
REPORT_OUT = ROOT / "processed_data/draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits.md"

SOURCE_DRAW_YEAR = 2024
MODEL_TARGET_YEAR = 2025


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    return "" if text in {"", "-", "nan", "None"} else text


def int_text(value: object) -> str:
    text = clean(value).replace(",", "")
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_pdf_path(source_file: str) -> Path:
    return ROOT / "pipeline/RAW/hunt_unit_database/2025/pdf/draw_odds" / source_file


def triple(row: dict[str, str], prefix: str) -> tuple[str, str, str]:
    return (
        int_text(row.get(f"{prefix}_res")),
        int_text(row.get(f"{prefix}_nr")),
        int_text(row.get(f"{prefix}_total")),
    )


def compare(source: tuple[str, str, str], target: tuple[str, str, str]) -> str:
    if source == target:
        return "MATCH"
    if target == ("", "", ""):
        return "DATABASE_BLANK"
    return "DIFFERS"


def build_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    source_rows = read_csv(SOURCE)
    db_by_code = {row["hunt_code"]: row for row in read_csv(DATABASE) if row.get("hunt_code")}
    source_hash_by_file = {
        file_name: sha256(source_pdf_path(file_name)) for file_name in sorted({row["source_file"] for row in source_rows})
    }

    normalized: list[dict[str, object]] = []
    validation: list[dict[str, object]] = []
    missing_database_codes: list[str] = []

    for row in source_rows:
        code = clean(row.get("hunt_code")).upper()
        db = db_by_code.get(code, {})
        source_file = clean(row.get("source_file"))
        source_res = int_text(row.get("res_total_permits"))
        source_nr = int_text(row.get("nr_total_permits"))
        source_total = int_text(row.get("total_permits"))
        source_values = (source_res, source_nr, source_total)
        db_2025 = triple(db, "permits_2025") if db else ("", "", "")
        db_2025_draw = triple(db, "permits_2025_draw") if db else ("", "", "")
        source_rel = f"pipeline/RAW/hunt_unit_database/2025/pdf/draw_odds/{source_file}"

        if not db:
            missing_database_codes.append(code)

        normalized_row = {
            "hunt_code": code,
            "boundary_id": db.get("boundary_id", ""),
            "hunt_code_mapping_status": "REVIEWED_CURRENT_DATABASE_CODE" if db else "SOURCE_CODE_NOT_IN_DATABASE",
            "boundary_id_mapping_status": "DATABASE_BOUNDARY_ID" if db.get("boundary_id") else "BOUNDARY_ID_MISSING",
            "candidate_hunt_code": code,
            "candidate_boundary_id": db.get("boundary_id", ""),
            "hunt_name": clean(row.get("hunt_name")),
            "database_hunt_name": db.get("hunt_name", ""),
            "source_draw_year": SOURCE_DRAW_YEAR,
            "model_target_year": MODEL_TARGET_YEAR,
            "source_file": source_rel,
            "source_sha256": source_hash_by_file.get(source_file, ""),
            "source_page": int_text(row.get("source_page")),
            "source_dataset": clean(row.get("source_dataset")),
            "dataset_family": clean(row.get("dataset_family")),
            "parse_style": clean(row.get("parse_style")),
            "resident_total_permits": source_res,
            "nonresident_total_permits": source_nr,
            "total_public_draw_permits": source_total,
        }
        normalized.append(normalized_row)
        validation.append(
            {
                **normalized_row,
                "database_species": db.get("species", ""),
                "database_weapon": db.get("weapon", ""),
                "database_hunt_type": db.get("hunt_type", ""),
                "database_permits_2025_res": db_2025[0],
                "database_permits_2025_nr": db_2025[1],
                "database_permits_2025_total": db_2025[2],
                "database_permits_2025_source": db.get("permits_2025_source", ""),
                "database_permits_2025_draw_res": db_2025_draw[0],
                "database_permits_2025_draw_nr": db_2025_draw[1],
                "database_permits_2025_draw_total": db_2025_draw[2],
                "database_permits_2025_draw_source": db.get("permits_2025_draw_source", ""),
                "permits_2025_comparison_status": "SOURCE_CODE_NOT_IN_DATABASE"
                if not db
                else compare(source_values, db_2025),
                "permits_2025_draw_comparison_status": "SOURCE_CODE_NOT_IN_DATABASE"
                if not db
                else compare(source_values, db_2025_draw),
                "promotion_recommendation": "DO_NOT_OVERWRITE_REVIEWED_2025_HISTORY"
                if db and compare(source_values, db_2025) == "DIFFERS"
                else ("SAFE_BLANK_CANDIDATE_REVIEW_REQUIRED" if db and db_2025 == ("", "", "") else "REFERENCE_ONLY"),
            }
        )

    status_2025 = Counter(str(row["permits_2025_comparison_status"]) for row in validation)
    status_2025_draw = Counter(str(row["permits_2025_draw_comparison_status"]) for row in validation)
    source_prefix_counts = Counter(str(row["hunt_code"])[:2] for row in normalized)
    recommendation_counts = Counter(str(row["promotion_recommendation"]) for row in validation)
    blank_candidates = [
        row["hunt_code"] for row in validation if row["promotion_recommendation"] == "SAFE_BLANK_CANDIDATE_REVIEW_REQUIRED"
    ]
    summary = {
        "artifact": "draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_csv": SOURCE.relative_to(ROOT).as_posix(),
        "database_csv": DATABASE.relative_to(ROOT).as_posix(),
        "source_draw_year": SOURCE_DRAW_YEAR,
        "model_target_year": MODEL_TARGET_YEAR,
        "source_rows": len(source_rows),
        "source_unique_hunt_codes": len({row["hunt_code"] for row in normalized}),
        "database_row_count": len(db_by_code),
        "source_codes_missing_database_count": len(set(missing_database_codes)),
        "source_codes_missing_database": sorted(set(missing_database_codes)),
        "source_prefix_counts": dict(sorted(source_prefix_counts.items())),
        "permits_2025_status_counts": dict(sorted(status_2025.items())),
        "permits_2025_draw_status_counts": dict(sorted(status_2025_draw.items())),
        "promotion_recommendation_counts": dict(sorted(recommendation_counts.items())),
        "safe_blank_candidate_codes": sorted(blank_candidates),
        "guardrail": "Reference audit only. No DATABASE.csv permit fields are modified by this script.",
        "outputs": {
            "normalized_csv": NORMALIZED_OUT.relative_to(ROOT).as_posix(),
            "validation_csv": VALIDATION_OUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_OUT.relative_to(ROOT).as_posix(),
            "report_md": REPORT_OUT.relative_to(ROOT).as_posix(),
        },
    }
    return normalized, validation, summary


def write_report(summary: dict[str, object]) -> None:
    lines = [
        "# 2024 Draw Odds Vs DATABASE 2025 Permit Fields",
        "",
        f"- Source rows: `{summary['source_rows']}`",
        f"- Source unique hunt codes: `{summary['source_unique_hunt_codes']}`",
        f"- Source codes missing active DATABASE: `{summary['source_codes_missing_database_count']}`",
        f"- Safe blank broad-2025 candidates needing review: `{len(summary['safe_blank_candidate_codes'])}`",
        "",
        "## permits_2025 Status Counts",
        "",
    ]
    for status, count in summary["permits_2025_status_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## permits_2025_draw Status Counts", ""])
    for status, count in summary["permits_2025_draw_status_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            str(summary["guardrail"]),
            "",
            "The many `DIFFERS` rows mean this 2024 draw-odds package is strong historical/model-target evidence, but it is not safe to blindly overwrite reviewed 2025 DATABASE values.",
        ]
    )
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    normalized, validation, summary = build_rows()
    fields = [
        "hunt_code",
        "boundary_id",
        "hunt_code_mapping_status",
        "boundary_id_mapping_status",
        "candidate_hunt_code",
        "candidate_boundary_id",
        "hunt_name",
        "database_hunt_name",
        "source_draw_year",
        "model_target_year",
        "source_file",
        "source_sha256",
        "source_page",
        "source_dataset",
        "dataset_family",
        "parse_style",
        "resident_total_permits",
        "nonresident_total_permits",
        "total_public_draw_permits",
    ]
    validation_fields = fields + [
        "database_species",
        "database_weapon",
        "database_hunt_type",
        "database_permits_2025_res",
        "database_permits_2025_nr",
        "database_permits_2025_total",
        "database_permits_2025_source",
        "database_permits_2025_draw_res",
        "database_permits_2025_draw_nr",
        "database_permits_2025_draw_total",
        "database_permits_2025_draw_source",
        "permits_2025_comparison_status",
        "permits_2025_draw_comparison_status",
        "promotion_recommendation",
    ]
    write_csv(NORMALIZED_OUT, normalized, fields)
    write_csv(VALIDATION_OUT, validation, validation_fields)
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
