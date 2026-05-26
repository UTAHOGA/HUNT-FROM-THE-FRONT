from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Big Game Application.pdf"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
OUT_DIR = ROOT / "data_truth/regulations_truth/normalized"
REPORT_DIR = ROOT / "processed_data"

GUIDEBOOK_HUNT_TABLES = OUT_DIR / "2026_big_game_application_guidebook_hunt_tables.csv"
GUIDEBOOK_POST_PUBLICATION_CORRECTIONS = (
    OUT_DIR / "2026_big_game_application_guidebook_post_publication_corrections.csv"
)
GUIDEBOOK_COMPARE = REPORT_DIR / "2026_big_game_application_guidebook_vs_DATABASE.csv"
GUIDEBOOK_SUMMARY = REPORT_DIR / "2026_big_game_application_guidebook_vs_DATABASE_summary.json"
GUIDEBOOK_MD = REPORT_DIR / "2026_big_game_application_guidebook_vs_DATABASE.md"

CODE_RE = re.compile(r"\b([A-Z]{2}\d{4})\b")
DATE_TOKEN_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2}\b",
    re.IGNORECASE,
)

NOISE_PREFIXES = (
    "Hunt name Hunt #",
    "Use the hunt number",
    "game application by selecting",
)

SPECIES_BY_PREFIX = {
    "DB": "Deer",
    "EB": "Elk",
    "PB": "Pronghorn",
    "MB": "Moose",
    "BI": "Bison",
    "DS": "Desert Bighorn Sheep",
    "RS": "Rocky Mountain Bighorn Sheep",
    "GO": "Mountain Goat",
    "BR": "Black Bear",
    "TK": "Turkey",
}

POST_PUBLICATION_CORRECTIONS = [
    {
        "hunt_code": "DB1276",
        "guidebook_page": "72",
        "correction_date": "2026-04-06",
        "action": "DELETE_HUNT_ROW",
        "corrected_value": "",
        "superseded_by_hunt_code": "DB1306",
        "reason": "Plymouth Peak is no longer a CWMU and was combined with Washakie CWMU.",
    },
    {
        "hunt_code": "MB6264",
        "guidebook_page": "78",
        "correction_date": "2026-03-13",
        "action": "DELETE_HUNT_ROW",
        "corrected_value": "",
        "superseded_by_hunt_code": "",
        "reason": "Sand Creek CWMU was included in error; there is no public moose permit this year on that CWMU.",
    },
    {
        "hunt_code": "DB1115",
        "guidebook_page": "51",
        "correction_date": "2026-03-03",
        "action": "RENAME_HUNT",
        "corrected_value": "Little Rockies",
        "superseded_by_hunt_code": "",
        "reason": "Hunt name shortened from Henry Mtns, Little Rockies to Little Rockies.",
    },
    {
        "hunt_code": "DB1350",
        "guidebook_page": "71",
        "correction_date": "2026-02-25",
        "action": "DELETE_HUNT_ROW",
        "corrected_value": "",
        "superseded_by_hunt_code": "",
        "reason": "Milburn CWMU withdrew from the program.",
    },
]


@dataclass
class GuidebookRow:
    hunt_code: str
    guidebook_page: int
    guidebook_section: str
    species_inferred: str
    guidebook_hunt_name: str
    guidebook_detail_text: str
    guidebook_season_text: str
    guidebook_county_text: str
    guidebook_public_permits: str
    raw_line: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "hunt_code": self.hunt_code,
            "guidebook_page": self.guidebook_page,
            "guidebook_section": self.guidebook_section,
            "species_inferred": self.species_inferred,
            "guidebook_hunt_name": self.guidebook_hunt_name,
            "guidebook_detail_text": self.guidebook_detail_text,
            "guidebook_season_text": self.guidebook_season_text,
            "guidebook_county_text": self.guidebook_county_text,
            "guidebook_public_permits": self.guidebook_public_permits,
            "raw_line": self.raw_line,
        }


