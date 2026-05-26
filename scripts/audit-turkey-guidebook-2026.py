from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Turkey.pdf"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"
OUT_DIR = ROOT / "data_truth/regulations_truth/normalized"
REPORT_DIR = ROOT / "processed_data"

TEXT_LINES_CSV = OUT_DIR / "2026_turkey_guidebook_text_lines.csv"
NUMBER_TOKENS_CSV = OUT_DIR / "2026_turkey_guidebook_number_tokens.csv"
EXPECTED_TEXT_CHECKS_CSV = OUT_DIR / "2026_turkey_guidebook_expected_text_checks.csv"
HUNT_CODE_RECONCILIATION_CSV = OUT_DIR / "2026_turkey_guidebook_hunt_code_name_reconciliation.csv"
SUMMARY = REPORT_DIR / "2026_turkey_guidebook_audit.json"
REPORT_MD = REPORT_DIR / "2026_turkey_guidebook_audit.md"

SOURCE_PATH = "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Turkey.pdf"
EXPECTED_SHA256 = "c2d54eff8304c6b93d549cc59cba17a5df2cb0fcc22cb723d3befc088beab149"
EXPECTED_SIZE_BYTES = 1_645_889
EXPECTED_PDF_PAGES = 45

CODE_RE = re.compile(r"\b(?:TK\d{4}|TKY)\b")
DATE_TOKEN_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+"
    r"\d{1,2}(?:\s*[-–]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+)?\d{1,2})?"
    r"(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
CODE_CITATION_RE = re.compile(r"\b(?:R657-\d+[a-z]?(?:-\d+)?|23A-\d+-\d+|76-\d+-\d+|50 CFR \d+\.\d+)\b")
NUMBER_TOKEN_RE = re.compile(r"\$?\b\d+(?:,\d{3})*(?:\.\d+)?%?\b|\b\d{1,2}:\d{2}\b|\bTK\d{4}\b|\bTKY\b")


@dataclass(frozen=True)
class ExpectedTextCheck:
    check_id: str
    printed_page: str
    expected_text: str
    source_note: str


@dataclass(frozen=True)
class GuidebookCode:
    code: str
    guidebook_name: str
    code_type: str
    guidebook_context: str


