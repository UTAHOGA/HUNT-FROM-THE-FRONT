from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]

SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2024/pdf/draw_odds/2023 DEER ODDS.pdf"
SOURCE_LONG_CSV = ROOT / "pipeline/RAW/hunt_unit_database/2024/csv/draw_results_2023_for_2024_long.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
POINT_LADDER = ROOT / "processed_data/point_ladder_view.csv"
DRAW_REALITY = ROOT / "processed_data/draw_reality_engine.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"
GAP_SCAN = ROOT / "processed_data/2026_hunt_code_family_gap_scan.csv"

DRAW_EXTRACT_DIR = ROOT / "data_truth/draw_results_truth/extracted"
VALIDATION_DIR = ROOT / "data_truth/draw_results_truth/validation"
REPORT_DIR = ROOT / "processed_data"

TEXT_LINES_CSV = DRAW_EXTRACT_DIR / "2023_deer_odds_text_lines.csv"
HUNT_HEADERS_CSV = DRAW_EXTRACT_DIR / "2023_deer_odds_hunt_headers.csv"
CODE_RECONCILIATION_CSV = VALIDATION_DIR / "2026_deer_hunt_code_reconciliation.csv"
PROMOTION_DETAIL_CSV = REPORT_DIR / "2026_deer_predictive_v2_reference_promotion.csv"
AUDIT_JSON = REPORT_DIR / "2023_deer_odds_audit.json"
AUDIT_MD = REPORT_DIR / "2023_deer_odds_audit.md"
PROMOTION_JSON = REPORT_DIR / "2026_deer_predictive_v2_reference_promotion_summary.json"
RECONCILIATION_JSON = REPORT_DIR / "2026_deer_hunt_code_reconciliation_summary.json"
RECONCILIATION_MD = REPORT_DIR / "2026_deer_hunt_code_reconciliation.md"

SOURCE_PATH = "pipeline/RAW/hunt_unit_database/2024/pdf/draw_odds/2023 DEER ODDS.pdf"
SOURCE_LONG_CSV_PATH = "pipeline/RAW/hunt_unit_database/2024/csv/draw_results_2023_for_2024_long.csv"
EXPECTED_SHA256 = "4188e4c1b712ec1c4973b735b6cb06e489680f15a1b2011857046b49707efabf"
EXPECTED_SIZE_BYTES = 1_028_367
EXPECTED_PAGES = 190
EXPECTED_TEXT_LINES = 7_220
EXPECTED_HUNT_HEADERS = 189
EXPECTED_LONG_CSV_ROWS = 11_718

TARGET_PREFIXES = {"DB", "LO"}
DRAW_RESULT_PREFIXES = {"DB"}
REFERENCE_MODEL_VERSION = "deer_reference_v1.0.0"
REFERENCE_RULE_VERSION = "utah_deer_code_resolution_v1.0.0"
DATA_CUTOFF_DATE = "2026-05-24"

HUNT_RE = re.compile(r"Hunt:\s+([A-Z]{2}\d{4})\s+(.+?)(?:\s+Page\s+(\d+))?$")


@dataclass(frozen=True)
class HuntHeader:
    source_file: str
    source_sha256: str
    source_page: int
    source_report_page: str
    hunt_code: str
    hunt_name: str
    code_prefix: str
    raw_hunt_line: str


