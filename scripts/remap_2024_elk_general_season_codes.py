from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


TARGET = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/elk_general_season_2024_extract/ELK_GENERAL_SEASON.csv"
)
REPORT = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/elk_general_season_2024_extract/ELK_GENERAL_SEASON_2024_REMAP_REPORT.txt"
)


def map_code_2024(row: dict[str, str]) -> tuple[str, str]:
    title = (row.get("table_title") or "").lower()
    hunt_type = (row.get("hunt_type") or "").lower()
    hunt_class = (row.get("hunt_class") or "").lower()
    name = (row.get("hunt_name") or "").lower().strip()
    page = (row.get("adobe_page") or "").strip()

    if "uinta basin" in name and "any bull elk" in name:
        return "EB1012", "2024_alias_uinta_basin_any_bull"
    if "spike-bull" in title and "muzzleloader" in title:
        return "EB1004", "2024_table_title_muzzleloader_spike"
    if "any-bull" in title and "muzzleloader" in title:
        return "EB1002", "2024_table_title_muzzleloader_any_bull"
    if "any-bull" in title and "early" in title and "any legal weapon" in title:
        return "EB1001", "2024_table_title_early_any_legal_any_bull"
    if "any-bull" in title and "late" in title and "any legal weapon" in title:
        return "EB1010", "2024_table_title_late_any_legal_any_bull"
    if "spike-bull" in title and "any legal weapon" in title:
        return "EB1003", "2024_table_title_any_legal_spike"

    if "spike" in hunt_class and "general season" in hunt_type and page == "1":
        return "EB1003", "2024_fallback_page1_spike"
    if "any bull" in hunt_class and "early" in hunt_type:
        return "EB1001", "2024_fallback_early_any_bull"
    if "any bull" in hunt_class and "late" in hunt_type:
        return "EB1010", "2024_fallback_late_any_bull"
    if "spike" in hunt_class and page == "4":
        return "EB1004", "2024_fallback_page4_spike_muzzle"
    if "any bull" in hunt_class and page == "5":
        return "EB1002", "2024_fallback_page5_any_bull_muzzle"

    return "", "unmapped_2024_rule"


def main() -> None:
    with TARGET.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise RuntimeError(f"No rows in {TARGET}")

    changed = 0
    for row in rows:
        old = (row.get("hunt_code") or "").strip()
        code, basis = map_code_2024(row)
        if code != old:
            changed += 1
        row["hunt_code"] = code
        row["mapping_status"] = "mapped_to_2024_codes" if code else "unmapped_2024"
        row["match_basis"] = basis
        row["hunt_codes_2026_elk"] = ""
        row["hunt_code_count_2026"] = ""
        row["matched_hunt_names_2026"] = ""

    fields = list(rows[0].keys())
    with TARGET.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter((row.get("hunt_code") or "").strip() for row in rows)
    blanks = sum(1 for row in rows if not (row.get("hunt_code") or "").strip())

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", encoding="utf-8") as f:
        f.write("ELK_GENERAL_SEASON 2024 remap report\n")
        f.write(f"rows={len(rows)}\n")
        f.write(f"changed={changed}\n")
        f.write(f"blank_hunt_code_rows={blanks}\n")
        f.write("code_counts:\n")
        for code, n in sorted(counts.items()):
            f.write(f"  {code or '<blank>'}: {n}\n")

    print(f"Updated {TARGET}")
    print(f"Report {REPORT}")
    print(f"rows={len(rows)} changed={changed} blanks={blanks}")


if __name__ == "__main__":
    main()
