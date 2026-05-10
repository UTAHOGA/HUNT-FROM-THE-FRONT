from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(r"pipeline/RAW/hunt_unit_database/2025/formatted_tables")
OUT_DIR = ROOT / "comprehensive_harvest_2024"
OUT_CSV = OUT_DIR / "2024_HARVEST_RESULTS_COMPREHENSIVE.csv"
OUT_XLSX = OUT_DIR / "2024_HARVEST_RESULTS_COMPREHENSIVE.xlsx"
REPORT_JSON = OUT_DIR / "2024_HARVEST_RESULTS_COMPREHENSIVE_report.json"


def is_harvest_file(path: Path) -> bool:
    lower = str(path).lower()
    if "draw_odds_results" in lower:
        return False
    if "_archive_nonfinal_" in lower:
        return False
    if "comprehensive_harvest_2024" in lower:
        return False
    return True


def main() -> None:
    files = sorted([p for p in ROOT.rglob("*.csv") if is_harvest_file(p)])
    if not files:
        raise RuntimeError("No harvest CSV files found to aggregate.")

    rows: list[dict[str, str]] = []
    header_union: list[str] = []
    header_set = set()
    per_file_counts: list[dict[str, object]] = []

    for file_path in files:
        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            for c in cols:
                if c not in header_set:
                    header_set.add(c)
                    header_union.append(c)
            file_row_count = 0
            for i, row in enumerate(reader, start=2):
                file_row_count += 1
                out_row = {k: (row.get(k) or "") for k in cols}
                out_row["source_file"] = str(file_path).replace("\\", "/")
                out_row["source_row"] = str(i)
                out_row["source_dataset_group"] = file_path.parent.name
                rows.append(out_row)
            per_file_counts.append(
                {
                    "file": str(file_path).replace("\\", "/"),
                    "rows": file_row_count,
                    "columns": cols,
                }
            )

    fixed_cols = ["source_file", "source_row", "source_dataset_group"]
    ordered_cols = fixed_cols + [c for c in header_union if c not in fixed_cols]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ordered_cols)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in ordered_cols})

    # Optional XLSX output
    try:
        import pandas as pd  # type: ignore

        pd.DataFrame(rows).reindex(columns=ordered_cols).to_excel(OUT_XLSX, index=False)
        xlsx_written = True
    except Exception:
        xlsx_written = False

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT).replace("\\", "/"),
        "files_included": len(files),
        "rows_total": len(rows),
        "columns_total": len(ordered_cols),
        "output_csv": str(OUT_CSV).replace("\\", "/"),
        "output_xlsx": str(OUT_XLSX).replace("\\", "/") if xlsx_written else "",
        "xlsx_written": xlsx_written,
        "filters": {
            "excluded_paths_containing": [
                "draw_odds_results",
                "_archive_nonfinal_",
                "comprehensive_harvest_2024",
            ]
        },
        "files": per_file_counts,
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {OUT_CSV}")
    if xlsx_written:
        print(f"Wrote {OUT_XLSX}")
    print(f"Wrote {REPORT_JSON}")
    print(f"files={len(files)} rows={len(rows)} cols={len(ordered_cols)}")


if __name__ == "__main__":
    main()
