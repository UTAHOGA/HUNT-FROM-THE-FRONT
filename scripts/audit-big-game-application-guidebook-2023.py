from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2023/pdf/regulation/2023_biggameapp.pdf"
RAW_INVENTORY = ROOT / "data_model/quality/raw_pdf_inventory.csv"
RAW_AUDIT = ROOT / "data_model/quality/raw_pdf_inventory_audit.csv"
OUT_DIR = ROOT / "data_truth/regulations_truth/normalized"
REPORT_DIR = ROOT / "processed_data"

SUMMARY = REPORT_DIR / "2023_big_game_application_guidebook_source_audit.json"
REPORT_MD = REPORT_DIR / "2023_big_game_application_guidebook_source_audit.md"
TEXT_LINES_CSV = OUT_DIR / "2023_big_game_application_guidebook_text_lines.csv"
NUMBER_TOKENS_CSV = OUT_DIR / "2023_big_game_application_guidebook_number_tokens.csv"
EXPECTED_TEXT_CHECKS_CSV = OUT_DIR / "2023_big_game_application_guidebook_expected_text_checks.csv"
HUNT_TABLES_CSV = OUT_DIR / "2023_big_game_application_guidebook_hunt_tables.csv"

SOURCE_PATH = "pipeline/RAW/hunt_unit_database/2023/pdf/regulation/2023_biggameapp.pdf"
EXPECTED_SHA256 = "7357df71939b084d5e6807a1bc01670bb6f1c04369e550946b1363c57ed2082b"
EXPECTED_SIZE_BYTES = 2_880_571
EXPECTED_TITLE = "2023 Utah Big Game Application Guidebook"
EXPECTED_SOURCE_YEAR = "2023"

CODE_RE = re.compile(r"\b([A-Z]{2}\d{4})\b")
DATE_TOKEN_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+"
    r"\d{1,2}(?:\s*[-]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+)?\d{1,2})?"
    r"(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
CODE_CITATION_RE = re.compile(r"\b(?:R657-\d+(?:-\d+)?(?:\(\d+\))?|(?:\d{2,3}-){2}\d{1,4})\b")
NUMBER_TOKEN_RE = re.compile(r"\$?\b\d+(?:,\d{3})*(?:\.\d+)?%?\b|\b\d{1,2}:\d{2}\b|\b[A-Z]{1,3}\d{4}\b")

SPECIES_BY_PREFIX = {
    "DB": "Deer",
    "EB": "Elk",
    "PB": "Pronghorn",
    "MB": "Moose",
    "BI": "Bison",
    "DS": "Desert Bighorn Sheep",
    "RS": "Rocky Mountain Bighorn Sheep",
    "GO": "Mountain Goat",
}


@dataclass(frozen=True)
class ExpectedTextCheck:
    check_id: str
    guidebook_page: str
    match_type: str
    expected_text: str
    source_note: str


