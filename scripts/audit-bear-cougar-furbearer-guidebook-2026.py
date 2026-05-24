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
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Bear Cougar Furbearer Guidebook.pdf"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"
OUT_DIR = ROOT / "data_truth/regulations_truth/normalized"
REPORT_DIR = ROOT / "processed_data"

TEXT_LINES_CSV = OUT_DIR / "2026_bear_cougar_furbearer_guidebook_text_lines.csv"
NUMBER_TOKENS_CSV = OUT_DIR / "2026_bear_cougar_furbearer_guidebook_number_tokens.csv"
EXPECTED_TEXT_CHECKS_CSV = OUT_DIR / "2026_bear_cougar_furbearer_guidebook_expected_text_checks.csv"
BEAR_HUNT_TABLES_CSV = OUT_DIR / "2026_bear_cougar_furbearer_guidebook_bear_hunt_tables.csv"
SUMMARY = REPORT_DIR / "2026_bear_cougar_furbearer_guidebook_audit.json"
REPORT_MD = REPORT_DIR / "2026_bear_cougar_furbearer_guidebook_audit.md"

SOURCE_PATH = "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Bear Cougar Furbearer Guidebook.pdf"
EXPECTED_SHA256 = "57a7a7c4b40196faf34251b260d30946aaaf23cbe0755e916508fc7d70b5b5f6"
EXPECTED_SIZE_BYTES = 3_243_631
EXPECTED_PDF_PAGES = 88

BR_CODE_RE = re.compile(r"\bBR\d{4}\b")
DATE_TOKEN_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+"
    r"\d{1,2}(?:\s*[-–]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+)?\d{1,2})?"
    r"(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
CODE_CITATION_RE = re.compile(r"\b(?:R657-\d+(?:-\d+)?|23A-\d+-\d+|76-\d+-\d+|53-5a-\d+|R651-\d+-\d+)\b")
NUMBER_TOKEN_RE = re.compile(r"\$?\b\d+(?:,\d{3})*(?:\.\d+)?%?\b|\b\d{1,2}:\d{2}\b|\bBR\d{4}\b")


@dataclass(frozen=True)
class ExpectedTextCheck:
    check_id: str
    printed_page: str
    match_type: str
    expected_text: str
    source_note: str


