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
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2023/pdf/regulation/2023_field_regs.pdf"
RAW_INVENTORY = ROOT / "data_model/quality/raw_pdf_inventory.csv"
RAW_AUDIT = ROOT / "data_model/quality/raw_pdf_inventory_audit.csv"
OUT_DIR = ROOT / "data_truth/regulations_truth/normalized"
REPORT_DIR = ROOT / "processed_data"

SUMMARY = REPORT_DIR / "2023_big_game_field_regulations_source_audit.json"
REPORT_MD = REPORT_DIR / "2023_big_game_field_regulations_source_audit.md"
TEXT_LINES_CSV = OUT_DIR / "2023_big_game_field_regulations_text_lines.csv"
NUMBER_TOKENS_CSV = OUT_DIR / "2023_big_game_field_regulations_number_tokens.csv"
EXPECTED_TEXT_CHECKS_CSV = OUT_DIR / "2023_big_game_field_regulations_expected_text_checks.csv"

SOURCE_PATH = "pipeline/RAW/hunt_unit_database/2023/pdf/regulation/2023_field_regs.pdf"
EXPECTED_SHA256 = "c68a0ef12e09e810449e2a5f569bcf445709249c9354036bc1ef17086477284f"
EXPECTED_SIZE_BYTES = 5_784_679
EXPECTED_TITLE = "2023 Utah Big Game Field Regulations"
EXPECTED_SOURCE_YEAR = "2023"

DATE_TOKEN_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+"
    r"\d{1,2}(?:\s*[-]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+)?\d{1,2})?"
    r"(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
CODE_CITATION_RE = re.compile(r"\b(?:R657-\d+(?:-\d+)?(?:\(\d+\))?|(?:\d{2,3}-){2}\d{1,4})\b")
NUMBER_TOKEN_RE = re.compile(r"\$?\b\d+(?:,\d{3})*(?:\.\d+)?%?\b|\b\d{1,2}:\d{2}\b|\b[A-Z]{1,3}\d{4}\b")


@dataclass(frozen=True)
class ExpectedTextCheck:
    check_id: str
    guidebook_page: str
    match_type: str
    expected_text: str
    source_note: str