EXPECTED_TEXT_CHECKS = [
    ExpectedTextCheck("cover_title", "1", "2025-26 GROUSE HARE PARTRIDGE PHEASANT PTARMIGAN QUAIL RABBIT TURKEY", "cover"),
    ExpectedTextCheck("contents_key_dates", "2", "7 Key dates and fees", "contents"),
    ExpectedTextCheck("contents_turkey_permits", "2", "17 Turkey permits", "contents"),
    ExpectedTextCheck("contents_season_dates", "2", "37 Season dates, bag and possession", "contents"),
    ExpectedTextCheck("utip_phone", "2", "Phone: 800-662-3337", "contact block"),
    ExpectedTextCheck("utip_text", "2", "Text: 847411", "contact block"),
    ExpectedTextCheck("migratory_game_moved", "3", "Migratory game birds have moved", "what's new"),
    ExpectedTextCheck("turkey_drawing_dates", "3", "the application period runs from Dec. 16-30, 2025", "what's new"),
    ExpectedTextCheck("nonresident_fee_increase", "4", "Nonresident fee increase", "what's new"),
    ExpectedTextCheck("wma_license_requirement", "4", "License required to access WMAs", "what's new"),
    ExpectedTextCheck("fall_management_harvest", "5", "Fall turkey management harvest hunt", "reminders"),
    ExpectedTextCheck("air_rifles_allowed", "5", "Air rifles allowed for specific hunts", "reminders"),
    ExpectedTextCheck("turkey_limited_fee", "7", "Turkey limited-entry permit $40", "fees"),
    ExpectedTextCheck("turkey_general_fee", "7", "Turkey general-season permit $40", "fees"),
    ExpectedTextCheck("application_fee", "7", "Application fee", "fees"),
    ExpectedTextCheck("fall_2025_dates", "7", "Fall 2025 turkey hunts", "season dates"),
    ExpectedTextCheck("spring_limited_dates", "7", "April 11-30, 2026", "season dates"),
    ExpectedTextCheck("spring_youth_dates", "7", "May 1-3, 2026", "season dates"),
    ExpectedTextCheck("spring_general_dates", "7", "May 4-31, 2026", "season dates"),
    ExpectedTextCheck("turkey_apply_dec_16", "7", "Limited-entry applications Dec. 16, 2025", "application dates"),
    ExpectedTextCheck("turkey_deadline_dec_30", "7", "Application deadline Dec. 30, 2025", "application dates"),
    ExpectedTextCheck("turkey_results_jan_8", "7", "Drawing results available Jan. 8, 2026", "application dates"),
    ExpectedTextCheck("remaining_permits_march_10", "7", "Remaining limited-entry March 10, 2026", "application dates"),
    ExpectedTextCheck("hunter_education", "9", "Is hunter education gov/huntereducation", "basic requirements"),
    ExpectedTextCheck("trial_hunting", "11", "Utah's Trial Hunting Program", "basic requirements"),
    ExpectedTextCheck("upland_permit_species", "12", "Greater sage-grouse", "upland permits"),
    ExpectedTextCheck("application_website_change", "16", "utah-hunt.com utahdraws.com", "application website"),
    ExpectedTextCheck("turkey_permit_types", "17", "Limited-entry permits (spring)", "turkey permits"),
    ExpectedTextCheck("turkey_one_spring_permit", "17", "You may obtain one permit for", "turkey permits"),
    ExpectedTextCheck("youth_limited_entry", "18", "Fifteen percent of Utah's turkey limited-entry", "youth turkey"),
    ExpectedTextCheck("turkey_application_fee_2026", "19", "$10 for residents and $21 for nonresidents", "application fees"),
    ExpectedTextCheck("waiting_periods", "19", "Waiting periods do not apply to turkey", "bonus points"),
    ExpectedTextCheck("fall_management_regions", "21", "Central Region, Oct. 1, 2025-Feb. 28, 2026", "fall management"),
    ExpectedTextCheck("utahdraws", "22", "From Dec. 16-30, 2025, residents and", "application instructions"),
    ExpectedTextCheck("march_10_remaining", "23", "March 10: Spring general-season", "remaining permits"),
    ExpectedTextCheck("cwmu_program", "23", "Cooperative Wildlife Management Unit permits", "CWMU permits"),
    ExpectedTextCheck("wild_turkey_weapons", "24", "You may hunt and harvest a turkey", "field regulations"),
    ExpectedTextCheck("air_rifle_2000", "24", "minimum of 2,000 per square inch", "field regulations"),
    ExpectedTextCheck("areas_closed_turkey", "26", "Areas closed to turkey hunting", "field regulations"),
    ExpectedTextCheck("baiting", "28", "upland game or wild turkey by baiting", "hunting methods"),
    ExpectedTextCheck("electronic_calls", "29", "You may not use drones, live decoys, recorded", "hunting methods"),
    ExpectedTextCheck("tagging_requirements", "31", "You must tag the carcass of a greater sage-grouse", "possession"),
    ExpectedTextCheck("head_and_beard", "32", "the head and beard (if applicable) of the turkey", "transport"),
    ExpectedTextCheck("wma_rules", "35", "WILDLIFE MANAGEMENT AREA RULES", "WMA rules"),
    ExpectedTextCheck("wild_turkey_fall", "38", "Wild turkey (Fall management harvest hunts)", "turkey hunt tables"),
    ExpectedTextCheck("limited_entry_codes", "39", "Central (TK1003), Northeastern (TK1004), Northern (TK1005), Southeastern", "limited entry codes"),
    ExpectedTextCheck("southern_code", "39", "(TK1006) and Southern (TK1007) areas", "limited entry codes"),
    ExpectedTextCheck("bonus_point_tky", "39", "To apply for a bonus point, use the code TKY", "bonus point code"),
    ExpectedTextCheck("cwmu_codes", "39", "Pahvant Ensign (TK1018) and East Zion (TK1021)", "CWMU codes"),
    ExpectedTextCheck("shooting_hours", "42", "Shooting hours for all upland game species", "shooting hours"),
    ExpectedTextCheck("wild_turkey_identification", "46", "There are two subspecies of wild turkey in Utah", "species identification"),
    ExpectedTextCheck("turkey_age", "51", "DETERMINING A SPRING TURKEY'S AGE", "turkey age"),
    ExpectedTextCheck("definition_resident", "53", "Resident means a person who has a domicile", "definitions"),
]

GUIDEBOOK_CODES = [
    GuidebookCode("TK1003", "Central", "hunt_code", "limited-entry area"),
    GuidebookCode("TK1004", "Northeastern", "hunt_code", "limited-entry area"),
    GuidebookCode("TK1005", "Northern", "hunt_code", "limited-entry area"),
    GuidebookCode("TK1006", "Southeastern", "hunt_code", "limited-entry area"),
    GuidebookCode("TK1007", "Southern", "hunt_code", "limited-entry area"),
    GuidebookCode("TK1018", "Pahvant Ensign", "hunt_code", "CWMU area"),
    GuidebookCode("TK1021", "East Zion", "hunt_code", "CWMU area"),
    GuidebookCode("TKY", "Turkey bonus point", "bonus_point_code", "bonus point application code"),
]


