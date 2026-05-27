from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data_truth/comparison_outputs/validation"
AUDIT_CSV = OUT_DIR / "repair_2025_historical_source_labels.csv"
SUMMARY_JSON = OUT_DIR / "repair_2025_historical_source_labels_summary.json"
REPORT_MD = ROOT / "processed_data/repair_2025_historical_source_labels.md"

REPLACEMENTS = {
    "canonical_2026_source_of_truth_draw_results": "2025_DRAW_RESULTS_TABLES",
    "2025_OIL_DRAW_RESULTS_PDF_MODEL_TARGET_2026": "2025_OIL_DRAW_RESULTS_PDF_HUNT_YEAR_2025",
    "2025 O.I.L. Draw Results PDF Model Target 2026": "2025 O.I.L. Draw Results PDF Hunt Year 2025",
}

SKIP_DIR_PARTS = {".git", "node_modules", "__pycache__", "processed_data/backups"}
TARGET_SUFFIXES = {".csv", ".json", ".md", ".py"}


def should_scan(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "scripts/repair-2025-historical-source-labels.py":
        return False
    if any(part in rel for part in SKIP_DIR_PARTS):
        return False
    if path.suffix.lower() not in TARGET_SUFFIXES:
        return False
    return True


def repair_file(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    original = text
    rows: list[dict[str, str]] = []
    rel = path.relative_to(ROOT).as_posix()
    for old, new in REPLACEMENTS.items():
        count = text.count(old)
        if not count:
            continue
        text = text.replace(old, new)
        rows.append({"file": rel, "old_value": old, "new_value": new, "replacement_count": str(count)})
    if text != original:
        path.write_text(text, encoding="utf-8")
    return rows


def validate_no_bad_2025_source_labels() -> list[dict[str, str]]:
    bad_rows: list[dict[str, str]] = []
    database = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
    import csv

    with database.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            for field in ("permits_2025_source", "permits_2025_draw_source", "draw_2025_type"):
                value = row.get(field) or ""
                if any(bad in value for bad in REPLACEMENTS):
                    bad_rows.append(
                        {
                            "file": database.relative_to(ROOT).as_posix(),
                            "hunt_code": row.get("hunt_code", ""),
                            "field": field,
                            "remaining_bad_value": value,
                        }
                    )
    return bad_rows


def write_csv(rows: list[dict[str, str]]) -> None:
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "old_value", "new_value", "replacement_count"]
    with AUDIT_CSV.open("w", newline="", encoding="utf-8") as handle:
        import csv

        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    changed_rows: list[dict[str, str]] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and should_scan(path):
            changed_rows.extend(repair_file(path))

    remaining_bad_rows = validate_no_bad_2025_source_labels()
    write_csv(changed_rows)

    counts_by_old = Counter()
    for row in changed_rows:
        counts_by_old[row["old_value"]] += int(row["replacement_count"])

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    summary = {
        "artifact": "repair_2025_historical_source_labels",
        "generated_at_utc": generated_at,
        "guardrail": (
            "Only lineage/type labels were repaired. Numeric 2025 permit values, numeric 2026 DWR live values, "
            "and 2026 allotment values were not recalculated or overwritten."
        ),
        "files_changed": len({row["file"] for row in changed_rows}),
        "replacement_count": sum(int(row["replacement_count"]) for row in changed_rows),
        "replacement_counts_by_old_value": dict(sorted(counts_by_old.items())),
        "remaining_bad_database_2025_label_count": len(remaining_bad_rows),
        "remaining_bad_database_2025_labels": remaining_bad_rows,
        "outputs": {
            "audit_csv": AUDIT_CSV.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_JSON.relative_to(ROOT).as_posix(),
            "report_md": REPORT_MD.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# 2025 Historical Source Label Repair",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Files changed: `{summary['files_changed']}`",
        f"- Replacement count: `{summary['replacement_count']}`",
        f"- Remaining bad 2025 DATABASE labels: `{summary['remaining_bad_database_2025_label_count']}`",
        "",
        "Only lineage/type labels were repaired. No permit numbers were recalculated or overwritten.",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if remaining_bad_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