EXPECTED_TEXT_CHECKS = [
    ExpectedTextCheck("contents_season_dates", "2", "contains", "7 2023 season dates", "user pasted contents"),
    ExpectedTextCheck("contents_definitions", "2", "contains", "68 Definitions", "user pasted contents"),
    ExpectedTextCheck("utip_phone", "2", "contains", "Phone: 800-662-3337", "user pasted contact block"),
    ExpectedTextCheck("utip_text", "2", "contains", "Text: 847411", "user pasted contact block"),
    ExpectedTextCheck("title_2023_field_regs", "3", "contains", "This guidebook-along with the 2023", "user pasted know-the-laws block"),
    ExpectedTextCheck("trail_camera_2023_change", "3", "contains", "Changes to trail camera regulations", "user pasted what's-new block"),
    ExpectedTextCheck("night_vision_devices", "3", "contains", "Night-vision devices", "user pasted what's-new block"),
    ExpectedTextCheck("elk_any_legal_weapon_split", "3", "contains", "general-season elk any legal weapon any", "user pasted elk change"),
    ExpectedTextCheck("hamss_hunts", "4", "contains", "HAMSS hunts", "user pasted HAMSS block"),
    ExpectedTextCheck("new_antlerless_elk_rule", "4", "contains", "New antlerless elk permit rules", "user pasted antlerless rule"),
    ExpectedTextCheck("general_archery_deer_date", "7", "contains", "General archery deer Aug. 19-Sept. 15", "user pasted season dates"),
    ExpectedTextCheck("early_any_bull_elk_date", "7", "contains", "Early general any legal Oct. 7-13", "user pasted season dates"),
    ExpectedTextCheck("extended_archery_deer_dates", "7", "contains", "Extended archery deer Sept. 16-", "user pasted extended archery dates"),
    ExpectedTextCheck("sportsman_deer_elk_weapon_date", "8", "contains", "Deer and elk on any Sept. 1, 2023-", "user pasted sportsman dates"),
    ExpectedTextCheck("resident_hunting_license_fee", "8", "contains", "365-day hunting license", "user pasted license fees"),
    ExpectedTextCheck("general_deer_permit_fee", "9", "contains", "General deer $40 $398", "user pasted permit fees"),
    ExpectedTextCheck("disabled_veterans", "10", "contains", "Discounted licenses for", "user pasted disabled veterans block"),
    ExpectedTextCheck("basic_requirements_heading", "11", "contains", "BASIC REQUIREMENTS", "user pasted requirements block"),
    ExpectedTextCheck("trial_hunting_program", "11", "contains", "Utah's Trial Hunting Program", "user pasted trial hunting block"),
    ExpectedTextCheck("license_on_phone", "12", "contains", "Keep your license on", "user pasted mobile license block"),
    ExpectedTextCheck("sportsman_permit_window", "13", "contains", "run from Oct. 18 to Nov. 8, 2023", "user pasted sportsman permit block"),
    ExpectedTextCheck("antlerless_apply_june_7", "14", "contains", "Starting June 7, 2023", "user pasted antlerless application block"),
    ExpectedTextCheck("antlerless_results_july_7", "14", "contains", "July 7: Antlerless drawing results", "user pasted antlerless application block"),
    ExpectedTextCheck("permit_sales_july_11", "15", "contains", "July 11: General-season archery elk", "user pasted permit sales"),
    ExpectedTextCheck("three_elk_permits", "16", "contains", "A hunter can obtain up to three elk", "user pasted elk permit rules"),
    ExpectedTextCheck("definition_of_youth", "17", "contains", "Definition of youth", "user pasted youth definition"),
    ExpectedTextCheck("youth_elk_seasons", "18", "contains", "YOUTH ELK SEASONS", "user pasted youth tables"),
    ExpectedTextCheck("youth_deer_seasons", "18", "contains", "YOUTH DEER", "user pasted youth tables"),
    ExpectedTextCheck("young_hunter_opportunities", "19", "contains", "OPPORTUNITIES FOR YOUNG HUNTERS", "user pasted young hunters block"),
    ExpectedTextCheck("cwd_positive_counts", "20", "contains", "194 mule deer and", "user pasted CWD block"),
    ExpectedTextCheck("trail_camera_public_land_dates", "21", "contains", "All trail cameras are prohibited on", "user pasted trail camera rules"),
    ExpectedTextCheck("big_game_hunts_heading", "22", "contains", "BIG GAME HUNTS", "user pasted big game hunts block"),
    ExpectedTextCheck("mandatory_reporting_heading", "23", "contains", "Mandatory reporting", "user pasted reporting block"),
    ExpectedTextCheck("hamss_deer_units", "24", "contains", "Book Cliffs, Floy Canyon", "user pasted HAMSS deer block"),
    ExpectedTextCheck("straight_walled_rifle", "25", "contains", "Straight-walled rifle (new)", "user pasted HAMSS weapon block"),
    ExpectedTextCheck("cactus_buck", "26", "contains", "Obtaining and using a cactus buck", "user pasted cactus buck block"),
    ExpectedTextCheck("bull_elk_hunting", "27", "contains", "Bull elk hunting", "user pasted elk block"),
    ExpectedTextCheck("multi_season_spike_elk", "29", "contains", "Multi-season general spike", "user pasted spike elk block"),
    ExpectedTextCheck("collared_wildlife", "30", "contains", "Avoid harvesting", "user pasted collared wildlife block"),
    ExpectedTextCheck("buck_pronghorn", "32", "contains", "Buck pronghorn", "user pasted pronghorn block"),
    ExpectedTextCheck("bison_hunting", "33", "contains", "Bison hunting", "user pasted bison block"),
    ExpectedTextCheck("antlerless_reporting", "34", "contains", "Mandatory reporting", "user pasted antlerless reporting block"),
    ExpectedTextCheck("military_points", "35", "contains", "Points options for", "user pasted military block"),
    ExpectedTextCheck("mountain_goat", "36", "contains", "Mountain goat", "user pasted mountain goat block"),
    ExpectedTextCheck("antlerless_hunts_heading", "37", "contains", "ANTLERLESS HUNTS", "user pasted antlerless block"),
    ExpectedTextCheck("antlerless_elk_printed_dates_rule", "39", "contains", "Antlerless elk permits may be used only during", "user pasted antlerless elk block"),
    ExpectedTextCheck("permit_surrender", "41", "contains", "PERMIT SURRENDERS, REFUNDS AND EXCHANGES", "user pasted surrender block"),
    ExpectedTextCheck("cwmu_heading", "43", "contains", "COOPERATIVE WILDLIFE MANAGEMENT UNITS", "user pasted CWMU block"),
    ExpectedTextCheck("cwmu_archery_dates", "44", "contains", "Archery hunts for buck", "user pasted CWMU dates"),
    ExpectedTextCheck("field_regulations_heading", "45", "contains", "FIELD REGULATIONS", "user pasted field regs block"),
    ExpectedTextCheck("prohibited_weapons", "45", "contains", "Prohibited weapons", "user pasted weapon rules"),
    ExpectedTextCheck("muzzleloader_requirements", "47", "contains", "Muzzleloaders may be used during any", "user pasted muzzleloader rules"),
    ExpectedTextCheck("archery_equipment", "48", "contains", "Archery equipment", "user pasted archery rules"),
    ExpectedTextCheck("walk_in_access", "49", "contains", "Utah's Walk-in Access", "user pasted WIA block"),
    ExpectedTextCheck("national_parks_closed", "50", "contains", "All of Utah's national parks and monu-", "user pasted parks block"),
    ExpectedTextCheck("salt_lake_county", "51", "contains", "muzzleloader south of I-80 and east of", "user pasted Salt Lake County block"),
    ExpectedTextCheck("trespassing", "52", "contains", "Trespassing", "user pasted trespassing block"),
    ExpectedTextCheck("no_drones", "52", "contains", "No drones allowed", "user pasted no drones block"),
    ExpectedTextCheck("night_vision_rule", "53", "contains", "You may not use any type", "user pasted night vision block"),
    ExpectedTextCheck("trail_cameras", "54", "contains", "Trail cameras", "user pasted trail cameras block"),
    ExpectedTextCheck("tagging_requirements", "55", "contains", "Tagging requirements", "user pasted tagging block"),
    ExpectedTextCheck("transporting_big_game", "56", "contains", "Transporting big game", "user pasted transport block"),
    ExpectedTextCheck("waste_of_game", "57", "contains", "Waste of game", "user pasted waste block"),
    ExpectedTextCheck("shed_antlers", "58", "contains", "Possession of antlers", "user pasted antlers block"),
    ExpectedTextCheck("definitions_heading", "68", "contains", "DEFINITIONS", "user pasted definitions"),
    ExpectedTextCheck("definition_baited_area", "68", "contains", "Baited area means all land within a 50-yard", "user pasted definitions"),
    ExpectedTextCheck("definition_hamss", "69", "contains", "Handgun-archery-muzzleloader-", "user pasted definitions"),
    ExpectedTextCheck("definition_resident", "70", "contains", "Resident means a person who has a", "user pasted definitions"),
    ExpectedTextCheck("definition_youth", "71", "contains", "Youth means someone who is 17 years old or", "user pasted definitions"),
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
) -> dict[str, object]:
    source_exists = SOURCE_PDF.exists()
    source_hash = sha256(SOURCE_PDF) if source_exists else ""
    source_size = SOURCE_PDF.stat().st_size if source_exists else 0
    first_pages_text = " ".join(row["line_text"] for row in line_rows if int(row["pdf_page_number"]) <= 4)
    compact_text = compact_for_match(first_pages_text)

    raw_inventory_rows = [row for row in read_csv_rows(RAW_INVENTORY) if row.get("path") == SOURCE_PATH]
    raw_audit_rows = [row for row in read_csv_rows(RAW_AUDIT) if row.get("path") == SOURCE_PATH]
    token_counts = Counter(row["token_type"] for row in token_rows)
    expected_failures = [row for row in expected_check_rows if row["status"] != "PASS"]

    checks = {
        "source_pdf_exists": source_exists,
        "source_path_is_2023_folder": "/2023/" in SOURCE_PATH.replace("\\", "/"),
        "source_hash_matches_expected": source_hash == EXPECTED_SHA256,
        "source_size_matches_expected": source_size == EXPECTED_SIZE_BYTES,
        "text_mentions_2023_field_regulations": (
            "utah big game field regulations" in compact_text and "2023" in compact_text
        ),
        "text_does_not_identify_as_draw_odds": "draw odds" not in compact_text,
        "raw_inventory_classifies_as_regulation_if_present": all(
            row.get("source_class") in {"regulations", "regulation", ""} or row.get("report_type") in {"regulation", ""}
            for row in raw_inventory_rows
        ),
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
        "classification": "REGULATION_REFERENCE_ONLY",
        "modeling_guardrail": "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT",
        "database_reconciliation_effect": "NO_DRAW_OR_PREDICTION_ROWS_PROMOTED",
        "source_inventory_rows_found": len(raw_inventory_rows),
        "source_audit_rows_found": len(raw_audit_rows),
        "pdf_page_count": pdf_page_count,
        "text_line_count": len(line_rows),
        "number_token_count": len(token_rows),
        "token_type_counts": dict(token_counts),
        "expected_text_check_count": len(expected_check_rows),
        "expected_text_check_failures": len(expected_failures),
        "text_lines_output": str(TEXT_LINES_CSV.relative_to(ROOT)).replace("\\", "/"),
        "number_tokens_output": str(NUMBER_TOKENS_CSV.relative_to(ROOT)).replace("\\", "/"),
        "expected_text_checks_output": str(EXPECTED_TEXT_CHECKS_CSV.relative_to(ROOT)).replace("\\", "/"),
        "checks": checks,
        "status_counts": dict(status_counts),
        "audit_blocker_count": status_counts.get("REVIEW", 0) + len(expected_failures),
    }


def write_markdown(summary: dict[str, object]) -> None:
    lines = [
        "# 2023 Big Game Field Regulations Source Audit",
        "",
        f"Source PDF: `{summary['source_file']}`",
        "",
        "This audit locks the file identity as 2023 field regulations only. It does not promote the file into draw odds, harvest features, quota math, or prediction math.",
        "",
        "## Summary",
        "",
        f"- Expected title: `{summary['expected_title']}`",
        f"- Expected source year: `{summary['expected_source_year']}`",
        f"- SHA-256: `{summary['actual_sha256']}`",
        f"- PDF pages: `{summary['pdf_page_count']}`",
        f"- Extracted text lines: `{summary['text_line_count']}`",
        f"- Extracted number/date/citation tokens: `{summary['number_token_count']}`",
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

    summary = build_summary(line_rows, pdf_page_count, token_rows, expected_check_rows)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
