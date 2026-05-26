"""Normalize 2026 Hunt Expo permit draw-result totals from the workbook.

The Expo source publishes permit totals only. This extractor intentionally
does not create resident/nonresident split fields.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
SOURCE_XLSX = ROOT / "pipeline/RAW/hunt_unit_database/2026/xlsx/expo permits 2026.xlsx"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
NORMALIZED_OUT = ROOT / "data_truth/draw_results_truth/normalized/expo_permit_draw_results_2026_total_only.csv"
VALIDATION_OUT = ROOT / "data_truth/draw_results_truth/validation/expo_permit_draw_results_2026_total_only_summary.json"
REPORT_OUT = ROOT / "processed_data/expo_permit_draw_results_2026_total_only.md"

HEADER_RE = re.compile(r"^(?P<body>.+?) - Permits: (?P<permits>\d+)$")
SEASON_RE = re.compile(r"\((?P<season>early|mid|late)\)", re.IGNORECASE)

SPECIES_SEX = {
    "Buck Deer": ("Deer", "Buck"),
    "Bull Elk": ("Elk", "Bull"),
    "Antlerless Elk": ("Elk", "Antlerless"),
    "Buck Pronghorn": ("Pronghorn", "Buck"),
    "Bull Moose": ("Moose", "Bull"),
    "Bison": ("Bison", ""),
    "Black Bear": ("Black Bear", "Either Sex"),
    "Desert Bighorn Sheep": ("Desert Bighorn Sheep", "Male Only"),
    "Rocky Mtn. Bighorn Sheep": ("Rocky Mountain Bighorn Sheep", "Ram"),
    "Mountain Goat": ("Mountain Goat", "Hunters Choice"),
    "Turkey": ("Turkey", "Bearded"),
}


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("\ufeff", "")


def norm(value: str) -> str:
    text = clean(value).lower()
    text = text.replace("&", "and")
    replacements = {
        "mtns": "mountains",
        "mtn": "mountain",
        "mt ": "mount ",
        "l.e.": "limited entry",
        "le": "limited entry",
        "rocky mtn.": "rocky mountain",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_database() -> list[dict[str, str]]:
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def source_species(parts: list[str]) -> tuple[str, str]:
    label = parts[0]
    if label not in SPECIES_SEX:
        raise ValueError(f"Unsupported Expo species label: {label}")
    return SPECIES_SEX[label]


def normalize_weapon(source_weapon: str, extra_season: str = "") -> tuple[str, str, str]:
    source_weapon = clean(source_weapon)
    season_segment = clean(extra_season)
    match = SEASON_RE.search(source_weapon)
    if match:
        season_segment = match.group("season").title()
        source_weapon = SEASON_RE.sub("", source_weapon).strip()

    weapon = source_weapon
    weapon = weapon.replace("Any Weapon", "Any Legal Weapon")
    weapon = weapon.replace("Premium ", "")
    weapon = weapon.replace("Hunter Choice Archery", "Archery")
    weapon = weapon.replace("Hunter Choice", "Any Legal Weapon")
    weapon = weapon.replace("Multi-Season", "Multiseason")
    weapon = weapon.replace("Management Buck, ", "")
    weapon = weapon.replace("Spring, Limited Entry", "Any Legal Weapon")
    weapon = weapon.strip(" ,-")

    if source_weapon.startswith("Premium ") and not season_segment:
        season_segment = "Premium"
    if source_weapon.startswith("Late-season "):
        season_segment = "Late"
        weapon = source_weapon.replace("Late-season ", "").strip()
    if source_weapon.startswith("Management Buck"):
        season_segment = "Management Buck"
    if not weapon:
        weapon = "Any Legal Weapon"

    database_weapon = weapon
    if season_segment in {"Early", "Mid", "Late"} and weapon == "Any Legal Weapon":
        database_weapon = f"{season_segment} Any Legal Weapon"
    elif season_segment == "Late" and weapon == "Archery":
        database_weapon = "Late Archery"
    return weapon, season_segment, database_weapon


def parse_header(row_number: int, text: str) -> dict[str, str]:
    match = HEADER_RE.match(text)
    if not match:
        raise ValueError(f"Row {row_number} is not an Expo permit header: {text}")
    body = match.group("body")
    permits = match.group("permits")
    parts = [part.strip() for part in body.split(" - ")]
    species, sex_type = source_species(parts)
    source_hunt_type = parts[1] if len(parts) > 1 else ""

    source_weapon = parts[2] if len(parts) > 2 else ""
    hunt_unit = parts[3] if len(parts) > 3 else ""
    trailing = parts[4:] if len(parts) > 4 else []

    if species == "Bison":
        sex_type = "Hunters Choice"
        if trailing:
            sex_label = trailing[0]
            if "cow" in sex_label.lower():
                sex_type = "Female Only"
            elif "hunter" in sex_label.lower():
                sex_type = "Hunters Choice"
            source_weapon = "Any Legal Weapon"
            extra_season = sex_label
        else:
            extra_season = ""
    else:
        extra_season = ""

    if species == "Mountain Goat" and source_weapon.lower().startswith("hunter choice"):
        sex_type = "Hunters Choice"
    if species == "Turkey":
        source_hunt_type = "Limited Entry"

    weapon, season_segment, database_weapon = normalize_weapon(source_weapon, extra_season)
    if species == "Bison" and extra_season:
        season_match = SEASON_RE.search(extra_season)
        season_segment = season_match.group("season").title() if season_match else clean(extra_season)

    return {
        "source_row": str(row_number),
        "source_text": text,
        "species": species,
        "sex_type": sex_type,
        "hunt_type": source_hunt_type,
        "hunt_unit": hunt_unit,
        "weapon": weapon,
        "season_segment": season_segment,
        "database_weapon_candidate": database_weapon,
        "permits_2026_total": permits,
        "source_file": SOURCE_XLSX.relative_to(ROOT).as_posix(),
        "source_sheet": "Sheet1",
    }


def sex_compatible(source: str, database: str) -> bool:
    if source == database:
        return True
    aliases = {
        ("Male Only", "Ram"),
        ("Ram", "Male Only"),
        ("Female Only", "Cow Only"),
        ("Cow Only", "Female Only"),
        ("Hunters Choice", "Either Sex"),
        ("Either Sex", "Hunters Choice"),
    }
    return (source, database) in aliases


def map_to_database(row: dict[str, str], database_rows: list[dict[str, str]]) -> dict[str, str]:
    unit_key = norm(row["hunt_unit"])
    weapon_key = norm(row["database_weapon_candidate"])
    candidates = []
    for db in database_rows:
        if db.get("species") != row["species"]:
            continue
        if not sex_compatible(row["sex_type"], db.get("sex_type", "")):
            continue
        if unit_key and unit_key not in norm(db.get("hunt_name", "")) and norm(db.get("hunt_name", "")) not in unit_key:
            continue
        if weapon_key and weapon_key != norm(db.get("weapon", "")):
            continue
        candidates.append(db)

    if len(candidates) == 1:
        db = candidates[0]
        return {
            "hunt_code": db.get("hunt_code", ""),
            "boundary_id": db.get("boundary_id", ""),
            "mapping_status": "MATCH_HIGH",
            "database_hunt_name": db.get("hunt_name", ""),
            "database_weapon": db.get("weapon", ""),
            "database_season": db.get("season", ""),
        }
    if not candidates:
        return {
            "hunt_code": "",
            "boundary_id": "",
            "mapping_status": "NO_DATABASE_MATCH",
            "database_hunt_name": "",
            "database_weapon": "",
            "database_season": "",
        }
    return {
        "hunt_code": "|".join(db.get("hunt_code", "") for db in candidates[:10]),
        "boundary_id": "|".join(db.get("boundary_id", "") for db in candidates[:10]),
        "mapping_status": "AMBIGUOUS_DATABASE_MATCH",
        "database_hunt_name": "|".join(db.get("hunt_name", "") for db in candidates[:10]),
        "database_weapon": "|".join(db.get("weapon", "") for db in candidates[:10]),
        "database_season": "|".join(db.get("season", "") for db in candidates[:10]),
    }


def extract_rows() -> list[dict[str, str]]:
    workbook = openpyxl.load_workbook(SOURCE_XLSX, data_only=True, read_only=True)
    rows = []
    for sheet in workbook.worksheets:
        for row_number, cells in enumerate(sheet.iter_rows(values_only=True), start=1):
            text = clean(cells[0] if cells else "")
            if "Permits:" not in text:
                continue
            parsed = parse_header(row_number, text)
            parsed["source_sheet"] = sheet.title
            rows.append(parsed)
    return rows


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    database_rows = read_database()
    rows = []
    for extracted in extract_rows():
        mapped = map_to_database(extracted, database_rows)
        rows.append({"snapshot_utc": timestamp, **extracted, **mapped})

    fields = [
        "snapshot_utc",
        "hunt_code",
        "boundary_id",
        "mapping_status",
        "species",
        "sex_type",
        "hunt_type",
        "hunt_unit",
        "weapon",
        "season_segment",
        "database_weapon_candidate",
        "database_hunt_name",
        "database_weapon",
        "database_season",
        "permits_2026_total",
        "source_file",
        "source_sheet",
        "source_row",
        "source_text",
    ]
    write_csv(NORMALIZED_OUT, rows, fields)

    mapping_counts = Counter(row["mapping_status"] for row in rows)
    species_counts = Counter(row["species"] for row in rows)
    total_permits = sum(int(row["permits_2026_total"]) for row in rows)
    summary = {
        "artifact": "expo_permit_draw_results_2026_total_only",
        "snapshot_utc": timestamp,
        "source_file": SOURCE_XLSX.relative_to(ROOT).as_posix(),
        "row_count": len(rows),
        "total_expo_permits": total_permits,
        "mapping_status_counts": dict(sorted(mapping_counts.items())),
        "species_counts": dict(sorted(species_counts.items())),
        "guardrail": "Expo permits are published as permits_2026_total only; no resident or nonresident split fields are created.",
        "outputs": {
            "normalized_csv": NORMALIZED_OUT.relative_to(ROOT).as_posix(),
            "summary_json": VALIDATION_OUT.relative_to(ROOT).as_posix(),
            "report_md": REPORT_OUT.relative_to(ROOT).as_posix(),
        },
    }
    VALIDATION_OUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Expo Permit Draw Results 2026 Total-Only",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- Source file: `{summary['source_file']}`",
        f"- Rows extracted: `{len(rows)}`",
        f"- Total Expo permits: `{total_permits}`",
        "",
        "## Mapping Status Counts",
        "",
    ]
    for status, count in sorted(mapping_counts.items()):
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Species Counts", ""])
    for species, count in sorted(species_counts.items()):
        lines.append(f"- `{species}`: `{count}`")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
