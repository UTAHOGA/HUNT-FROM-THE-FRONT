from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATABASE_CSV = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
SOURCE_AUDIT_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits.csv"
)

PROMOTION_CSV = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "source_only_2024_draw_pdf_values_promoted_to_DATABASE_2025.csv"
)
SUMMARY_JSON = (
    ROOT
    / "data_truth/draw_results_truth/validation/"
    / "source_only_2024_draw_pdf_values_promoted_to_DATABASE_2025_summary.json"
)
REPORT_MD = ROOT / "processed_data/source_only_2024_draw_pdf_values_promoted_to_DATABASE_2025.md"

SOURCE_LABEL = "2024_DRAW_RESULTS_PDF_MODEL_TARGET_2025_SOURCE_ONLY_PROMOTION"
HISTORICAL_SEASON_NOTE = "Historical 2025 draw only; season dates not validated in current DATABASE"


CODE_METADATA: dict[str, dict[str, str]] = {
    "BI6530": {"boundary_id": "889", "hunt_name": "Book Cliffs, Little Creek/South", "sex_type": "Hunters Choice", "species": "Bison", "weapon": "Any Legal Weapon", "hunt_type": "Once-in-a-lifetime"},
    "DA1044": {"boundary_id": "864", "hunt_name": "Myton", "sex_type": "Antlerless", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "General Season"},
    "DB1036": {"boundary_id": "632", "hunt_name": "Thousand Lakes", "sex_type": "Buck", "species": "Deer", "weapon": "Muzzleloader", "hunt_type": "Limited Entry"},
    "DB1059": {"boundary_id": "628", "hunt_name": "Beaver", "sex_type": "Buck", "species": "Deer", "weapon": "Muzzleloader", "hunt_type": "Limited Entry"},
    "DB1082": {"boundary_id": "622", "hunt_name": "Oquirrh-Stansbury", "sex_type": "Buck", "species": "Deer", "weapon": "Muzzleloader", "hunt_type": "Limited Entry"},
    "DB1088": {"boundary_id": "624", "hunt_name": "West Desert, Tintic", "sex_type": "Buck", "species": "Deer", "weapon": "Muzzleloader", "hunt_type": "Limited Entry"},
    "DB1089": {"boundary_id": "623", "hunt_name": "West Desert, West", "sex_type": "Buck", "species": "Deer", "weapon": "Muzzleloader", "hunt_type": "Limited Entry"},
    "DB1094": {"boundary_id": "864", "hunt_name": "Myton", "sex_type": "Buck", "species": "Deer", "weapon": "Muzzleloader", "hunt_type": "Limited Entry"},
    "DB1276": {"boundary_id": "737", "hunt_name": "Plymouth Peak CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DB1320": {"boundary_id": "686", "hunt_name": "Deer Creek CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DB1324": {"boundary_id": "828", "hunt_name": "Royal Ivory Outfitters CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DB1338": {"boundary_id": "891", "hunt_name": "Sweetwater CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DB1343": {"boundary_id": "907", "hunt_name": "Red Iron CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DB1344": {"boundary_id": "906", "hunt_name": "Salt Wells CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DB1345": {"boundary_id": "923", "hunt_name": "Diamond Mountain CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DB1348": {"boundary_id": "922", "hunt_name": "Kimberly CWMU", "sex_type": "Buck", "species": "Deer", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "DS6602": {"boundary_id": "99", "hunt_name": "Kaiparowits, Escalante", "sex_type": "Male Only", "species": "Desert Bighorn Sheep", "weapon": "Any Legal Weapon", "hunt_type": "Once-in-a-lifetime"},
    "EA1040": {"boundary_id": "723", "hunt_name": "Monroe, Koosharem Valley", "sex_type": "Antlerless", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "General Season"},
    "EA1074": {"boundary_id": "636", "hunt_name": "Pine Valley", "sex_type": "Antlerless", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "General Season"},
    "EA1116": {"boundary_id": "635", "hunt_name": "Zion", "sex_type": "Antlerless", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "General Season"},
    "EA1126": {"boundary_id": "640", "hunt_name": "Cotton Thomas CWMU", "sex_type": "Antlerless", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "EA1176": {"boundary_id": "524", "hunt_name": "Weber Florence Creek CWMU", "sex_type": "Antlerless", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "EA1252": {"boundary_id": "893", "hunt_name": "Southwest Desert, Burbank/Garrison", "sex_type": "Antlerless", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "General Season"},
    "EB3561": {"boundary_id": "521", "hunt_name": "Two Bear CWMU", "sex_type": "Bull", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "EB3609": {"boundary_id": "828", "hunt_name": "Royal Ivory Outfitters CWMU", "sex_type": "Bull", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "EB3616": {"boundary_id": "891", "hunt_name": "Sweetwater CWMU", "sex_type": "Bull", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "EB3617": {"boundary_id": "923", "hunt_name": "Diamond Mountain CWMU", "sex_type": "Bull", "species": "Elk", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MA1006": {"boundary_id": "620", "hunt_name": "Wasatch Mtns, West", "sex_type": "Antlerless", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "Once-in-a-lifetime"},
    "MB6200": {"boundary_id": "575", "hunt_name": "Bear Springs CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6207": {"boundary_id": "567", "hunt_name": "Durst Mountain CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6209": {"boundary_id": "522", "hunt_name": "Ensign Ranches CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6217": {"boundary_id": "490", "hunt_name": "Sharp Mountain CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6220": {"boundary_id": "491", "hunt_name": "South Canyon CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6223": {"boundary_id": "553", "hunt_name": "Three C CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6224": {"boundary_id": "521", "hunt_name": "Two Bear CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6240": {"boundary_id": "732", "hunt_name": "Chimney Rock CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6254": {"boundary_id": "576", "hunt_name": "SJ Ranch CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6259": {"boundary_id": "828", "hunt_name": "Royal Ivory Outfitters CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6263": {"boundary_id": "485", "hunt_name": "Moon Ranch CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "MB6264": {"boundary_id": "740", "hunt_name": "Sand Creek CWMU", "sex_type": "Bull", "species": "Moose", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PB5313": {"boundary_id": "805", "hunt_name": "West Willow Creek Ranch CWMU", "sex_type": "Buck", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PB5341": {"boundary_id": "891", "hunt_name": "Sweetwater CWMU", "sex_type": "Buck", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PD1006": {"boundary_id": "171", "hunt_name": "Parker Mtn", "sex_type": "Doe", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "General Season"},
    "PD1016": {"boundary_id": "537", "hunt_name": "Zane CWMU", "sex_type": "Doe", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PD1025": {"boundary_id": "824", "hunt_name": "Cottonwood Ridge CWMU", "sex_type": "Doe", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PD1026": {"boundary_id": "826", "hunt_name": "Pahvant Ensign CWMU", "sex_type": "Doe", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PD1032": {"boundary_id": "581", "hunt_name": "Antelope Creek CWMU", "sex_type": "Doe", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PD1045": {"boundary_id": "509", "hunt_name": "The Rose of Snowville CWMU", "sex_type": "Doe", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
    "PD1046": {"boundary_id": "918", "hunt_name": "Green River Flat CWMU", "sex_type": "Doe", "species": "Pronghorn", "weapon": "Any Legal Weapon", "hunt_type": "CWMU"},
}


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fieldnames})


def clean_int(value: str) -> str:
    return str(int(str(value).strip()))


def make_database_row(source: dict[str, str], fields: list[str]) -> dict[str, str]:
    code = source["hunt_code"].strip()
    meta = CODE_METADATA[code]
    res = clean_int(source["resident_total_permits"])
    nr = clean_int(source["nonresident_total_permits"])
    total = clean_int(source["total_public_draw_permits"])

    row = {field: "" for field in fields}
    row.update(
        {
            "hunt_code": code,
            "boundary_id": meta["boundary_id"],
            "hunt_name": meta["hunt_name"],
            "sex_type": meta["sex_type"],
            "species": meta["species"],
            "weapon": meta["weapon"],
            "hunt_type": meta["hunt_type"],
            "season": HISTORICAL_SEASON_NOTE,
            "NOTES": "HISTORICAL_2025_DRAW_ONLY_NOT_ACTIVE_2026",
            "permits_2025_draw_res": res,
            "permits_2025_draw_nr": nr,
            "permits_2025_draw_total": total,
            "draw_2025_bg_pdf_page": source["source_page"].strip(),
            "draw_2025_type": "2024 Draw Results PDF Model Target 2025",
            "permits_2025_draw_source": SOURCE_LABEL,
            "permits_2025_res": res,
            "permits_2025_nr": nr,
            "permits_2025_total": total,
            "permits_2025_source": SOURCE_LABEL,
            "permit_allotment_2026_status": "HISTORICAL_2025_ONLY_NOT_ACTIVE_2026",
        }
    )
    return row


def main() -> int:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    db_rows, db_fields = read_csv(DATABASE_CSV)
    existing_codes = {row["hunt_code"].strip() for row in db_rows}
    source_rows, _ = read_csv(SOURCE_AUDIT_CSV)
    source_by_code = {row["hunt_code"].strip(): row for row in source_rows}

    target_codes = sorted(CODE_METADATA)
    missing_source_codes = [code for code in target_codes if code not in source_by_code]
    if missing_source_codes:
        raise RuntimeError(f"Source audit missing target codes: {missing_source_codes}")

    inserted_rows: list[dict[str, Any]] = []
    skipped_existing: list[str] = []
    for code in target_codes:
        if code in existing_codes:
            skipped_existing.append(code)
            continue
        source = source_by_code[code]
        if source.get("permits_2025_comparison_status") != "SOURCE_CODE_NOT_IN_DATABASE":
            raise RuntimeError(f"{code} is no longer source-only in the current audit")
        db_row = make_database_row(source, db_fields)
        db_rows.append(db_row)
        inserted_rows.append(
            {
                "hunt_code": code,
                "boundary_id": db_row["boundary_id"],
                "hunt_name": db_row["hunt_name"],
                "sex_type": db_row["sex_type"],
                "species": db_row["species"],
                "weapon": db_row["weapon"],
                "hunt_type": db_row["hunt_type"],
                "source_hunt_name": source["hunt_name"],
                "source_file": source["source_file"],
                "source_sha256": source["source_sha256"],
                "source_page": source["source_page"],
                "source_resident_permits": source["resident_total_permits"],
                "source_nonresident_permits": source["nonresident_total_permits"],
                "source_total_permits": source["total_public_draw_permits"],
                "permits_2025_source": SOURCE_LABEL,
                "notes": db_row["NOTES"],
            }
        )

    write_csv(DATABASE_CSV, db_rows, db_fields)

    promotion_fields = [
        "hunt_code",
        "boundary_id",
        "hunt_name",
        "sex_type",
        "species",
        "weapon",
        "hunt_type",
        "source_hunt_name",
        "source_file",
        "source_sha256",
        "source_page",
        "source_resident_permits",
        "source_nonresident_permits",
        "source_total_permits",
        "permits_2025_source",
        "notes",
    ]
    write_csv(PROMOTION_CSV, inserted_rows, promotion_fields)

    summary = {
        "artifact": "source_only_2024_draw_pdf_values_promoted_to_DATABASE_2025",
        "generated_at_utc": generated_at,
        "database_csv": DATABASE_CSV.relative_to(ROOT).as_posix(),
        "source_audit_csv": SOURCE_AUDIT_CSV.relative_to(ROOT).as_posix(),
        "source_label": SOURCE_LABEL,
        "guardrail": "Promotes only PDF-derived 2025 historical draw rows. All 2026 permit/allotment fields remain blank.",
        "target_code_count": len(target_codes),
        "target_codes": target_codes,
        "inserted_row_count": len(inserted_rows),
        "inserted_codes": [row["hunt_code"] for row in inserted_rows],
        "skipped_existing_count": len(skipped_existing),
        "skipped_existing_codes": skipped_existing,
        "outputs": {
            "promotion_csv": PROMOTION_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Source-Only 2024 Draw PDF Values Promoted To DATABASE 2025",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Inserted historical 2025 rows: `{len(inserted_rows)}`",
        "- All inserted rows are historical 2025 draw-result rows only.",
        "- No 2026 permit/allotment values were populated.",
        "",
        "| Hunt code | Boundary ID | Hunt name | Species | Weapon | Res | Nonres | Total | Source page |",
        "|---|---:|---|---|---|---:|---:|---:|---:|",
    ]
    for row in inserted_rows:
        lines.append(
            "| {hunt_code} | {boundary_id} | {hunt_name} | {species} | {weapon} | "
            "{source_resident_permits} | {source_nonresident_permits} | {source_total_permits} | {source_page} |".format(
                **row
            )
        )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
