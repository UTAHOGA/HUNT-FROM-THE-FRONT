from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader


REPO = Path(__file__).resolve().parents[1]
PDF_PATH = REPO / "pipeline/RAW/hunt_unit_database/2026/pdf/Conservation Permits/2025-27 Conservation Permits.pdf"
OUT_DIR = REPO / "pipeline/RAW/hunt_unit_database/2026/reports"
OUT_DETAIL = OUT_DIR / "conservation_permits_2025_2027_extracted_detail.csv"
OUT_GROUPED = OUT_DIR / "conservation_permits_2025_2027_grouped.csv"
OUT_JSON = OUT_DIR / "conservation_permits_2025_2027_extraction_report.json"

SPECIES = [
    "Rocky Mountain Bighorn Sheep",
    "Desert Bighorn Sheep",
    "Mountain Goat",
    "Antlerless Elk",
    "Pronghorn",
    "Bison",
    "Moose",
    "Turkey",
    "Bear",
    "Deer",
    "Elk",
]

ORG_CODES = {
    "RMEF",
    "WCF",
    "NWTF",
    "SCI",
    "SFW",
    "UAA",
    "MDF",
    "DSC",
    "UHA",
    "UWSF",
    "UCWF",
}

CONDITION_KEYWORDS = [
    "Any Legal Weapon, late",
    "Any Legal Weapon, mid",
    "Any Legal Weapon, early",
    "Hunter's Choice (early)",
    "Hunter's Choice (late)",
    "Cow Only (late)",
    "Any Legal Weapon",
    "Hunter's Choice",
    "Multiseason",
    "Muzzleloader",
    "Archery",
]

CONDITION_NOTES = {
    "Hunter's Choice": "Winning bidder chooses one eligible season for that unit/species; this is not a multiseason permit.",
    "Hunter's Choice (early)": "Hunter's Choice label from source; interpreted as season-choice for the listed early season context, not multiseason.",
    "Hunter's Choice (late)": "Hunter's Choice label from source; interpreted as season-choice for the listed late season context, not multiseason.",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_money(value: str) -> str:
    return value.replace(",", "").replace("$", "").strip()


def starts_with_species(line: str) -> str:
    for species in SPECIES:
        if line.startswith(species + " "):
            return species
    return ""


def strip_leading_noise(line: str) -> str:
    line = clean_text(line)
    line = re.sub(r"^\d+\s+", "", line)
    return clean_text(line)


def split_condition(area_condition: str) -> tuple[str, str]:
    for condition in CONDITION_KEYWORDS:
        if area_condition.endswith(" " + condition):
            return clean_text(area_condition[: -len(condition)]), condition
    return clean_text(area_condition), ""


def parse_line(line: str, page_number: int, raw_line_number: int) -> dict | None:
    line = strip_leading_noise(line)
    if not line or line.startswith("No. Species Area Condition") or "Total permits issued" in line:
        return None
    species = starts_with_species(line)
    if not species:
        return None

    value_match = re.search(r"\$[\d,]+(?:\.\d{2})?", line)
    if not value_match:
        return None

    before_value = clean_text(line[len(species) : value_match.start()])
    after_value = clean_text(line[value_match.end() :])
    trailing_parts = after_value.split()
    organization = ""
    for part in reversed(trailing_parts):
        if part in ORG_CODES:
            organization = part
            break
    if not organization and trailing_parts:
        organization = trailing_parts[-1]

    area, condition = split_condition(before_value)
    if not area:
        return None

    return {
        "source_pdf": str(PDF_PATH.relative_to(REPO)).replace("\\", "/"),
        "page": page_number,
        "raw_line": raw_line_number,
        "species": species,
        "area": area,
        "condition": condition,
        "value": normalize_money(value_match.group(0)),
        "organization": organization,
        "raw_text": line,
    }


def extract_rows() -> list[dict]:
    reader = PdfReader(str(PDF_PATH))
    extracted: list[dict] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for raw_line_number, raw_line in enumerate(text.splitlines(), start=1):
            parsed = parse_line(raw_line, page_number, raw_line_number)
            if parsed:
                extracted.append(parsed)
    return extracted


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def main() -> None:
    rows = extract_rows()
    detail_headers = [
        "source_pdf",
        "page",
        "raw_line",
        "species",
        "area",
        "condition",
        "value",
        "organization",
        "raw_text",
    ]
    write_csv(OUT_DETAIL, rows, detail_headers)

    grouped_map: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        key = (row["species"], row["area"], row["condition"])
        target = grouped_map.setdefault(
            key,
            {
                "species": row["species"],
                "area": row["area"],
                "condition": row["condition"],
                "condition_note": CONDITION_NOTES.get(row["condition"], ""),
                "conservation_permit_count_2025_2027": 0,
                "permits_2026_conservation": 0,
                "organizations": set(),
                "total_value": 0.0,
                "source_pdf": row["source_pdf"],
            },
        )
        target["conservation_permit_count_2025_2027"] += 1
        # Conservation permit allocations are set for the full 2025-2027 cycle.
        # The count therefore applies to each year in the cycle, including 2026.
        target["permits_2026_conservation"] += 1
        target["organizations"].add(row["organization"])
        try:
            target["total_value"] += float(row["value"])
        except ValueError:
            pass

    grouped = []
    for row in grouped_map.values():
        grouped.append(
            {
                **row,
                "organizations": ";".join(sorted(row["organizations"])),
                "total_value": f"{row['total_value']:.2f}",
            }
        )
    grouped.sort(key=lambda item: (item["species"], item["area"], item["condition"]))
    write_csv(
        OUT_GROUPED,
        grouped,
        [
            "species",
            "area",
            "condition",
            "condition_note",
            "conservation_permit_count_2025_2027",
            "permits_2026_conservation",
            "organizations",
            "total_value",
            "source_pdf",
        ],
    )

    species_counts = Counter(row["species"] for row in rows)
    report = {
        "source_pdf": str(PDF_PATH.relative_to(REPO)).replace("\\", "/"),
        "detail_csv": str(OUT_DETAIL.relative_to(REPO)).replace("\\", "/"),
        "grouped_csv": str(OUT_GROUPED.relative_to(REPO)).replace("\\", "/"),
        "rows_extracted": len(rows),
        "grouped_rows": len(grouped),
        "species_counts": dict(sorted(species_counts.items())),
        "note": "The source is a 2025-2027 multi-year conservation permit working list. Because conservation allocations are set for the three-year cycle, conservation_permit_count_2025_2027 is treated as permits_2026_conservation, not divided by three. Counts are kept separate from normal public draw allocation fields.",
    }
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