EXPECTED_TEXT_CHECKS = [
    ExpectedTextCheck("revision_label", "", "contains", "REVISED MAY 2023", "user pasted cover/revision label"),
    ExpectedTextCheck("contents_keep_license", "2", "contains", "4 Keep your license on your", "user pasted contents"),
    ExpectedTextCheck("contents_hunt_tables", "2", "contains", "42 Hunt tables", "user pasted contents"),
    ExpectedTextCheck("contents_definitions", "2", "contains", "78 Definitions", "user pasted contents"),
    ExpectedTextCheck("utip_phone", "2", "contains", "Phone: 1-800-662-3337", "user pasted contact block"),
    ExpectedTextCheck("title_2023_application_guidebook", "3", "contains", "This guidebook-along with the 2023", "user pasted laws block"),
    ExpectedTextCheck("apply_window", "3", "contains", "2023 big game hunts from March 23 to April", "user pasted what's-new block"),
    ExpectedTextCheck("drawing_results_date", "3", "contains", "will be available on May 31, 2023", "user pasted what's-new block"),
    ExpectedTextCheck("elk_split", "3", "contains", "elk any legal weapon any bull hunt is", "user pasted elk split block"),
    ExpectedTextCheck("antlerless_application_period", "4", "contains", "period runs from June 7-22, 2023", "user pasted antlerless block"),
    ExpectedTextCheck("late_archery_elk", "4", "contains", "Dec. 2-17, 2023", "user pasted late-season elk block"),
    ExpectedTextCheck("antlerless_hunting", "5", "contains", "Antlerless big game", "user pasted antlerless box"),
    ExpectedTextCheck("disabled_veterans", "6", "contains", "Discounted licenses", "user pasted disabled veterans block"),
    ExpectedTextCheck("general_archery_deer", "7", "contains", "General archery deer Aug. 19-Sept. 15", "user pasted season dates"),
    ExpectedTextCheck("general_muzzleloader_elk", "7", "contains", "General muzzleloader", "user pasted season dates"),
    ExpectedTextCheck("extended_archery", "8", "contains", "Extended archery", "user pasted extended archery block"),
    ExpectedTextCheck("sportsman_permits_2024", "9", "contains", "2024 sportsman", "user pasted sportsman block"),
    ExpectedTextCheck("sales_dates", "10", "contains", "General-season any bull elk", "user pasted sales dates"),
    ExpectedTextCheck("trail_camera_regulations", "11", "contains", "CHANGES TO TRAIL CAMERA", "user pasted trail camera block"),
    ExpectedTextCheck("cwmu_season_dates", "12", "contains", "CWMU season dates", "user pasted CWMU dates"),
    ExpectedTextCheck("shed_antlers", "13", "contains", "Gathering shed", "user pasted shed antlers block"),
    ExpectedTextCheck("permit_numbers", "13", "contains", "15,000 general-season permits", "user pasted permit numbers"),
    ExpectedTextCheck("resident_license_fees", "14", "contains", "Resident license fees", "user pasted fees"),
    ExpectedTextCheck("permit_fees", "15", "contains", "Deer permit fees", "user pasted fees"),
    ExpectedTextCheck("basic_requirements", "16", "contains", "BASIC REQUIREMENTS", "user pasted requirements"),
    ExpectedTextCheck("carry_permit", "17", "contains", "Carry your permit", "user pasted carry permit"),
    ExpectedTextCheck("prepare_to_apply", "18", "contains", "PREPARE TO APPLY", "user pasted prepare block"),
    ExpectedTextCheck("drawing_order", "19", "contains", "Understand the drawing", "user pasted drawing order"),
    ExpectedTextCheck("bonus_points", "20", "contains", "Why bonus points", "user pasted bonus points"),
    ExpectedTextCheck("preference_points", "21", "contains", "Why preference", "user pasted preference points"),
    ExpectedTextCheck("waiting_periods", "22", "contains", "Waiting periods", "user pasted waiting periods"),
    ExpectedTextCheck("three_elk_permits", "23", "contains", "Obtain up to three elk", "user pasted elk permits"),
    ExpectedTextCheck("mandatory_reporting", "24", "contains", "Mandatory reporting", "user pasted reporting"),
    ExpectedTextCheck("early_deer_hunts", "25", "contains", "Early general-season buck", "user pasted early deer"),
    ExpectedTextCheck("hams_deer", "26", "contains", "Handgun-archery", "user pasted HAMS block"),
    ExpectedTextCheck("apply_for_permits", "28", "contains", "APPLY FOR BIG GAME PERMITS", "user pasted apply block"),
    ExpectedTextCheck("after_you_apply", "30", "contains", "AFTER YOU APPLY", "user pasted after apply"),
    ExpectedTextCheck("lifetime_license", "32", "contains", "Lifetime license", "user pasted lifetime license"),
    ExpectedTextCheck("dedicated_hunter", "33", "contains", "DEDICATED HUNTER PROGRAM", "user pasted DH block"),
    ExpectedTextCheck("youth_deer_seasons", "34", "contains", "YOUTH DEER", "user pasted youth table"),
    ExpectedTextCheck("youth_elk_seasons", "35", "contains", "YOUTH ELK SEASONS", "user pasted youth table"),
    ExpectedTextCheck("general_deer_table", "42", "contains", "Beaver DB1500 Aug. 19-Sept. 15", "user pasted deer table"),
    ExpectedTextCheck("limited_deer_table", "48", "contains", "Henry Mtns DB1000", "user pasted premium deer table"),
    ExpectedTextCheck("management_buck", "49", "contains", "Paunsaugunt (archery) DB1073", "user pasted management table"),
    ExpectedTextCheck("hams_hunt_codes", "52", "contains", "Book Cliffs, Floy Canyon DB1090", "user pasted HAMS table"),
    ExpectedTextCheck("draw_only_youth_elk_code", "53", "contains", "Draw-only youth any bull", "user pasted elk table"),
    ExpectedTextCheck("late_archery_elk_table", "54", "contains", "Beaver, East EB3158 Dec. 2-Dec. 17", "user pasted elk table"),
    ExpectedTextCheck("midseason_elk", "56", "contains", "Beaver, East (new) EB3159 Oct. 7-Oct. 19", "user pasted elk table"),
    ExpectedTextCheck("multi_season_elk", "59", "contains", "Beaver, East EB3102 Limited Entry Seasons", "user pasted elk table"),
    ExpectedTextCheck("hams_elk", "60", "contains", "Cache, North EB3139 Nov. 11-Nov. 30", "user pasted HAMS elk"),
    ExpectedTextCheck("pronghorn_archery", "60", "contains", "Beaver PB5000 Aug. 19-Sept. 15", "user pasted pronghorn table"),
    ExpectedTextCheck("pronghorn_rifle", "62", "contains", "Beaver PB5025 Sept. 16-Sept. 24", "user pasted pronghorn table"),
    ExpectedTextCheck("moose_table", "63", "contains", "Cache MB6000 Sept. 16-Oct. 19", "user pasted moose table"),
    ExpectedTextCheck("bison_table", "64", "contains", "Antelope Island BI6500 Dec. 4-Dec. 6", "user pasted bison table"),
    ExpectedTextCheck("desert_bighorn", "65", "contains", "Henry Mtns DS6600 Sept. 16-Nov. 10", "user pasted bighorn table"),
    ExpectedTextCheck("rocky_bighorn", "66", "contains", "Book Cliffs, South RS6701 Nov. 1-Nov. 30", "user pasted bighorn table"),
    ExpectedTextCheck("mountain_goat", "67", "contains", "Beaver GO6800 Sept. 9-Oct. 1", "user pasted goat table"),
    ExpectedTextCheck("cwmu_premium", "68", "contains", "Alton DB1200 Kane 3", "user pasted CWMU table"),
    ExpectedTextCheck("cwmu_buck_deer", "69", "contains", "Antelope Creek DB1202 Duchesne 1", "user pasted CWMU table"),
    ExpectedTextCheck("cwmu_bull_elk", "73", "contains", "Alton EB3500 Kane 2", "user pasted CWMU elk"),
    ExpectedTextCheck("cwmu_pronghorn", "76", "contains", "Allen Ranch PB5325 Utah 2", "user pasted CWMU pronghorn"),
    ExpectedTextCheck("cwmu_moose", "77", "contains", "Causey Spring MB6202 Weber 1", "user pasted CWMU moose"),
    ExpectedTextCheck("definitions", "78", "contains", "DEFINITIONS", "user pasted definitions"),
    ExpectedTextCheck("hams_definition", "78", "contains", "Handgun-archery-muzzleloader", "user pasted definitions"),
    ExpectedTextCheck("resident_definition", "79", "contains", "Resident means a person who has a", "user pasted definitions"),
    ExpectedTextCheck("trail_camera_definition", "80", "contains", "Trail camera means a device", "user pasted definitions"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize_text(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "",
        "\u2021": "",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def compact_for_match(text: str) -> str:
    return normalize_text(text).casefold()


def extract_pdf_lines(path: Path) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for pdf_page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            raw_lines = text.splitlines()
            printed_page = ""
            for candidate in raw_lines[:5]:
                cleaned = normalize_text(candidate)
                if cleaned.isdigit():
                    printed_page = cleaned
                    break
            if not printed_page and pdf_page_number > 1:
                printed_page = str(pdf_page_number)
            text_line_number = 0
            for raw_line in raw_lines:
                line_text = normalize_text(raw_line)
                if not line_text:
                    continue
                text_line_number += 1
                rows.append(
                    {
                        "source_file": SOURCE_PATH,
                        "pdf_page_number": str(pdf_page_number),
                        "printed_page": printed_page,
                        "line_number_on_pdf_page": str(text_line_number),
                        "line_text": line_text,
                    }
                )
    return rows, page_count


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_number_tokens(line_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    token_rows: list[dict[str, str]] = []
    for row in line_rows:
        line_text = row["line_text"]
        seen: set[tuple[str, str]] = set()
        for token_type, pattern in (
            ("date", DATE_TOKEN_RE),
            ("code_citation", CODE_CITATION_RE),
            ("number_or_money", NUMBER_TOKEN_RE),
        ):
            for match in pattern.finditer(line_text):
                token = normalize_text(match.group(0))
                key = (token_type, token)
                if key in seen:
                    continue
                seen.add(key)
                token_rows.append(
                    {
                        "source_file": SOURCE_PATH,
                        "pdf_page_number": row["pdf_page_number"],
                        "printed_page": row["printed_page"],
                        "line_number_on_pdf_page": row["line_number_on_pdf_page"],
                        "token_type": token_type,
                        "token": token,
                        "line_text": line_text,
                    }
                )
    return token_rows


def section_for_page(page: int) -> str:
    if 42 <= page <= 52:
        return "BUCK_DEER_HUNT_TABLES"
    if 53 <= page <= 60:
        return "BULL_ELK_HUNT_TABLES"
    if 60 <= page <= 63:
        return "BUCK_PRONGHORN_HUNT_TABLES"
    if page == 63:
        return "BULL_MOOSE_HUNT_TABLES"
    if page == 64:
        return "BISON_HUNT_TABLES"
    if 65 <= page <= 66:
        return "BIGHORN_SHEEP_HUNT_TABLES"
    if page == 67:
        return "MOUNTAIN_GOAT_HUNT_TABLES"
    if 68 <= page <= 77:
        return "CWMU_HUNT_TABLES"
    return "GUIDEBOOK_REFERENCE"


def parse_hunt_code_line(row: dict[str, str]) -> list[dict[str, str]]:
    line = row["line_text"]
    guidebook_page = int(row["printed_page"] or row["pdf_page_number"])
    parsed_rows: list[dict[str, str]] = []
    for match in CODE_RE.finditer(line):
        code = match.group(1)
        if guidebook_page < 42 or guidebook_page > 77:
            continue
        before = normalize_text(line[: match.start()])
        after = normalize_text(line[match.end() :])
        if before.startswith("* Nonresidents") or before.startswith("† Nonresidents"):
            continue

        county_text = ""
        public_permits = ""
        season_text = after
        if section_for_page(guidebook_page) == "CWMU_HUNT_TABLES":
            county_match = re.match(r"(?P<county>.+?)\s+(?P<permits>\d+)$", after)
            if county_match:
                county_text = normalize_text(county_match.group("county"))
                public_permits = county_match.group("permits")
                season_text = ""

        parsed_rows.append(
            {
                "source_file": SOURCE_PATH,
                "hunt_code": code,
                "guidebook_page": str(guidebook_page),
                "guidebook_section": section_for_page(guidebook_page),
                "species_inferred": SPECIES_BY_PREFIX.get(code[:2], ""),
                "guidebook_hunt_name": before,
                "guidebook_season_text": season_text,
                "guidebook_county_text": county_text,
                "guidebook_public_permits": public_permits,
                "raw_line": line,
            }
        )
    return parsed_rows


def extract_hunt_table_rows(line_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in line_rows:
        rows.extend(parse_hunt_code_line(row))

    best_by_code: dict[str, dict[str, str]] = {}
    for row in rows:
        current = best_by_code.get(row["hunt_code"])
        if current is None:
            best_by_code[row["hunt_code"]] = row
            continue
        current_score = (current["guidebook_hunt_name"] == "", int(current["guidebook_page"]))
        row_score = (row["guidebook_hunt_name"] == "", int(row["guidebook_page"]))
        if row_score < current_score:
            best_by_code[row["hunt_code"]] = row
    return sorted(best_by_code.values(), key=lambda row: (row["hunt_code"], int(row["guidebook_page"])))


def find_expected_match(line_rows: list[dict[str, str]], check: ExpectedTextCheck) -> tuple[str, dict[str, str] | None]:
    scoped_rows = [row for row in line_rows if not check.guidebook_page or row["printed_page"] == check.guidebook_page]
    haystack = compact_for_match(" ".join(row["line_text"] for row in scoped_rows))
    needle = compact_for_match(check.expected_text)

    if check.match_type == "absent":
        return ("PASS" if needle not in haystack else "FAIL", None)
    if needle not in haystack:
        return "FAIL", None

    words = [word for word in needle.split() if len(word) >= 4]
    snippets = [" ".join(words[:5]), " ".join(words[:4]), " ".join(words[:3]), words[0] if words else needle]
    for row in scoped_rows:
        line_compact = compact_for_match(row["line_text"])
        if any(snippet and snippet in line_compact for snippet in snippets):
            return "PASS", row
    return "PASS", scoped_rows[0] if scoped_rows else None


def run_expected_text_checks(line_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for check in EXPECTED_TEXT_CHECKS:
        status, matched = find_expected_match(line_rows, check)
        rows.append(
            {
                "source_file": SOURCE_PATH,
                "check_id": check.check_id,
                "guidebook_page": check.guidebook_page,
                "match_type": check.match_type,
                "expected_text": check.expected_text,
                "status": status,
                "matched_pdf_page_number": matched["pdf_page_number"] if matched else "",
                "matched_printed_page": matched["printed_page"] if matched else "",
                "matched_line_number_on_pdf_page": matched["line_number_on_pdf_page"] if matched else "",
                "matched_line_text": matched["line_text"] if matched else "",
                "source_note": check.source_note,
            }
        )
    return rows


def build_summary(
    line_rows: list[dict[str, str]],
    pdf_page_count: int,
    token_rows: list[dict[str, str]],
    expected_check_rows: list[dict[str, str]],
    hunt_table_rows: list[dict[str, str]],
) -> dict[str, object]:
    source_exists = SOURCE_PDF.exists()
    source_hash = sha256(SOURCE_PDF) if source_exists else ""
    source_size = SOURCE_PDF.stat().st_size if source_exists else 0
    first_pages_text = " ".join(row["line_text"] for row in line_rows if int(row["pdf_page_number"]) <= 4)
    compact_text = compact_for_match(first_pages_text)

    raw_inventory_rows = [row for row in read_csv_rows(RAW_INVENTORY) if row.get("path") == SOURCE_PATH]
    raw_audit_rows = [row for row in read_csv_rows(RAW_AUDIT) if row.get("path") == SOURCE_PATH]
    token_counts = Counter(row["token_type"] for row in token_rows)
    hunt_code_prefix_counts = Counter(row["hunt_code"][:2] for row in hunt_table_rows)
    expected_failures = [row for row in expected_check_rows if row["status"] != "PASS"]

    checks = {
        "source_pdf_exists": source_exists,
        "source_path_is_2023_folder": "/2023/" in SOURCE_PATH.replace("\\", "/"),
        "source_hash_matches_expected": source_hash == EXPECTED_SHA256,
        "source_size_matches_expected": source_size == EXPECTED_SIZE_BYTES,
        "text_mentions_2023_application_guidebook": (
            "utah big game application guidebook" in compact_text and "2023" in compact_text
        ),
        "text_mentions_revised_may_2023": "revised may 2023" in compact_for_match(" ".join(row["line_text"] for row in line_rows[:5])),
        "text_does_not_identify_as_draw_odds": "draw odds" not in compact_text,
        "not_promoted_by_quality_or_draw_audit": all(
            row.get("promotion_status") != "PROMOTE"
            and row.get("quality_engine_use") != "YES"
            and row.get("draw_engine_use") != "YES"
            for row in raw_audit_rows
        ),
    }
    status_counts = Counter("PASS" if passed else "REVIEW" for passed in checks.values())

    return {
        "source_file": SOURCE_PATH,
        "expected_title": EXPECTED_TITLE,
        "expected_source_year": EXPECTED_SOURCE_YEAR,
        "actual_sha256": source_hash,
        "expected_sha256": EXPECTED_SHA256,
        "actual_size_bytes": source_size,
        "expected_size_bytes": EXPECTED_SIZE_BYTES,
        "classification": "APPLICATION_GUIDEBOOK_REFERENCE_ONLY",
        "modeling_guardrail": "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT",
        "database_reconciliation_effect": "NO_DRAW_OR_PREDICTION_ROWS_PROMOTED",
        "source_inventory_rows_found": len(raw_inventory_rows),
        "source_audit_rows_found": len(raw_audit_rows),
        "pdf_page_count": pdf_page_count,
        "text_line_count": len(line_rows),
        "number_token_count": len(token_rows),
        "token_type_counts": dict(token_counts),
        "hunt_table_row_count": len(hunt_table_rows),
        "hunt_table_unique_code_count": len({row["hunt_code"] for row in hunt_table_rows}),
        "hunt_code_prefix_counts": dict(hunt_code_prefix_counts),
        "expected_text_check_count": len(expected_check_rows),
        "expected_text_check_failures": len(expected_failures),
        "text_lines_output": str(TEXT_LINES_CSV.relative_to(ROOT)).replace("\\", "/"),
        "number_tokens_output": str(NUMBER_TOKENS_CSV.relative_to(ROOT)).replace("\\", "/"),
        "expected_text_checks_output": str(EXPECTED_TEXT_CHECKS_CSV.relative_to(ROOT)).replace("\\", "/"),
        "hunt_tables_output": str(HUNT_TABLES_CSV.relative_to(ROOT)).replace("\\", "/"),
        "checks": checks,
        "status_counts": dict(status_counts),
        "audit_blocker_count": status_counts.get("REVIEW", 0) + len(expected_failures),
    }


def write_markdown(summary: dict[str, object]) -> None:
    lines = [
        "# 2023 Big Game Application Guidebook Source Audit",
        "",
        f"Source PDF: `{summary['source_file']}`",
        "",
        "This audit locks the file identity as the revised May 2023 Big Game Application Guidebook. Hunt codes are extracted as application-guidebook reference rows only; this does not promote draw odds, harvest features, quota math, or prediction rows.",
        "",
        "## Summary",
        "",
        f"- Expected title: `{summary['expected_title']}`",
        f"- Expected source year: `{summary['expected_source_year']}`",
        f"- SHA-256: `{summary['actual_sha256']}`",
        f"- PDF pages: `{summary['pdf_page_count']}`",
        f"- Extracted text lines: `{summary['text_line_count']}`",
        f"- Extracted number/date/citation tokens: `{summary['number_token_count']}`",
        f"- Hunt-table reference rows: `{summary['hunt_table_row_count']}`",
        f"- Unique hunt codes: `{summary['hunt_table_unique_code_count']}`",
        f"- Expected pasted-text checks: `{summary['expected_text_check_count']}`",
        f"- Expected pasted-text failures: `{summary['expected_text_check_failures']}`",
        f"- Database reconciliation effect: `{summary['database_reconciliation_effect']}`",
        f"- Audit blockers: `{summary['audit_blocker_count']}`",
        "",
        "## Outputs",
        "",
        f"- Text lines: `{summary['text_lines_output']}`",
        f"- Number/date/citation tokens: `{summary['number_tokens_output']}`",
        f"- Pasted-text checks: `{summary['expected_text_checks_output']}`",
        f"- Hunt-table references: `{summary['hunt_tables_output']}`",
        "",
        "## Checks",
        "",
        "| check | status |",
        "|---|---:|",
    ]
    for check, passed in summary["checks"].items():
        lines.append(f"| {check} | {'PASS' if passed else 'REVIEW'} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    line_rows, pdf_page_count = extract_pdf_lines(SOURCE_PDF) if SOURCE_PDF.exists() else ([], 0)
    write_csv(
        TEXT_LINES_CSV,
        line_rows,
        ["source_file", "pdf_page_number", "printed_page", "line_number_on_pdf_page", "line_text"],
    )

    token_rows = extract_number_tokens(line_rows)
    write_csv(
        NUMBER_TOKENS_CSV,
        token_rows,
        [
            "source_file",
            "pdf_page_number",
            "printed_page",
            "line_number_on_pdf_page",
            "token_type",
            "token",
            "line_text",
        ],
    )

    hunt_table_rows = extract_hunt_table_rows(line_rows)
    write_csv(
        HUNT_TABLES_CSV,
        hunt_table_rows,
        [
            "source_file",
            "hunt_code",
            "guidebook_page",
            "guidebook_section",
            "species_inferred",
            "guidebook_hunt_name",
            "guidebook_season_text",
            "guidebook_county_text",
            "guidebook_public_permits",
            "raw_line",
        ],
    )

    expected_check_rows = run_expected_text_checks(line_rows)
    write_csv(
        EXPECTED_TEXT_CHECKS_CSV,
        expected_check_rows,
        [
            "source_file",
            "check_id",
            "guidebook_page",
            "match_type",
            "expected_text",
            "status",
            "matched_pdf_page_number",
            "matched_printed_page",
            "matched_line_number_on_pdf_page",
            "matched_line_text",
            "source_note",
        ],
    )

    summary = build_summary(line_rows, pdf_page_count, token_rows, expected_check_rows, hunt_table_rows)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