def clean_text(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    value = re.sub(r"[†‡*^]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_name(value: str) -> str:
    value = clean_text(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\b(new|premium|limited|entry|hunt|hunts|cwmu)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalized_date_tokens(value: str) -> list[str]:
    value = clean_text(value).replace("Sept", "Sep")
    tokens = []
    expanded_range_re = re.compile(
        r"\b(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+"
        r"(?P<start>\d{1,2})\s*-\s*(?P<end>\d{1,2})\b",
        re.IGNORECASE,
    )
    for match in expanded_range_re.finditer(value):
        month = match.group("month").replace(".", "").title()
        tokens.append(f"{month} {int(match.group('start'))}")
        tokens.append(f"{month} {int(match.group('end'))}")
    for match in DATE_TOKEN_RE.findall(value):
        token = match.replace(".", "").replace("Sept", "Sep")
        month, day = re.sub(r"\s+", " ", token).title().split()
        normalized = f"{month} {int(day)}"
        if normalized not in tokens:
            tokens.append(normalized)
    return tokens


def section_for_page(page: int, line: str) -> str:
    upper = line.upper()
    if page in range(43, 54):
        return "BUCK_DEER_HUNT_TABLES"
    if page in range(54, 61):
        return "BULL_ELK_HUNT_TABLES"
    if page in range(61, 64):
        return "BUCK_PRONGHORN_HUNT_TABLES"
    if page == 64:
        return "BUCK_PRONGHORN_OR_BULL_MOOSE_HUNT_TABLES"
    if page == 65:
        return "BISON_HUNT_TABLES"
    if page in range(66, 68):
        return "BIGHORN_SHEEP_HUNT_TABLES"
    if page == 68:
        return "MOUNTAIN_GOAT_HUNT_TABLES"
    if page in range(69, 79):
        return "CWMU_HUNT_TABLES"
    if page == 10:
        return "SPORTSMAN_AND_STATEWIDE_CONSERVATION_DATES"
    if "EXTENDED ARCHERY" in upper:
        return "EXTENDED_ARCHERY_REFERENCE"
    return "GUIDEBOOK_REFERENCE"


def parse_guidebook_line(page: int, line: str) -> list[GuidebookRow]:
    line = clean_text(line)
    if not line or any(line.startswith(prefix) for prefix in NOISE_PREFIXES):
        return []

    rows = []
    for match in CODE_RE.finditer(line):
        code = match.group(1)
        before = clean_text(line[: match.start()])
        after = clean_text(line[match.end() :])
        section = section_for_page(page, line)
        species = SPECIES_BY_PREFIX.get(code[:2], "")

        if before:
            name = before
            detail = after
        else:
            detail = after
            date_match = DATE_TOKEN_RE.search(after)
            if date_match:
                name = clean_text(after[: date_match.start()])
                detail = clean_text(after[date_match.start() :])
            else:
                parts = after.split()
                name = " ".join(parts[:2]) if len(parts) > 1 else after

        name = re.sub(r"^(?:Hunt name|Any legal weapon hunts?|Archery hunts?)\s+", "", name, flags=re.I)
        name = clean_text(name)

        county = ""
        public_permits = ""
        season = detail
        if section == "CWMU_HUNT_TABLES":
            county_match = re.match(r"(?P<county>.+?)\s+(?P<permits>\d+)$", detail)
            if county_match:
                county = clean_text(county_match.group("county"))
                public_permits = county_match.group("permits")
                season = ""

        rows.append(
            GuidebookRow(
                hunt_code=code,
                guidebook_page=page,
                guidebook_section=section,
                species_inferred=species,
                guidebook_hunt_name=name,
                guidebook_detail_text=detail,
                guidebook_season_text=season,
                guidebook_county_text=county,
                guidebook_public_permits=public_permits,
                raw_line=line,
            )
        )
    return rows


def choose_best_rows(rows: Iterable[GuidebookRow]) -> list[GuidebookRow]:
    by_code: dict[str, list[GuidebookRow]] = {}
    for row in rows:
        by_code.setdefault(row.hunt_code, []).append(row)

    best = []
    for code, candidates in by_code.items():
        candidates = sorted(
            candidates,
            key=lambda row: (
                0 if row.guidebook_page >= 43 else 1,
                0 if row.guidebook_hunt_name and not row.guidebook_hunt_name.lower().startswith("game application") else 1,
                row.guidebook_page,
            ),
        )
        best.append(candidates[0])
    return sorted(best, key=lambda row: (row.hunt_code, row.guidebook_page))


def extract_guidebook_rows() -> list[GuidebookRow]:
    rows: list[GuidebookRow] = []
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            if not (8 <= page_index <= 78):
                continue
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            for line in text.splitlines():
                rows.extend(parse_guidebook_line(page_index, line))
    return choose_best_rows(rows)


def apply_post_publication_corrections(rows: list[GuidebookRow]) -> list[GuidebookRow]:
    delete_codes = {
        correction["hunt_code"]
        for correction in POST_PUBLICATION_CORRECTIONS
        if correction["action"] == "DELETE_HUNT_ROW"
    }
    rename_by_code = {
        correction["hunt_code"]: correction["corrected_value"]
        for correction in POST_PUBLICATION_CORRECTIONS
        if correction["action"] == "RENAME_HUNT"
    }

    corrected_rows = []
    for row in rows:
        if row.hunt_code in delete_codes:
            continue
        if row.hunt_code in rename_by_code and row.guidebook_hunt_name != rename_by_code[row.hunt_code]:
            row = GuidebookRow(
                hunt_code=row.hunt_code,
                guidebook_page=row.guidebook_page,
                guidebook_section=row.guidebook_section,
                species_inferred=row.species_inferred,
                guidebook_hunt_name=rename_by_code[row.hunt_code],
                guidebook_detail_text=row.guidebook_detail_text,
                guidebook_season_text=row.guidebook_season_text,
                guidebook_county_text=row.guidebook_county_text,
                guidebook_public_permits=row.guidebook_public_permits,
                raw_line=row.raw_line,
            )
        corrected_rows.append(row)
    return corrected_rows


def read_database() -> dict[str, dict[str, str]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        return {row["hunt_code"]: row for row in csv.DictReader(handle)}


def build_post_publication_correction_rows(
    extracted_rows: list[GuidebookRow],
    corrected_rows: list[GuidebookRow],
    database: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    extracted_by_code = {row.hunt_code: row for row in extracted_rows}
    corrected_by_code = {row.hunt_code: row for row in corrected_rows}
    output = []

    for correction in POST_PUBLICATION_CORRECTIONS:
        code = correction["hunt_code"]
        extracted_row = extracted_by_code.get(code)
        corrected_row = corrected_by_code.get(code)
        database_row = database.get(code, {})
        superseded_by = correction["superseded_by_hunt_code"]
        superseded_row = database.get(superseded_by, {}) if superseded_by else {}

        if correction["action"] == "DELETE_HUNT_ROW":
            status = "PASS" if corrected_row is None and code not in database else "REVIEW"
        else:
            expected = correction["corrected_value"]
            status = (
                "PASS"
                if corrected_row is not None
                and corrected_row.guidebook_hunt_name == expected
                and database_row.get("hunt_name", "") == expected
                else "REVIEW"
            )

        output.append(
            {
                "hunt_code": code,
                "guidebook_page": correction["guidebook_page"],
                "correction_date": correction["correction_date"],
                "action": correction["action"],
                "corrected_value": correction["corrected_value"],
                "superseded_by_hunt_code": superseded_by,
                "reason": correction["reason"],
                "source_row_found_before_correction": str(extracted_row is not None).lower(),
                "source_row_present_after_correction": str(corrected_row is not None).lower(),
                "database_row_present": str(code in database).lower(),
                "database_hunt_name": database_row.get("hunt_name", ""),
                "superseded_by_database_row_present": str(bool(superseded_row)).lower(),
                "superseded_by_database_hunt_name": superseded_row.get("hunt_name", ""),
                "validation_status": status,
            }
        )
    return output


def overlap_score(left: str, right: str) -> float:
    left_tokens = set(normalize_name(left).split())
    right_tokens = set(normalize_name(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def compare_rows(guidebook_rows: list[GuidebookRow], database: dict[str, dict[str, str]]) -> list[dict[str, str | int | float]]:
    comparisons = []
    for row in guidebook_rows:
        db_row = database.get(row.hunt_code)
        if not db_row:
            comparisons.append(
                {
                    **row.to_dict(),
                    "database_status": "MISSING_IN_DATABASE",
                    "database_hunt_name": "",
                    "database_species": "",
                    "database_season": "",
                    "name_overlap_score": "",
                    "name_status": "MISSING_IN_DATABASE",
                    "season_status": "MISSING_IN_DATABASE",
                    "difference_severity": "BLOCKER",
                    "difference_reason": "GUIDEBOOK_HUNT_CODE_NOT_IN_DATABASE",
                }
            )
            continue

        name_score = overlap_score(row.guidebook_hunt_name, db_row.get("hunt_name", ""))
        raw_code_count = len(CODE_RE.findall(row.raw_line))
        if raw_code_count > 1:
            name_status = "MULTI_COLUMN_TEXT_NOT_COMPARABLE"
        elif row.guidebook_section == "SPORTSMAN_AND_STATEWIDE_CONSERVATION_DATES":
            name_status = "SPORTSMAN_STATEWIDE_LABEL_VARIANT"
        else:
            name_status = "MATCH" if name_score >= 0.5 else "REVIEW"

        guide_dates = normalized_date_tokens(row.guidebook_season_text)
        db_dates = normalized_date_tokens(db_row.get("season", ""))
        if not row.guidebook_season_text or row.guidebook_season_text.lower().startswith(("see ", "all ", "limited-entry")):
            season_status = "REFERENCE_OR_COMPOSITE_SEASON"
        elif guide_dates and db_dates and all(token in db_dates for token in guide_dates):
            season_status = "MATCH"
        elif guide_dates and db_dates:
            season_status = "REVIEW"
        else:
            season_status = "NOT_COMPARABLE"

        severity = "OK"
        reason = ""
        if name_status == "REVIEW":
            severity = "WARNING"
            reason = "NAME_NEEDS_REVIEW"
        if season_status == "REVIEW":
            severity = "WARNING"
            reason = f"{reason};SEASON_NEEDS_REVIEW" if reason else "SEASON_NEEDS_REVIEW"

        comparisons.append(
            {
                **row.to_dict(),
                "database_status": "MATCHED",
                "database_hunt_name": db_row.get("hunt_name", ""),
                "database_species": db_row.get("species", ""),
                "database_season": db_row.get("season", ""),
                "name_overlap_score": round(name_score, 3),
                "name_status": name_status,
                "season_status": season_status,
                "difference_severity": severity,
                "difference_reason": reason,
            }
        )
    return comparisons


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(
    summary: dict[str, object],
    comparisons: list[dict[str, object]],
    post_publication_corrections: list[dict[str, str]],
) -> None:
    blockers = [row for row in comparisons if row["difference_severity"] == "BLOCKER"]
    warnings = [row for row in comparisons if row["difference_severity"] == "WARNING"]
    lines = [
        "# 2026 Big Game Application Guidebook vs DATABASE Audit",
        "",
        "Source PDF: `pipeline/RAW/hunt_unit_database/2026/pdf/regulations/2026 Big Game Application.pdf`",
        "",
        "This is a regulation/reference audit. It does not promote guidebook text into draw odds, harvest features, or 2026 quota math.",
        "",
        "## Summary",
        "",
        f"- Guidebook hunt codes extracted: `{summary['guidebook_unique_hunt_codes']}`",
        f"- Guidebook hunt codes found in DATABASE.csv: `{summary['matched_database_hunt_codes']}`",
        f"- Guidebook hunt codes missing from DATABASE.csv: `{summary['missing_database_hunt_codes']}`",
        f"- Name review warnings: `{summary['name_review_warnings']}`",
        f"- Season review warnings: `{summary['season_review_warnings']}`",
        f"- Blockers: `{summary['blockers']}`",
        f"- Post-publication corrections checked: `{summary['post_publication_correction_count']}`",
        f"- Post-publication correction review items: `{summary['post_publication_correction_review_count']}`",
        "",
        "## Post-Publication Corrections",
        "",
        "| hunt_code | action | status | correction |",
        "|---|---|---:|---|",
    ]
    for correction in post_publication_corrections:
        lines.append(
            "| {hunt_code} | {action} | {validation_status} | {reason} |".format(**correction)
        )
    lines.extend(
        [
            "",
            "## Significant Differences",
            "",
        ]
    )
    if not blockers and not warnings:
        lines.append("No blocker-level differences were found. All extracted guidebook hunt codes are present in `DATABASE.csv`.")
    else:
        lines.extend(["| hunt_code | severity | reason | guidebook | database |", "|---|---:|---|---|---|"])
        for row in blockers + warnings[:75]:
            lines.append(
                "| {hunt_code} | {difference_severity} | {difference_reason} | {guidebook_hunt_name} | {database_hunt_name} |".format(
                    **row
                )
            )
    lines.append("")
    lines.append("Full row-level comparison: `processed_data/2026_big_game_application_guidebook_vs_DATABASE.csv`")
    GUIDEBOOK_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    extracted_guidebook_rows = extract_guidebook_rows()
    guidebook_rows = apply_post_publication_corrections(extracted_guidebook_rows)
    database = read_database()
    post_publication_corrections = build_post_publication_correction_rows(
        extracted_guidebook_rows, guidebook_rows, database
    )
    comparisons = compare_rows(guidebook_rows, database)

    status_counts = Counter(row["difference_severity"] for row in comparisons)
    season_counts = Counter(row["season_status"] for row in comparisons)
    name_counts = Counter(row["name_status"] for row in comparisons)
    section_counts = Counter(row.guidebook_section for row in guidebook_rows)

    summary = {
        "source_pdf": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "database": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
        "guidebook_unique_hunt_codes": len({row.hunt_code for row in guidebook_rows}),
        "guidebook_rows": len(guidebook_rows),
        "matched_database_hunt_codes": sum(1 for row in comparisons if row["database_status"] == "MATCHED"),
        "missing_database_hunt_codes": sum(1 for row in comparisons if row["database_status"] == "MISSING_IN_DATABASE"),
        "name_review_warnings": sum(1 for row in comparisons if row["name_status"] == "REVIEW"),
        "season_review_warnings": sum(1 for row in comparisons if row["season_status"] == "REVIEW"),
        "blockers": status_counts.get("BLOCKER", 0),
        "warnings": status_counts.get("WARNING", 0),
        "post_publication_correction_count": len(post_publication_corrections),
        "post_publication_correction_review_count": sum(
            1 for row in post_publication_corrections if row["validation_status"] != "PASS"
        ),
        "post_publication_correction_status_counts": dict(
            Counter(row["validation_status"] for row in post_publication_corrections)
        ),
        "status_counts": dict(status_counts),
        "name_status_counts": dict(name_counts),
        "season_status_counts": dict(season_counts),
        "section_counts": dict(section_counts),
        "classification": "REGULATION_REFERENCE_ONLY",
        "modeling_guardrail": "DO_NOT_USE_AS_DRAW_ODDS_HARVEST_FEATURE_OR_2026_QUOTA_INPUT",
    }

    write_csv(GUIDEBOOK_HUNT_TABLES, [row.to_dict() for row in guidebook_rows])
    write_csv(GUIDEBOOK_POST_PUBLICATION_CORRECTIONS, post_publication_corrections)
    write_csv(GUIDEBOOK_COMPARE, comparisons)
    GUIDEBOOK_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, comparisons, post_publication_corrections)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
