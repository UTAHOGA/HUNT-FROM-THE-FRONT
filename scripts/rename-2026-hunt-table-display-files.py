from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(r"C:\Users\tyler\Desktop\GitHub\HUNT-BUILDER")
XLSX_DIR = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026" / "XLXS"
PDF_DIR = ROOT / "processed_data" / "hard_data_exports" / "hunt_tables" / "2026" / "PDF'S"
AUDIT_CSV = ROOT / "processed_data" / "audits" / "hunt_tables_2026_display_filename_audit.csv"


# Keep the display names visitor-facing: YEAR SPECIES SEX/TYPE HUNT CLASS.
# Abbreviations omit trailing periods to avoid names like "L.E..pdf".
DISPLAY_NAMES = {
    "2026_ANTLERLESS_DEER_formatted": "2026 DEER ANTLERLESS DRAW",
    "2026 DEER ANTLERLESS": "2026 DEER ANTLERLESS DRAW",
    "2026_DEER_ANTLERLESS": "2026 DEER ANTLERLESS DRAW SUMMARY",
    "2026_antlerless_elk_general_season": "2026 ELK ANTLERLESS GENERAL SEASON",
    "2026 ELK ANTLERLESS GENERAL SEASON": "2026 ELK ANTLERLESS GENERAL SEASON",
    "2026_BISON_COW": "2026 BISON COW O.I.L",
    "2026 BISON COW": "2026 BISON COW O.I.L",
    "2026_BISON_HUNTER_CHOICE": "2026 BISON HUNTER CHOICE O.I.L",
    "2026 BISON HUNTER CHOICE": "2026 BISON HUNTER CHOICE O.I.L",
    "2026_BLACK_BEAR": "2026 BLACK BEAR DRAW",
    "2026_cougar": "2026 COUGAR DRAW",
    "2026_deer_antlerless_cwmu": "2026 DEER ANTLERLESS CWMU",
    "2026_DEER_ARCHERY_EXTENDED": "2026 DEER BUCK EXTENDED ARCHERY",
    "2026_DEER_BUCK": "2026 DEER BUCK DRAW",
    "2026_deer_buck_cactus": "2026 DEER BUCK CACTUS BUCK",
    "2026_deer_buck_conservation": "2026 DEER BUCK CONSERVATION PERMIT",
    "2026_deer_buck_cwmu": "2026 DEER BUCK CWMU",
    "2026_deer_buck_limited_entry": "2026 DEER BUCK L.E",
    "2026_deer_buck_limited_entry_management_buck": "2026 DEER BUCK L.E MANAGEMENT BUCK",
    "2026_deer_buck_limited_entry_private_lands_only": "2026 DEER BUCK L.E PRIVATE LANDS ONLY",
    "2026_deer_buck_premium_limited_entry": "2026 DEER BUCK P.L.E",
    "2026_deer_buck_statewide": "2026 DEER BUCK STATEWIDE",
    "2026_deer_general_season": "2026 DEER BUCK GENERAL SEASON",
    "2026_deer_general_season_private_lands": "2026 DEER BUCK GENERAL SEASON PRIVATE LANDS",
    "2026_deer_hunter_choice": "2026 DEER HUNTER CHOICE",
    "2026_desert_bighorn_ram": "2026 DESERT BIGHORN SHEEP RAM O.I.L EXPANDED",
    "2026_ELK_ANTLERLESS": "2026 ELK ANTLERLESS DRAW",
    "2026_elk_antlerless_conservation": "2026 ELK ANTLERLESS CONSERVATION PERMIT",
    "2026_elk_antlerless_CWMU": "2026 ELK ANTLERLESS CWMU",
    "2026_elk_antlerless_privatelandsonly": "2026 ELK ANTLERLESS PRIVATE LANDS ONLY",
    "2026_elk_archery_extended": "2026 ELK BULL EXTENDED ARCHERY",
    "2026_elk_bull_all 2": "2026 ELK BULL ALL HUNTS EXPANDED",
    "2026_ELK_BULL_ALL": "2026 ELK BULL ALL HUNTS SUMMARY",
    "2026_elk_bull_conservation_permit": "2026 ELK BULL CONSERVATION PERMIT",
    "2026_elk_bull_cwmu": "2026 ELK BULL CWMU",
    "2026_elk_bull_general_anybull": "2026 ELK BULL GENERAL ANY BULL",
    "2026_elk_bull_limited_entry": "2026 ELK BULL L.E",
    "2026_elk_general_anybull_youth": "2026 ELK BULL YOUTH GENERAL ANY BULL",
    "2026_elk_general_archery": "2026 ELK BULL GENERAL ARCHERY",
    "2026_elk_general_spikeonly": "2026 ELK BULL GENERAL SPIKE ONLY",
    "2026_elk_limitedentry_maturebull": "2026 ELK BULL L.E MATURE BULL",
    "2026_elk_limitedentry_maturebull_privatelands": "2026 ELK BULL L.E MATURE BULL PRIVATE LANDS",
    "2026_elk_limitedentry_statewide": "2026 ELK BULL STATEWIDE",
    "2026_goat_hunter_choice ": "2026 MOUNTAIN GOAT HUNTER CHOICE O.I.L EXPANDED",
    "2026_GOAT_HUNTER_CHOICE": "2026 MOUNTAIN GOAT HUNTER CHOICE O.I.L SUMMARY",
    "2026_MOOSE_BULL": "2026 MOOSE BULL O.I.L",
    "2026_moose_cow": "2026 MOOSE COW O.I.L",
    "2026_SHEEP_DESERT_RAM": "2026 DESERT BIGHORN SHEEP RAM O.I.L",
    "2026_SHEEP_ROCKY_MOUNTAIN_EWE": "2026 ROCKY MOUNTAIN BIGHORN SHEEP EWE O.I.L",
    "2026_SHEEP_ROCKY_MOUNTAIN_RAM": "2026 ROCKY MOUNTAIN BIGHORN SHEEP RAM O.I.L",
    "2026_TURKEY_BEARDED": "2026 TURKEY BEARDED DRAW",
    "2026_TURKEY_EITHER_SEX": "2026 TURKEY EITHER SEX DRAW",
}