def normalized(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2022", " ")
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u00a0", " ")
    text = re.sub(r"-\s+", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_rows_by_code(path: Path) -> dict[str, list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows: dict[str, list[dict[str, str]]] = {}
        for row in csv.DictReader(handle):
            code = row.get("hunt_code", "")
            if code.startswith("TK"):
                rows.setdefault(code, []).append(row)
        return rows


def extract_lines() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for pdf_page, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for line_number, line in enumerate(text.splitlines(), start=1):
                clean_line = normalized(line)
                if not clean_line:
                    continue
                printed_page_match = re.match(r"^(\d{1,2})\b", clean_line)
                printed_page = printed_page_match.group(1) if printed_page_match else ""
                rows.append(
                    {
                        "source_file": SOURCE_PATH,
                        "source_sha256": EXPECTED_SHA256,
                        "pdf_page": str(pdf_page),
                        "printed_page": printed_page,
                        "line_number": str(line_number),
                        "text": clean_line,
                    }
                )
    return rows


def build_number_tokens(text_lines: list[dict[str, str]]) -> list[dict[str, str]]:
    token_rows: list[dict[str, str]] = []
    token_patterns = [
        ("date", DATE_TOKEN_RE),
        ("code_citation", CODE_CITATION_RE),
        ("number_money_code", NUMBER_TOKEN_RE),
    ]
    for line in text_lines:
        seen: set[tuple[str, str]] = set()
        for token_type, pattern in token_patterns:
            for match in pattern.finditer(line["text"]):
                token = match.group(0)
                key = (token_type, token)
                if key in seen:
                    continue
                seen.add(key)
                token_rows.append(
                    {
                        "source_file": line["source_file"],
                        "source_sha256": line["source_sha256"],
                        "pdf_page": line["pdf_page"],
                        "printed_page": line["printed_page"],
                        "line_number": line["line_number"],
                        "token_type": token_type,
                        "token": token,
                        "line_text": line["text"],
                    }
                )
    return token_rows


def build_expected_checks(all_text: str) -> list[dict[str, str]]:
    norm_text = normalized(all_text)
    rows: list[dict[str, str]] = []
    for check in EXPECTED_TEXT_CHECKS:
        expected = normalized(check.expected_text)
        rows.append(
            {
                "check_id": check.check_id,
                "printed_page": check.printed_page,
                "match_type": "contains",
                "expected_text": expected,
                "source_note": check.source_note,
                "status": "PASS" if expected in norm_text else "FAIL",
            }
        )
    return rows


def name_resolves(guidebook_name: str, database_name: str) -> bool:
    guide = normalized(guidebook_name).lower()
    database = normalized(database_name).lower()
    variants = {guide, f"{guide} area", f"{guide} cwmu"}
    return database in variants or guide in database


def build_hunt_code_reconciliation() -> list[dict[str, str]]:
    database_rows = read_rows_by_code(DATABASE)
    predictive_rows = read_rows_by_code(PREDICTIVE)
    rows: list[dict[str, str]] = []
    for guidebook_code in GUIDEBOOK_CODES:
        database_row = (database_rows.get(guidebook_code.code) or [{}])[0]
        predictive_row = (predictive_rows.get(guidebook_code.code) or [{}])[0]
        if guidebook_code.code_type == "bonus_point_code":
            status = "PASS_BONUS_POINT_CODE_NOT_DATABASE_HUNT"
            resolved = "true" if not database_row else "review"
        else:
            resolved = str(bool(database_row) and name_resolves(guidebook_code.guidebook_name, database_row.get("hunt_name", ""))).lower()
            status = "PASS" if resolved == "true" and predictive_row else "FAIL"
        rows.append(
            {
                "source_file": SOURCE_PATH,
                "source_sha256": EXPECTED_SHA256,
                "guidebook_code": guidebook_code.code,
                "code_type": guidebook_code.code_type,
                "guidebook_name": guidebook_code.guidebook_name,
                "guidebook_context": guidebook_code.guidebook_context,
                "database_present": str(bool(database_row)).lower(),
                "database_hunt_name": database_row.get("hunt_name", ""),
                "database_species": database_row.get("species", ""),
                "database_hunt_type": database_row.get("hunt_type", ""),
                "database_weapon": database_row.get("weapon", ""),
                "database_season": database_row.get("season", ""),
                "permits_2026_total": database_row.get("permits_2026_total", ""),
                "predictive_present": str(bool(predictive_row)).lower(),
                "predictive_hunt_name": predictive_row.get("hunt_name", ""),
                "name_resolution_status": resolved,
                "status": status,
            }
        )
    return rows


def main() -> int:
    actual_sha = sha256(SOURCE_PDF)
    text_lines = extract_lines()
    all_text = "\n".join(row["text"] for row in text_lines)
    number_tokens = build_number_tokens(text_lines)
    expected_checks = build_expected_checks(all_text)
    reconciliation_rows = build_hunt_code_reconciliation()
    database_codes = set(read_rows_by_code(DATABASE))
    guidebook_hunt_codes = {row["guidebook_code"] for row in reconciliation_rows if row["code_type"] == "hunt_code"}
    token_counts = Counter(row["token_type"] for row in number_tokens)

    write_rows(TEXT_LINES_CSV, ["source_file", "source_sha256", "pdf_page", "printed_page", "line_number", "text"], text_lines)
    write_rows(
        NUMBER_TOKENS_CSV,
        ["source_file", "source_sha256", "pdf_page", "printed_page", "line_number", "token_type", "token", "line_text"],
        number_tokens,
    )
    write_rows(
        EXPECTED_TEXT_CHECKS_CSV,
        ["check_id", "printed_page", "match_type", "expected_text", "source_note", "status"],
        expected_checks,
    )
    write_rows(
        HUNT_CODE_RECONCILIATION_CSV,
        [
            "source_file",
            "source_sha256",
            "guidebook_code",
            "code_type",
            "guidebook_name",
            "guidebook_context",
            "database_present",
            "database_hunt_name",
            "database_species",
            "database_hunt_type",
            "database_weapon",
            "database_season",
            "permits_2026_total",
            "predictive_present",
            "predictive_hunt_name",
            "name_resolution_status",
            "status",
        ],
        reconciliation_rows,
    )

    failed_checks = [row for row in expected_checks if row["status"] != "PASS"]
    failed_reconciliation = [row for row in reconciliation_rows if not row["status"].startswith("PASS")]
    blockers = []
    if actual_sha != EXPECTED_SHA256:
        blockers.append("source_sha256_mismatch")
    if SOURCE_PDF.stat().st_size != EXPECTED_SIZE_BYTES:
        blockers.append("source_size_mismatch")
    if failed_checks:
        blockers.append("expected_text_anchor_failures")
    if failed_reconciliation:
        blockers.append("hunt_code_name_reconciliation_failures")

    extra_database_codes = sorted(database_codes - guidebook_hunt_codes)
    summary = {
        "classification": "REGULATION_AND_GUIDEBOOK_TRUTH_SOURCE_AUDIT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_pdf": SOURCE_PATH,
        "guidebook_title": "2025-26 Utah Upland Game and Turkey Guidebook",
        "source_sha256": actual_sha,
        "expected_sha256": EXPECTED_SHA256,
        "source_size_bytes": SOURCE_PDF.stat().st_size,
        "expected_size_bytes": EXPECTED_SIZE_BYTES,
        "pdf_pages": EXPECTED_PDF_PAGES,
        "text_lines": len(text_lines),
        "number_tokens": len(number_tokens),
        "token_type_counts": dict(sorted(token_counts.items())),
        "expected_text_checks": len(expected_checks),
        "expected_text_anchor_failures": len(failed_checks),
        "guidebook_printed_hunt_code_count": len(guidebook_hunt_codes),
        "guidebook_bonus_point_codes": ["TKY"],
        "database_name_resolved_hunt_code_count": sum(
            1 for row in reconciliation_rows if row["code_type"] == "hunt_code" and row["name_resolution_status"] == "true"
        ),
        "hunt_code_reconciliation_failures": len(failed_reconciliation),
        "extra_database_turkey_codes_not_printed_in_guidebook_code_list": extra_database_codes,
        "blockers": len(blockers),
        "blocker_reasons": blockers,
        "guardrail": "Turkey guidebook text, dates, fees, printed hunt codes, and bonus-point codes are truth-source references; this audit does not model draw odds.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# 2026 Turkey Guidebook Audit",
                "",
                f"- Source PDF: `{SOURCE_PATH}`",
                f"- Source SHA-256: `{actual_sha}`",
                f"- PDF pages: `{EXPECTED_PDF_PAGES}`",
                f"- Extracted text lines: `{len(text_lines)}`",
                f"- Extracted number/date/code tokens: `{len(number_tokens)}`",
                f"- Expected pasted-data anchor checks: `{len(expected_checks)}`",
                f"- Anchor failures: `{len(failed_checks)}`",
                f"- Printed turkey hunt codes checked: `{len(guidebook_hunt_codes)}`",
                f"- Database name-resolved printed hunt codes: `{summary['database_name_resolved_hunt_code_count']}`",
                f"- Bonus-point code handled separately: `TKY`",
                f"- Blockers: `{len(blockers)}`",
                "",
                "Guidebook labels such as `Central (TK1003)` resolve to database names such as `Central Area`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
