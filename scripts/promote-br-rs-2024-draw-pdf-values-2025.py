from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DATABASE_CSV = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
DIFF_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_model_target_2025_permit_differences.csv"
)

PROMOTION_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_draw_pdf_values_promoted_to_DATABASE_2025.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_draw_pdf_values_promoted_to_DATABASE_2025_summary.json"
)
REPORT_MD = ROOT / "processed_data/br_rs_2024_draw_pdf_values_promoted_to_DATABASE_2025.md"

SOURCE_LABEL = "2024_DRAW_ODDS_PDF_VALUES_MODEL_TARGET_2025"

PERMIT_FIELDS = [
    ("source_resident_permits", "permits_2025_res"),
    ("source_nonresident_permits", "permits_2025_nr"),
    ("source_total_permits", "permits_2025_total"),
    ("source_resident_permits", "permits_2025_draw_res"),
    ("source_nonresident_permits", "permits_2025_draw_nr"),
    ("source_total_permits", "permits_2025_draw_total"),
]


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fieldnames})


def normalize_int_text(value: str | None) -> str:
    text = (value or "").strip()
    if text == "":
        return ""
    return str(int(text))


def main() -> None:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    db_rows, db_fields = read_csv(DATABASE_CSV)
    diff_rows, _ = read_csv(DIFF_CSV)
    db_by_code = {row["hunt_code"].strip(): row for row in db_rows}

    promotion_rows: list[dict[str, Any]] = []
    skipped_missing_rows: list[dict[str, Any]] = []
    changed_cell_count = 0
    promoted_codes: list[str] = []

    for diff in diff_rows:
        hunt_code = diff["hunt_code"].strip()
        status = diff["permits_2025_comparison_status"].strip()
        if status != "DIFFERS":
            if status == "SOURCE_CODE_NOT_IN_DATABASE":
                skipped_missing_rows.append(
                    {
                        "hunt_code": hunt_code,
                        "reason": "SOURCE_CODE_NOT_IN_DATABASE",
                        "source_total_permits": normalize_int_text(diff["source_total_permits"]),
                    }
                )
            continue

        if hunt_code not in db_by_code:
            skipped_missing_rows.append(
                {
                    "hunt_code": hunt_code,
                    "reason": "DIFF_ROW_CODE_NOT_IN_DATABASE",
                    "source_total_permits": normalize_int_text(diff["source_total_permits"]),
                }
            )
            continue

        db_row = db_by_code[hunt_code]
        before_values = {target: db_row.get(target, "") for _, target in PERMIT_FIELDS}
        after_values: dict[str, str] = {}

        for source_field, target_field in PERMIT_FIELDS:
            new_value = normalize_int_text(diff[source_field])
            after_values[target_field] = new_value
            if db_row.get(target_field, "") != new_value:
                changed_cell_count += 1
            db_row[target_field] = new_value

        source_before = db_row.get("permits_2025_source", "")
        draw_source_before = db_row.get("permits_2025_draw_source", "")
        if source_before != SOURCE_LABEL:
            changed_cell_count += 1
        if draw_source_before != SOURCE_LABEL:
            changed_cell_count += 1
        db_row["permits_2025_source"] = SOURCE_LABEL
        db_row["permits_2025_draw_source"] = SOURCE_LABEL

        if diff.get("source_page", "").strip():
            if db_row.get("draw_2025_bg_pdf_page", "") != diff["source_page"].strip():
                changed_cell_count += 1
            db_row["draw_2025_bg_pdf_page"] = diff["source_page"].strip()
        if db_row.get("draw_2025_type", "") != "2024 Draw Odds PDF Model Target 2025":
            changed_cell_count += 1
        db_row["draw_2025_type"] = "2024 Draw Odds PDF Model Target 2025"

        promoted_codes.append(hunt_code)
        promotion_rows.append(
            {
                "hunt_code": hunt_code,
                "hunt_code_prefix": diff["hunt_code_prefix"],
                "hunt_name": db_row.get("hunt_name", ""),
                "source_file": diff["source_file"],
                "source_page": diff["source_page"],
                "before_permits_2025_res": before_values["permits_2025_res"],
                "before_permits_2025_nr": before_values["permits_2025_nr"],
                "before_permits_2025_total": before_values["permits_2025_total"],
                "after_permits_2025_res": after_values["permits_2025_res"],
                "after_permits_2025_nr": after_values["permits_2025_nr"],
                "after_permits_2025_total": after_values["permits_2025_total"],
                "before_permits_2025_draw_res": before_values["permits_2025_draw_res"],
                "before_permits_2025_draw_nr": before_values["permits_2025_draw_nr"],
                "before_permits_2025_draw_total": before_values["permits_2025_draw_total"],
                "after_permits_2025_draw_res": after_values["permits_2025_draw_res"],
                "after_permits_2025_draw_nr": after_values["permits_2025_draw_nr"],
                "after_permits_2025_draw_total": after_values["permits_2025_draw_total"],
                "total_delta_source_minus_database_before": diff["total_delta_source_minus_database"],
                "source_label": SOURCE_LABEL,
            }
        )

    write_csv(DATABASE_CSV, db_rows, db_fields)

    promotion_fields = [
        "hunt_code",
        "hunt_code_prefix",
        "hunt_name",
        "source_file",
        "source_page",
        "before_permits_2025_res",
        "before_permits_2025_nr",
        "before_permits_2025_total",
        "after_permits_2025_res",
        "after_permits_2025_nr",
        "after_permits_2025_total",
        "before_permits_2025_draw_res",
        "before_permits_2025_draw_nr",
        "before_permits_2025_draw_total",
        "after_permits_2025_draw_res",
        "after_permits_2025_draw_nr",
        "after_permits_2025_draw_total",
        "total_delta_source_minus_database_before",
        "source_label",
    ]
    write_csv(PROMOTION_CSV, promotion_rows, promotion_fields)

    prefix_counts: dict[str, int] = {}
    for row in promotion_rows:
        prefix = row["hunt_code_prefix"]
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

    summary = {
        "artifact": "br_rs_2024_draw_pdf_values_promoted_to_DATABASE_2025",
        "generated_at_utc": generated_at,
        "database_csv": DATABASE_CSV.relative_to(ROOT).as_posix(),
        "source_difference_csv": DIFF_CSV.relative_to(ROOT).as_posix(),
        "source_label": SOURCE_LABEL,
        "guardrail": "Only active BR/RS rows with numeric DIFFERS status were promoted. Source-only missing DATABASE codes were not inserted.",
        "promoted_row_count": len(promotion_rows),
        "changed_cell_count": changed_cell_count,
        "prefix_counts": prefix_counts,
        "skipped_missing_database_count": len(skipped_missing_rows),
        "skipped_missing_database_codes": [row["hunt_code"] for row in skipped_missing_rows],
        "outputs": {
            "promotion_csv": PROMOTION_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# BR/RS 2024 Draw PDF Values Promoted To DATABASE 2025",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Promoted active rows: `{len(promotion_rows)}`",
        f"- Changed cells: `{changed_cell_count}`",
        f"- Prefix counts: `{prefix_counts}`",
        f"- Missing current database codes skipped: `{summary['skipped_missing_database_codes']}`",
        "",
        "PDF-derived draw values are now the database values for the promoted BR/RS active rows.",
        "No rows were inserted for source-only retired/current-absent hunt codes.",
        "",
        "| Hunt code | Before total | After total | Before draw total | After draw total | Source page |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in promotion_rows:
        lines.append(
            "| {hunt_code} | {before_permits_2025_total} | {after_permits_2025_total} | "
            "{before_permits_2025_draw_total} | {after_permits_2025_draw_total} | {source_page} |".format(**row)
        )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