def rename_in_dir(folder: Path, extension: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for src in sorted(folder.glob(f"*{extension}")):
        if src.name.startswith("~$"):
            continue
        target_base = DISPLAY_NAMES.get(src.stem)
        row = {
            "folder": str(folder.relative_to(ROOT)).replace("\\", "/"),
            "old_name": src.name,
            "new_name": "",
            "status": "",
            "error": "",
        }
        if not target_base:
            row["status"] = "UNMAPPED"
            row["error"] = f"No display-name mapping for stem: {src.stem}"
            rows.append(row)
            continue

        dest = src.with_name(f"{target_base}{extension}")
        row["new_name"] = dest.name
        if src.resolve() == dest.resolve():
            row["status"] = "UNCHANGED"
            rows.append(row)
            continue
        if dest.exists():
            row["status"] = "ERROR"
            row["error"] = f"Target already exists: {dest.name}"
            rows.append(row)
            continue
        src.rename(dest)
        row["status"] = "RENAMED"
        rows.append(row)
    return rows


def main() -> None:
    if not XLSX_DIR.exists():
        raise SystemExit(f"Missing XLSX folder: {XLSX_DIR}")
    if not PDF_DIR.exists():
        raise SystemExit(f"Missing PDF folder: {PDF_DIR}")

    rows = rename_in_dir(XLSX_DIR, ".xlsx")
    rows.extend(rename_in_dir(PDF_DIR, ".pdf"))

    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["folder", "old_name", "new_name", "status", "error"])
        writer.writeheader()
        writer.writerows(rows)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    print(f"wrote audit: {AUDIT_CSV}")
    for status in sorted(counts):
        print(f"{status}: {counts[status]}")

    errors = [row for row in rows if row["status"] in {"ERROR", "UNMAPPED"}]
    if errors:
        raise SystemExit(f"Filename cleanup finished with {len(errors)} errors/unmapped files")


if __name__ == "__main__":
    main()