def normalized(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u00a0", " ")
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip()


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def code_prefix(code: str) -> str:
    match = re.match(r"^[A-Z]+", code or "")
    return match.group(0) if match else ""


def extract_pdf_text_lines() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for line_number, line in enumerate((page.extract_text() or "").splitlines(), start=1):
                text = normalized(line)
                if not text:
                    continue
                rows.append(
                    {
                        "source_file": SOURCE_PATH,
                        "source_sha256": EXPECTED_SHA256,
                        "source_page": page_number,
                        "line_number": line_number,
                        "text": text,
                    }
                )
    return rows


def parse_hunt_headers() -> list[HuntHeader]:
    headers: list[HuntHeader] = []
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for raw_line in (page.extract_text() or "").splitlines():
                line = normalized(raw_line)
                match = HUNT_RE.search(line)
                if not match:
                    continue
                code = match.group(1).strip().upper()
                headers.append(
                    HuntHeader(
                        source_file=SOURCE_PATH,
                        source_sha256=EXPECTED_SHA256,
                        source_page=page_number,
                        source_report_page=match.group(3) or "",
                        hunt_code=code,
                        hunt_name=match.group(2).strip(),
                        code_prefix=code_prefix(code),
                        raw_hunt_line=line,
                    )
                )
    return headers


def rows_by_code(path: Path, prefixes: set[str] | None = None) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_rows(path):
        code = row.get("hunt_code", "").strip()
        if not code:
            continue
        if prefixes and code_prefix(code) not in prefixes:
            continue
        grouped.setdefault(code, []).append(row)
    return grouped


def missing_predictive_codes_from_gap_scan() -> set[str]:
    missing: set[str] = set()
    for row in read_rows(GAP_SCAN):
        if row["code_prefix"] not in TARGET_PREFIXES:
            continue
        missing.update(code for code in row.get("missing_predictive_v2_codes", "").split(";") if code)
    return missing


def choose_residency(database_row: dict[str, str]) -> str:
    res = database_row.get("permits_2026_res", "").strip()
    nr = database_row.get("permits_2026_nr", "").strip()
    if nr and not res:
        return "Nonresident"
    return "Resident"


def source_basis_for(database_row: dict[str, str], draw_header_codes: set[str]) -> str:
    code = database_row.get("hunt_code", "")
    if code in draw_header_codes:
        return "prior_2023_deer_draw_results"
    if code_prefix(code) == "LO":
        return "current_2026_private_land_reference_only"
    hunt_type = database_row.get("hunt_type", "").lower()
    hunt_name = database_row.get("hunt_name", "").lower()
    if "tribal" in hunt_type or "navajo" in hunt_name or "paiute" in hunt_name:
        return "current_2026_tribal_reference_only"
    if "conservation" in hunt_type or "conservation" in hunt_name or "expo" in hunt_type or "expo" in hunt_name:
        return "current_2026_special_permit_reference_only"
    return "current_2026_database_reference_only"


def build_reference_row(fieldnames: list[str], database_row: dict[str, str], source_basis: str) -> dict[str, str]:
    row = {fieldname: "" for fieldname in fieldnames}
    code = database_row["hunt_code"]
    prefix = code_prefix(code)
    total_permits = database_row.get("permits_2026_total", "")
    if prefix == "LO":
        draw_system_type = "PRIVATE_LAND_DEER_REFERENCE"
        draw_pool = "private_land_deer_reference"
    else:
        draw_system_type = "DEER_REFERENCE"
        draw_pool = "deer_reference"
    reason = (
        "Promoted from current 2026 deer reference coverage"
        f" with source basis {source_basis}; no draw-odds probability was invented."
    )
    row.update(
        {
            "year": "2026",
            "forecast_year": "2026",
            "hunt_code": code,
            "hunt_name": database_row.get("hunt_name", ""),
            "species": database_row.get("species", "Deer") or "Deer",
            "sex_type": database_row.get("sex_type", ""),
            "hunt_type": database_row.get("hunt_type", ""),
            "hunt_class": "Deer Reference",
            "residency": choose_residency(database_row),
            "points": "0",
            "draw_pool": draw_pool,
            "source_years_used": "2023;2026",
            "source_year_count": "2",
            "latest_source_year": "2026",
            "earliest_source_year": "2023",
            "source_dataset": "2026_deer_hunt_code_reconciliation",
            "model_strategy": "DEER_REFERENCE",
            "draw_system_type": draw_system_type,
            "season_dates": database_row.get("season", ""),
            "weapon": database_row.get("weapon", ""),
            "algorithm_status": "DEER_REFERENCE",
            "target_scope": "TARGET",
            "modeled_by_engine": "False",
            "reason": reason,
            "model_version": REFERENCE_MODEL_VERSION,
            "rule_version": REFERENCE_RULE_VERSION,
            "public_permits_2026": total_permits,
            "quota_source_status": "official_database_reference",
            "quota_source_year": "2026",
            "quota_source_file": "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
            "quota_2026_total": total_permits,
            "permit_allotment_2026_res": database_row.get("permits_2026_res", ""),
            "permit_allotment_2026_nr": database_row.get("permits_2026_nr", ""),
            "permit_allotment_2026_total": total_permits,
            "permit_allotment_2026_source": "DATABASE",
            "permit_allotment_2026_source_file": "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
            "permit_allotment_2026_status": "official_database_reference",
            "data_cutoff_date": DATA_CUTOFF_DATE,
            "reason_codes": "DEER_CURRENT_DATABASE_REFERENCE|NO_PREDICTIVE_DRAW_MODEL_ROW|NO_DRAW_PROBABILITY_INVENTED",
            "status": "deer_reference_no_draw_odds",
            "trend": "not_modeled",
            "permit_availability_type": draw_pool,
            "probability_model": "NONE",
            "rule_status": "deer_reference",
            "availability_status": "deer_reference",
            "data_quality_flags": "PROMOTED_DEER_REFERENCE_CODE;NO_DRAW_PROBABILITY_MODELED",
            "prediction_year": "2026",
            "source_year": "2026",
            "applicant_forecast_method": "not_modeled_deer_reference",
            "display_odds_text": "Deer reference only; odds not modeled",
            "data_quality_grade": "A",
        }
    )
    if not total_permits:
        row["public_permits_2026"] = ""
        row["quota_2026_total"] = ""
        row["permit_allotment_2026_total"] = ""
    return row


def build_reconciliation_rows(headers: list[HuntHeader]) -> list[dict[str, object]]:
    draw_header_codes = {header.hunt_code for header in headers if header.code_prefix in DRAW_RESULT_PREFIXES}
    database_rows = rows_by_code(DATABASE, TARGET_PREFIXES)
    hunt_master_rows = rows_by_code(HUNT_MASTER, TARGET_PREFIXES)
    point_ladder_rows = rows_by_code(POINT_LADDER, TARGET_PREFIXES)
    draw_reality_rows = rows_by_code(DRAW_REALITY, TARGET_PREFIXES)
    predictive_rows = rows_by_code(PREDICTIVE, TARGET_PREFIXES)
    codes = sorted(set(database_rows) | draw_header_codes)
    rows: list[dict[str, object]] = []
    for code in codes:
        database_row = (database_rows.get(code) or [{}])[0]
        current_database = bool(database_row)
        source_basis = source_basis_for(database_row | {"hunt_code": code}, draw_header_codes) if current_database else "prior_2023_deer_draw_results_not_current_2026"
        current_failure = current_database and not (
            code in hunt_master_rows and code in point_ladder_rows and code in draw_reality_rows and code in predictive_rows
        )
        rows.append(
            {
                "hunt_code": code,
                "code_prefix": code_prefix(code),
                "hunt_name": database_row.get("hunt_name", ""),
                "species": database_row.get("species", ""),
                "hunt_type": database_row.get("hunt_type", ""),
                "weapon": database_row.get("weapon", ""),
                "season": database_row.get("season", ""),
                "permits_2026_total": database_row.get("permits_2026_total", ""),
                "present_in_2023_deer_odds_pdf": str(code in draw_header_codes).lower(),
                "database_present": str(current_database).lower(),
                "hunt_master_present": str(code in hunt_master_rows).lower(),
                "point_ladder_present": str(code in point_ladder_rows).lower(),
                "draw_reality_present": str(code in draw_reality_rows).lower(),
                "predictive_v2_present": str(code in predictive_rows).lower(),
                "source_basis": source_basis,
                "current_database_reconciliation_status": "FAIL" if current_failure else "PASS",
            }
        )
    return rows


def promote_missing_reference_rows(reconciliation_rows: list[dict[str, object]], draw_header_codes: set[str]) -> dict[str, object]:
    missing_codes = missing_predictive_codes_from_gap_scan()
    database_rows = {
        row["hunt_code"]: row
        for row in read_rows(DATABASE)
        if code_prefix(row.get("hunt_code", "")) in TARGET_PREFIXES
    }
    predictive_rows = read_rows(PREDICTIVE)
    existing_codes = {
        row["hunt_code"]
        for row in predictive_rows
        if code_prefix(row.get("hunt_code", "")) in TARGET_PREFIXES
    }
    with PREDICTIVE.open(newline="", encoding="utf-8-sig") as handle:
        fieldnames = csv.DictReader(handle).fieldnames or []

    to_promote = sorted(code for code in missing_codes if code in database_rows and code not in existing_codes)
    promoted_rows = [
        build_reference_row(fieldnames, database_rows[code], source_basis_for(database_rows[code], draw_header_codes))
        for code in to_promote
    ]
    if promoted_rows:
        predictive_rows.extend(promoted_rows)
        write_rows(PREDICTIVE, fieldnames, predictive_rows)

    final_rows = read_rows(PREDICTIVE)
    final_codes = {
        row["hunt_code"]
        for row in final_rows
        if code_prefix(row.get("hunt_code", "")) in TARGET_PREFIXES
    }
    still_missing = sorted(code for code in missing_codes if code not in final_codes)
    reference_rows = [
        row
        for row in final_rows
        if row.get("model_version") == REFERENCE_MODEL_VERSION
        and code_prefix(row.get("hunt_code", "")) in TARGET_PREFIXES
    ]
    duplicate_keys = [
        key
        for key, count in Counter(
            (
                row.get("hunt_code", ""),
                row.get("residency", ""),
                row.get("points", ""),
                row.get("draw_pool", ""),
                row.get("model_version", ""),
            )
            for row in final_rows
        ).items()
        if count > 1
    ]
    detail_rows = [
        {
            "hunt_code": row.get("hunt_code", ""),
            "hunt_name": row.get("hunt_name", ""),
            "species": row.get("species", ""),
            "hunt_type": row.get("hunt_type", ""),
            "residency": row.get("residency", ""),
            "permits_2026_total": row.get("permit_allotment_2026_total", ""),
            "promotion_status": "PROMOTED",
            "reason": row.get("reason", ""),
        }
        for row in sorted(reference_rows, key=lambda item: item["hunt_code"])
    ]
    write_rows(
        PROMOTION_DETAIL_CSV,
        ["hunt_code", "hunt_name", "species", "hunt_type", "residency", "permits_2026_total", "promotion_status", "reason"],
        detail_rows,
    )
    prefix_counts = Counter(code_prefix(row["hunt_code"]) for row in reference_rows)
    summary = {
        "classification": "DEER_REFERENCE_PROMOTION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefixes": sorted(TARGET_PREFIXES),
        "initial_missing_predictive_hunt_code_count": len(missing_codes),
        "newly_promoted_hunt_code_count": len(promoted_rows),
        "promoted_reference_hunt_code_count": len({row["hunt_code"] for row in reference_rows}),
        "promoted_reference_prefix_counts": dict(sorted(prefix_counts.items())),
        "still_missing_predictive_hunt_code_count": len(still_missing),
        "duplicate_reference_key_count": len(duplicate_keys),
        "newly_promoted_hunt_codes": [row["hunt_code"] for row in promoted_rows],
        "promoted_reference_hunt_codes": sorted({row["hunt_code"] for row in reference_rows}),
        "still_missing_predictive_hunt_codes": still_missing,
        "guardrail": "Deer reference rows promote current hunt-code coverage only; no draw odds or probability fields are invented.",
    }
    PROMOTION_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    actual_sha = sha256(SOURCE_PDF)
    text_lines = extract_pdf_text_lines()
    headers = parse_hunt_headers()
    write_rows(TEXT_LINES_CSV, ["source_file", "source_sha256", "source_page", "line_number", "text"], text_lines)
    write_rows(
        HUNT_HEADERS_CSV,
        list(asdict(headers[0]).keys()) if headers else [],
        [asdict(header) for header in headers],
    )

    long_rows = read_rows(SOURCE_LONG_CSV)
    long_db_rows = [row for row in long_rows if code_prefix(row.get("hunt_code", "")) == "DB"]
    long_db_codes = {row["hunt_code"] for row in long_db_rows}
    header_codes = {header.hunt_code for header in headers}
    prefixes = Counter(header.code_prefix for header in headers)

    with pdfplumber.open(SOURCE_PDF) as pdf:
        page_count = len(pdf.pages)
    blockers: list[str] = []
    if actual_sha != EXPECTED_SHA256:
        blockers.append("source_sha256_mismatch")
    if SOURCE_PDF.stat().st_size != EXPECTED_SIZE_BYTES:
        blockers.append("source_size_mismatch")
    if page_count != EXPECTED_PAGES:
        blockers.append("page_count_mismatch")
    if len(text_lines) != EXPECTED_TEXT_LINES:
        blockers.append("text_line_count_mismatch")
    if len(headers) != EXPECTED_HUNT_HEADERS:
        blockers.append("hunt_header_count_mismatch")
    if len(long_db_rows) != EXPECTED_LONG_CSV_ROWS:
        blockers.append("long_csv_db_row_count_mismatch")
    if header_codes != long_db_codes:
        blockers.append("pdf_header_codes_do_not_match_long_csv_codes")

    audit_summary = {
        "classification": "DEER_DRAW_RESULTS_TRUTH_SOURCE_AUDIT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_pdf": SOURCE_PATH,
        "source_sha256": actual_sha,
        "expected_sha256": EXPECTED_SHA256,
        "source_size_bytes": SOURCE_PDF.stat().st_size,
        "expected_size_bytes": EXPECTED_SIZE_BYTES,
        "pdf_pages": page_count,
        "text_lines": len(text_lines),
        "hunt_header_rows": len(headers),
        "unique_hunt_header_codes": len(header_codes),
        "hunt_header_prefix_counts": dict(sorted(prefixes.items())),
        "source_long_csv": SOURCE_LONG_CSV_PATH,
        "long_csv_db_rows": len(long_db_rows),
        "long_csv_unique_db_codes": len(long_db_codes),
        "pdf_header_codes_match_long_csv_codes": header_codes == long_db_codes,
        "reported_draw_year": 2023,
        "model_target_year": 2024,
        "blockers": len(blockers),
        "blocker_reasons": blockers,
        "guardrail": "2023 deer odds rows are prior draw truth; this audit does not forecast or alter probability math.",
    }
    AUDIT_JSON.write_text(json.dumps(audit_summary, indent=2) + "\n", encoding="utf-8")
    AUDIT_MD.write_text(
        "\n".join(
            [
                "# 2023 Deer Odds Audit",
                "",
                f"- Source PDF: `{SOURCE_PATH}`",
                f"- Source SHA-256: `{actual_sha}`",
                f"- PDF pages: `{page_count}`",
                f"- Extracted text lines: `{len(text_lines)}`",
                f"- Parsed hunt headers: `{len(headers)}`",
                f"- Long CSV DB rows: `{len(long_db_rows)}`",
                f"- PDF headers match long CSV DB codes: `{str(header_codes == long_db_codes).lower()}`",
                f"- Blockers: `{len(blockers)}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    pre_reconciliation_rows = build_reconciliation_rows(headers)
    promotion_summary = promote_missing_reference_rows(pre_reconciliation_rows, header_codes)
    reconciliation_rows = build_reconciliation_rows(headers)
    write_rows(
        CODE_RECONCILIATION_CSV,
        [
            "hunt_code",
            "code_prefix",
            "hunt_name",
            "species",
            "hunt_type",
            "weapon",
            "season",
            "permits_2026_total",
            "present_in_2023_deer_odds_pdf",
            "database_present",
            "hunt_master_present",
            "point_ladder_present",
            "draw_reality_present",
            "predictive_v2_present",
            "source_basis",
            "current_database_reconciliation_status",
        ],
        reconciliation_rows,
    )
    current_rows = [row for row in reconciliation_rows if row["database_present"] == "true"]
    failures = [row for row in current_rows if row["current_database_reconciliation_status"] != "PASS"]
    summary = {
        "classification": "DEER_HUNT_CODE_RECONCILIATION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_prefixes": sorted(TARGET_PREFIXES),
        "current_database_code_count": len(current_rows),
        "draw_results_2023_db_code_count": len(header_codes),
        "current_database_codes_present_in_2023_deer_odds_count": sum(
            1 for row in current_rows if row["present_in_2023_deer_odds_pdf"] == "true"
        ),
        "current_database_reconciliation_failure_count": len(failures),
        "current_database_reconciliation_failures": [row["hunt_code"] for row in failures],
        "promotion_summary": promotion_summary,
        "blockers": len(failures)
        + int(promotion_summary["still_missing_predictive_hunt_code_count"])
        + int(promotion_summary["duplicate_reference_key_count"])
        + len(blockers),
        "guardrail": "Deer code reconciliation resolves current database coverage without changing draw odds or model math.",
    }
    RECONCILIATION_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    RECONCILIATION_MD.write_text(
        "\n".join(
            [
                "# 2026 Deer Hunt-Code Reconciliation",
                "",
                f"- Target prefixes: `{', '.join(sorted(TARGET_PREFIXES))}`",
                f"- Current database codes checked: `{summary['current_database_code_count']}`",
                f"- 2023 Deer Odds DB codes parsed: `{summary['draw_results_2023_db_code_count']}`",
                f"- Current database codes present in 2023 Deer Odds: `{summary['current_database_codes_present_in_2023_deer_odds_count']}`",
                f"- Promoted reference codes present: `{promotion_summary['promoted_reference_hunt_code_count']}`",
                f"- Still missing predictive codes: `{promotion_summary['still_missing_predictive_hunt_code_count']}`",
                f"- Reconciliation failures: `{summary['current_database_reconciliation_failure_count']}`",
                f"- Blockers: `{summary['blockers']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 1 if summary["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