EXPECTED_TEXT_CHECKS = [
    ExpectedTextCheck("cover_title", "1", "contains", "BEAR, COUGAR FURBEARER and GUIDEBOOK 2026 BLACK BEAR", "cover text"),
    ExpectedTextCheck("contents_key_dates", "3", "contains", "10 Key dates", "contents"),
    ExpectedTextCheck("contents_hunt_tables", "3", "contains", "73 Hunt tables", "contents"),
    ExpectedTextCheck("contents_management_units", "3", "contains", "81 Management units", "contents"),
    ExpectedTextCheck("contents_furbearer_dates", "3", "contains", "83 Furbearer season dates", "contents"),
    ExpectedTextCheck("combined_guidebook", "4", "contains", "Combined black bear, cougar and furbearer guidebook", "what's new"),
    ExpectedTextCheck("digital_only", "4", "contains", "Digital-only guidebook", "what's new"),
    ExpectedTextCheck("new_draw_platform", "4", "contains", "Apply for bear hunts using the NEW online draw platform", "what's new"),
    ExpectedTextCheck("dolores_new_unit", "4", "contains", "New bear unit", "what's new"),
    ExpectedTextCheck("nonresident_fee_increase", "5", "contains", "Nonresident fee increase", "what's new"),
    ExpectedTextCheck("wma_license_requirement", "5", "contains", "WMA license requirement", "what's new"),
    ExpectedTextCheck("cougar_year_round_reminder", "5", "contains", "A person may pursue or hunt cougars year-round", "important reminders"),
    ExpectedTextCheck("bear_orientation_course", "6", "contains", "Bear orientation course", "important reminders"),
    ExpectedTextCheck("bear_bait_season", "6", "contains", "May 25-June 28, 2026", "important reminders"),
    ExpectedTextCheck("trap_registration_numbers", "7", "contains", "Trap registration numbers", "important reminders"),
    ExpectedTextCheck("application_start", "10", "contains", "Start applying online Feb. 10, 2026 8:00 a.m. MST", "key dates"),
    ExpectedTextCheck("application_deadline", "10", "contains", "Application deadline Feb. 24, 2026 11:00 p.m. MST", "key dates"),
    ExpectedTextCheck("drawing_results", "10", "contains", "Drawing results available March 5, 2026", "key dates"),
    ExpectedTextCheck("remaining_permits_sale", "10", "contains", "Remaining permits go on sale, if available March 10, 2026 8:00 a.m. MDT", "key dates"),
    ExpectedTextCheck("restricted_units", "10", "contains", "Book Cliffs La Sal San Juan", "restricted pursuit units"),
    ExpectedTextCheck("marten_2026_tags", "11", "contains", "Sept. 14, 2026-March 5, 2027", "permit dates"),
    ExpectedTextCheck("bobcat_2026_permits", "11", "contains", "Oct. 1-31, 2026", "permit dates"),
    ExpectedTextCheck("bear_pursuit_fee", "12", "contains", "Bear pursuit permit $45 $342", "fees"),
    ExpectedTextCheck("bear_harvest_objective_fee", "12", "contains", "Bear harvest-objective permit $93 $600", "fees"),
    ExpectedTextCheck("bear_multiseason_fee", "12", "contains", "Bear multiseason limited-entry permit* $183* $889*", "fees"),
    ExpectedTextCheck("bear_application_fee", "12", "contains", "Bear application fee* $10 $21", "fees"),
    ExpectedTextCheck("bobcat_fee", "12", "contains", "Bobcat permit $17 each", "fees"),
    ExpectedTextCheck("bear_minimum_age", "14", "contains", "at least 12 years old by Dec. 31, 2026", "age requirements"),
    ExpectedTextCheck("trial_program", "17", "contains", "Utah's Trial Hunting Program", "basic requirements"),
    ExpectedTextCheck("furbearer_license_requirement", "17", "contains", "Furbearer license requirement", "basic requirements"),
    ExpectedTextCheck("one_bear_permit", "20", "contains", "You may not apply for or obtain more than one permit to harvest a black bear in 2026", "permit rules"),
    ExpectedTextCheck("bonus_points", "22", "contains", "Why bonus points matter", "bonus points"),
    ExpectedTextCheck("waiting_period", "24", "contains", "there is a two-year wait-ing period", "waiting period"),
    ExpectedTextCheck("utahdraws_phone", "25", "contains", "utahdraws.com, or by calling the new hunt-drawing helpline at 855-883-7297", "application instructions"),
    ExpectedTextCheck("cougar_no_extra_permit", "31", "contains", "A separate permit is not required to hunt cougars in Utah", "cougar section"),
    ExpectedTextCheck("bobcat_six_permits", "33", "contains", "no more than six bobcat permits each season", "furbearer permits"),
    ExpectedTextCheck("firearm_centerfire", "38", "contains", "Your rifle must fire centerfire cartridges and expanding bullets", "field regulations"),
    ExpectedTextCheck("no_drones", "43", "contains", "No drones allowed", "prohibited methods"),
    ExpectedTextCheck("bear_hunting_hours", "48", "contains", "30 minutes before official sunrise until 30 minutes after official sunset", "bear rules"),
    ExpectedTextCheck("bait_chocolate", "54", "contains", "The use of chocolate or cocoa powder products as bait is prohibited", "bait rules"),
    ExpectedTextCheck("bear_48_hour_report", "55", "contains", "If you harvest a bear, you must contact the DWR within 48 hours", "harvest reporting"),
    ExpectedTextCheck("cougar_48_hour_report", "58", "contains", "If you harvest a cougar, you must contact the DWR within 48 hours", "cougar reporting"),
    ExpectedTextCheck("trap_check_period", "63", "contains", "at least once every 48 hours", "trap checks"),
    ExpectedTextCheck("beaver_closure_johnson", "65", "contains", "Johnson on this road to USFS Rd 072; north Creek and Wildcat Creek", "closures"),
    ExpectedTextCheck("predator_control", "72", "contains", "Utah Predator Control Program", "predator control"),
    ExpectedTextCheck("spring_br7021", "73", "contains", "Dolores Triangle (new) BR7021 2 0 March 28-May 25", "bear hunt table"),
    ExpectedTextCheck("summer_br7126", "74", "contains", "Dolores Triangle (new) BR7126 6 0 May 25-June 28", "bear hunt table"),
    ExpectedTextCheck("fall_br7238", "75", "contains", "Dolores Triangle (new) BR7238 2 0", "bear hunt table"),
    ExpectedTextCheck("spot_stalk_br7225", "77", "contains", "Book Cliffs, Little Creek Roadless BR7225 5 0 Sept. 1-Nov. 8", "bear hunt table"),
    ExpectedTextCheck("restricted_br1015", "78", "contains", "Book Cliffs BR1015 See below 2 March 28-May 25", "restricted pursuit table"),
    ExpectedTextCheck("harvest_objective_beaver", "79", "contains", "Beaver 5 Sept. 1-Oct. 25 No bait/no dogs", "harvest objective table"),
    ExpectedTextCheck("cougar_management_22b", "81", "contains", "Beaver, East 22B", "cougar management units"),
    ExpectedTextCheck("furbearer_bobcat_dates", "83", "contains", "Bobcat Nov. 15, 2025-March 1, 2026 Nov. 18, 2026-March 1, 2027", "furbearer dates"),
    ExpectedTextCheck("definition_bear", "84", "contains", "Bear means Ursus americanus", "definitions"),
    ExpectedTextCheck("definition_resident", "87", "contains", "Resident means a person who has a domicile", "definitions"),
]


