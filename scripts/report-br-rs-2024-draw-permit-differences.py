from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

AUDIT_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits.csv"
)
IMPORTED_RM_SHEEP_PDF = (
    ROOT
    / "pipeline/RAW/hunt_unit_database/2025/pdf/harvest_report/rocky mountain sheep/"
    / "r.m. sheep 2024 harvest by unit.pdf"
)

DIFF_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_model_target_2025_permit_differences.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "br_rs_2024_model_target_2025_permit_differences_summary.json"
)
REPORT_MD = ROOT / "processed_data/br_rs_2024_model_target_2025_permit_differences.md"
IMPORT_MANIFEST_CSV = (
    ROOT
    / "data_truth/harvest_results_truth/raw_inventory/"
    / "imported_rm_sheep_2024_harvest_source.csv"
)
IMPORT_MANIFEST_JSON = (
    ROOT
    / "data_truth/harvest_results_truth/raw_inventory/"
    / "imported_rm_sheep_2024_harvest_source_summary.json"
)


def int_or_blank(value: str | None) -> int | None:
    text = (value or "").strip()
    if text == "":
        return None
    return int(text)


def text(value: Any) -> str:
    return "" if value is None else str(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: text(row.get(field, "")) for field in fieldnames})


def build_import_manifest(generated_at: str) -> dict[str, Any]:
    if not IMPORTED_RM_SHEEP_PDF.exists():
        raise FileNotFoundError(f"Imported RM sheep harvest PDF missing: {IMPORTED_RM_SHEEP_PDF}")

    rel_path = IMPORTED_RM_SHEEP_PDF.relative_to(ROOT).as_posix()
    source_sha256 = sha256_file(IMPORTED_RM_SHEEP_PDF)
    row = {
        "source_file": rel_path,
        "source_sha256": source_sha256,
        "inferred_species": "Rocky Mountain Bighorn Sheep",
        "inferred_year": "2024",
        "reported_hunt_year_inferred": "2024",
        "model_target_year": "2025",
        "source_class": "harvest_results",
        "report_type": "harvest_by_unit",
        "file_size_bytes": IMPORTED_RM_SHEEP_PDF.stat().st_size,
        "promotion_status": "IMPORTED_NOT_EXTRACTED",
        "quality_engine_use": "MAYBE",
        "draw_engine_use": "NO",
        "extraction_priority": "MEDIUM",
        "extraction_strategy": "manual_review_needed",
        "confidence": "HIGH",
        "reason": "Imported from HUNTS raw library for future RM sheep harvest-quality extraction; no harvest values parsed in this step.",
    }
    fieldnames = list(row.keys())
    write_csv(IMPORT_MANIFEST_CSV, [row], fieldnames)

    summary = {
        "artifact": "imported_rm_sheep_2024_harvest_source",
        "generated_at_utc": generated_at,
        "imported_source_count": 1,
        "guardrail": "Import manifest only. No harvest values were parsed and no DATABASE.csv values were modified.",
        "source_file": rel_path,
        "source_sha256": source_sha256,
        "outputs": {
            "manifest_csv": IMPORT_MANIFEST_CSV.relative_to(ROOT).as_posix(),
            "summary_json": IMPORT_MANIFEST_JSON.relative_to(ROOT).as_posix(),
        },
    }
    IMPORT_MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    IMPORT_MANIFEST_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def build_difference_report(generated_at: str) -> dict[str, Any]:
    if not AUDIT_CSV.exists():
        raise FileNotFoundError(f"Missing source audit CSV: {AUDIT_CSV}")

    diff_rows: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    prefix_counts: dict[str, int] = {}
    missing_codes: list[str] = []

    with AUDIT_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            hunt_code = row["hunt_code"].strip()
            prefix = hunt_code[:2]
            if prefix not in {"BR", "RS"}:
                continue

            status = row["permits_2025_comparison_status"].strip()
            if status == "MATCH":
                continue

            source_total = int_or_blank(row["total_public_draw_permits"])
            db_total = int_or_blank(row["database_permits_2025_total"])
            source_res = int_or_blank(row["resident_total_permits"])
            db_res = int_or_blank(row["database_permits_2025_res"])
            source_nr = int_or_blank(row["nonresident_total_permits"])
            db_nr = int_or_blank(row["database_permits_2025_nr"])
            total_delta = None if source_total is None or db_total is None else source_total - db_total
            res_delta = None if source_res is None or db_res is None else source_res - db_res
            nr_delta = None if source_nr is None or db_nr is None else source_nr - db_nr

            status_counts[status] = status_counts.get(status, 0) + 1
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
            if status == "SOURCE_CODE_NOT_IN_DATABASE":
                missing_codes.append(hunt_code)

            diff_rows.append(
                {
                    "hunt_code": hunt_code,
                    "hunt_code_prefix": prefix,
                    "hunt_name": row["hunt_name"],
                    "database_hunt_name": row["database_hunt_name"],
                    "source_file": row["source_file"],
                    "source_page": row["source_page"],
                    "source_resident_permits": source_res,
                    "database_permits_2025_res": db_res,
                    "resident_delta_source_minus_database": res_delta,
                    "source_nonresident_permits": source_nr,
                    "database_permits_2025_nr": db_nr,
                    "nonresident_delta_source_minus_database": nr_delta,
                    "source_total_permits": source_total,
                    "database_permits_2025_total": db_total,
                    "total_delta_source_minus_database": total_delta,
                    "database_permits_2025_source": row["database_permits_2025_source"],
                    "permits_2025_comparison_status": status,
                    "promotion_recommendation": row["promotion_recommendation"],
                }
            )

    diff_rows.sort(key=lambda item: (item["hunt_code_prefix"], item["hunt_code"]))

    fieldnames = [
        "hunt_code",
        "hunt_code_prefix",
        "hunt_name",
        "database_hunt_name",
        "source_file",
        "source_page",
        "source_resident_permits",
        "database_permits_2025_res",
        "resident_delta_source_minus_database",
        "source_nonresident_permits",
        "database_permits_2025_nr",
        "nonresident_delta_source_minus_database",
        "source_total_permits",
        "database_permits_2025_total",
        "total_delta_source_minus_database",
        "database_permits_2025_source",
        "permits_2025_comparison_status",
        "promotion_recommendation",
    ]
    write_csv(DIFF_CSV, diff_rows, fieldnames)

    total_diff_only_count = sum(1 for row in diff_rows if row["permits_2025_comparison_status"] == "DIFFERS")
    summary = {
        "artifact": "br_rs_2024_model_target_2025_permit_differences",
        "generated_at_utc": generated_at,
        "source_audit_csv": AUDIT_CSV.relative_to(ROOT).as_posix(),
        "guardrail": "Read-only difference report. No DATABASE.csv values are modified.",
        "difference_row_count": len(diff_rows),
        "numeric_difference_count": total_diff_only_count,
        "status_counts": status_counts,
        "prefix_counts": prefix_counts,
        "source_codes_missing_database": missing_codes,
        "outputs": {
            "difference_csv": DIFF_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# BR/RS 2024 Draw Odds To 2025 Permit Differences",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Difference rows: `{len(diff_rows)}`",
        f"- Numeric differing rows: `{total_diff_only_count}`",
        f"- Source-code-not-in-database rows: `{len(missing_codes)}`",
        f"- BR differing/missing rows: `{prefix_counts.get('BR', 0)}`",
        f"- RS differing/missing rows: `{prefix_counts.get('RS', 0)}`",
        "",
        "Guardrail: this is a read-only audit. It does not overwrite populated 2025 permit fields in `DATABASE.csv`.",
        "",
        "## Missing Current Database Codes",
        "",
        ", ".join(f"`{code}`" for code in missing_codes) if missing_codes else "None.",
        "",
        "## Numeric Difference Rows",
        "",
        "| Hunt code | Source total | Database 2025 total | Delta | Source res/nr | Database res/nr | Hunt name |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for row in diff_rows:
        if row["permits_2025_comparison_status"] != "DIFFERS":
            continue
        lines.append(
            "| {hunt_code} | {source_total_permits} | {database_permits_2025_total} | "
            "{total_delta_source_minus_database} | {source_resident_permits}/{source_nonresident_permits} | "
            "{database_permits_2025_res}/{database_permits_2025_nr} | {hunt_name} |".format(**row)
        )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    import_summary = build_import_manifest(generated_at)
    diff_summary = build_difference_report(generated_at)
    print(json.dumps({"import": import_summary, "differences": diff_summary}, indent=2))


if __name__ == "__main__":
    main()
