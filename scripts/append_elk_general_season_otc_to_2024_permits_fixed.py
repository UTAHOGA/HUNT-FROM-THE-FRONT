from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


PERMITS_FIXED = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/comprehensive_2024/2024_DRAW_RESULTS_COMPREHENSIVE_PERMITS_FIXED.csv"
)
ELK_GENERAL = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/elk_general_season_2024_extract/ELK_GENERAL_SEASON.csv"
)
OUT = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/comprehensive_2024/2024_DRAW_RESULTS_COMPREHENSIVE_PERMITS_FIXED_WITH_OTC.csv"
)
REPORT = Path(
    r"pipeline/RAW/hunt_unit_database/2025/formatted_tables/draw_odds_results/comprehensive_2024/2024_DRAW_RESULTS_COMPREHENSIVE_PERMITS_FIXED_plus_OTC_report.json"
)

OTC_FAMILY = "elk_general_season_otc_harvest_2024"
OTC_PARSE_STYLE = "otc_harvest_linked_no_draw_cap"


def main() -> None:
    with PERMITS_FIXED.open("r", encoding="utf-8-sig", newline="") as f:
        base_rows = list(csv.DictReader(f))

    with ELK_GENERAL.open("r", encoding="utf-8-sig", newline="") as f:
        elk_rows = list(csv.DictReader(f))

    if not base_rows:
        raise RuntimeError(f"No rows in {PERMITS_FIXED}")

    fields = list(base_rows[0].keys())

    # Remove existing OTC appended rows so reruns are clean.
    kept_rows = [r for r in base_rows if (r.get("dataset_family") or "").strip() != OTC_FAMILY]
    removed_existing_otc = len(base_rows) - len(kept_rows)

    append_rows: list[dict[str, str]] = []
    for src in elk_rows:
        hunt_code = (src.get("hunt_code") or "").strip()
        if not hunt_code:
            continue
        row = {k: "" for k in fields}
        row["source_file"] = "2024 ELK GENERAL SEASON.pdf"
        row["source_page"] = (src.get("adobe_page") or "").strip()
        row["hunt_code"] = hunt_code
        row["hunt_name"] = (src.get("hunt_name") or "").strip()
        row["species_or_category"] = "Elk"

        # OTC rows are not draw-capped permit quotas.
        row["res_total_permits"] = ""
        row["nr_total_permits"] = ""
        row["total_permits"] = ""
        row["totals_numbers"] = ""
        row["raw_hunt_line"] = ""
        row["raw_totals_line"] = ""

        row["parse_style"] = OTC_PARSE_STYLE
        row["dataset_family"] = OTC_FAMILY
        row["source_dataset"] = "ELK_GENERAL_SEASON_2024_EXTRACT"
        append_rows.append(row)

    out_rows = kept_rows + append_rows
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    report_obj = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_file": str(PERMITS_FIXED),
        "elk_general_source": str(ELK_GENERAL),
        "output_file": str(OUT),
        "otc_dataset_family": OTC_FAMILY,
        "otc_parse_style": OTC_PARSE_STYLE,
        "base_rows_before": len(base_rows),
        "existing_otc_rows_removed": removed_existing_otc,
        "otc_rows_appended": len(append_rows),
        "rows_after": len(out_rows),
        "note": "OTC elk rows carry hunt_code linkage only; draw permit columns intentionally blank.",
    }
    REPORT.write_text(json.dumps(report_obj, indent=2), encoding="utf-8")

    print(f"Wrote {OUT}")
    print(f"Wrote {REPORT}")
    print(
        f"base_before={len(base_rows)} removed_existing_otc={removed_existing_otc} "
        f"appended={len(append_rows)} rows_after={len(out_rows)}"
    )


if __name__ == "__main__":
    main()