def normalized(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2022", " ")
    text = text.replace("\u2019", "'").replace("\u00a0", " ")
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


def read_code_set(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row.get("hunt_code", "") for row in csv.DictReader(handle) if row.get("hunt_code", "").startswith("BR")}


def extract_lines() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for pdf_page, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for line_number, line in enumerate(text.splitlines(), start=1):
                clean_line = normalized(line)
                if not clean_line:
                    continue
                rows.append(
                    {
                        "source_file": SOURCE_PATH,
                        "source_sha256": EXPECTED_SHA256,
                        "pdf_page": str(pdf_page),
                        "printed_page": str(pdf_page),
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
    rows: list[dict[str, str]] = []
    norm_text = normalized(all_text)
    for check in EXPECTED_TEXT_CHECKS:
        expected = normalized(check.expected_text)
        found = expected not in norm_text if check.match_type == "absent" else expected in norm_text
        rows.append(
            {
                "check_id": check.check_id,
                "printed_page": check.printed_page,
                "match_type": check.match_type,
                "expected_text": expected,
                "source_note": check.source_note,
                "status": "PASS" if found else "FAIL",
            }
        )
    return rows


def build_bear_hunt_rows(text_lines: list[dict[str, str]]) -> list[dict[str, str]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        database_rows = {row["hunt_code"]: row for row in csv.DictReader(handle)}
    predictive_codes = read_code_set(PREDICTIVE)
    rows: list[dict[str, str]] = []
    for line in text_lines:
        for code in BR_CODE_RE.findall(line["text"]):
            database_row = database_rows.get(code, {})
            rows.append(
                {
                    "source_file": SOURCE_PATH,
                    "source_sha256": EXPECTED_SHA256,
                    "pdf_page": line["pdf_page"],
                    "printed_page": line["printed_page"],
                    "line_number": line["line_number"],
                    "hunt_code": code,
                    "guidebook_line_text": line["text"],
                    "database_present": str(bool(database_row)).lower(),
                    "predictive_present": str(code in predictive_codes).lower(),
                    "database_hunt_name": database_row.get("hunt_name", ""),
                    "database_species": database_row.get("species", ""),
                    "database_sex_type": database_row.get("sex_type", ""),
                    "database_hunt_type": database_row.get("hunt_type", ""),
                    "database_weapon": database_row.get("weapon", ""),
                    "permits_2026_res": database_row.get("permits_2026_res", ""),
                    "permits_2026_nr": database_row.get("permits_2026_nr", ""),
                    "permits_2026_total": database_row.get("permits_2026_total", ""),
                    "season": database_row.get("season", ""),
                }
            )
    return rows


def main() -> int:
    actual_sha = sha256(SOURCE_PDF)
    text_lines = extract_lines()
    all_text = "\n".join(row["text"] for row in text_lines)
    number_tokens = build_number_tokens(text_lines)
    expected_checks = build_expected_checks(all_text)
    bear_hunt_rows = build_bear_hunt_rows(text_lines)
    guidebook_br_codes = sorted({row["hunt_code"] for row in bear_hunt_rows})
    database_codes = read_code_set(DATABASE)
    predictive_codes = read_code_set(PREDICTIVE)

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
        BEAR_HUNT_TABLES_CSV,
        [
            "source_file",
            "source_sha256",
            "pdf_page",
            "printed_page",
            "line_number",
            "hunt_code",
            "guidebook_line_text",
            "database_present",
            "predictive_present",
            "database_hunt_name",
            "database_species",
            "database_sex_type",
            "database_hunt_type",
            "database_weapon",
            "permits_2026_res",
            "permits_2026_nr",
            "permits_2026_total",
            "season",
        ],
        bear_hunt_rows,
    )

    anchor_failures = [row for row in expected_checks if row["status"] != "PASS"]
    missing_database = sorted(set(guidebook_br_codes) - database_codes)
    missing_predictive = sorted(set(guidebook_br_codes) - predictive_codes)
    token_counts = Counter(row["token_type"] for row in number_tokens)
    blockers = []
    if actual_sha != EXPECTED_SHA256:
        blockers.append("source_sha256_mismatch")
    if SOURCE_PDF.stat().st_size != EXPECTED_SIZE_BYTES:
        blockers.append("source_size_mismatch")
    if missing_database:
        blockers.append("bear_hunt_codes_missing_database")
    if missing_predictive:
        blockers.append("bear_hunt_codes_missing_predictive")
    if anchor_failures:
        blockers.append("expected_text_anchor_failures")

    summary = {
        "classification": "REGULATION_AND_GUIDEBOOK_TRUTH_SOURCE_AUDIT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_pdf": SOURCE_PATH,
        "source_sha256": actual_sha,
        "expected_sha256": EXPECTED_SHA256,
        "source_size_bytes": SOURCE_PDF.stat().st_size,
        "expected_size_bytes": EXPECTED_SIZE_BYTES,
        "pdf_pages": EXPECTED_PDF_PAGES,
        "text_lines": len(text_lines),
        "number_tokens": len(number_tokens),
        "token_type_counts": dict(sorted(token_counts.items())),
        "expected_text_checks": len(expected_checks),
        "expected_text_anchor_failures": len(anchor_failures),
        "bear_guidebook_hunt_code_count": len(guidebook_br_codes),
        "bear_guidebook_hunt_codes": guidebook_br_codes,
        "bear_codes_missing_database": missing_database,
        "bear_codes_missing_predictive": missing_predictive,
        "blockers": len(blockers),
        "blocker_reasons": blockers,
        "guardrail": "Guidebook text, numbers, hunt codes, seasons, fees, and rules are truth-source references; this audit does not model draw odds.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# 2026 Bear/Cougar/Furbearer Guidebook Audit",
                "",
                f"- Source PDF: `{SOURCE_PATH}`",
                f"- Source SHA-256: `{actual_sha}`",
                f"- PDF pages: `{EXPECTED_PDF_PAGES}`",
                f"- Extracted text lines: `{len(text_lines)}`",
                f"- Extracted number/date/code tokens: `{len(number_tokens)}`",
                f"- Expected pasted-data anchor checks: `{len(expected_checks)}`",
                f"- Anchor failures: `{len(anchor_failures)}`",
                f"- Bear guidebook hunt codes: `{len(guidebook_br_codes)}`",
                f"- Bear codes missing DATABASE: `{len(missing_database)}`",
                f"- Bear codes missing predictive v2: `{len(missing_predictive)}`",
                f"- Blockers: `{len(blockers)}`",
                "",
                "This is a truth-source guidebook audit only; it does not invent draw odds or change prediction math.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
