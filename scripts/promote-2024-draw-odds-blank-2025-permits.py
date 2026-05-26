"""Fill blank DATABASE permits_2025 fields from reviewed 2024 draw-odds audit.

This script only fills rows where the broad `permits_2025_*` fields are blank
and the 2024 draw-odds audit marked the row as a safe blank candidate. It never
overwrites populated historical 2025 permit values.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
AUDIT = (
    ROOT / "data_truth/draw_results_truth/validation/draw_odds_2024_model_target_2025_vs_DATABASE_2025_permits.csv"
)
OUT_CSV = ROOT / "data_truth/draw_results_truth/validation/draw_odds_2024_blank_2025_permits_promoted.csv"
OUT_JSON = ROOT / "data_truth/draw_results_truth/validation/draw_odds_2024_blank_2025_permits_promoted_summary.json"
OUT_MD = ROOT / "processed_data/draw_odds_2024_blank_2025_permits_promoted.md"

SOURCE_LABEL = "2024_DRAW_ODDS_MODEL_TARGET_2025_BLANK_FILL"


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    return "" if text in {"", "-", "nan", "None"} else text


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [{key: clean(value) for key, value in row.items()} for row in reader], list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> int:
    db_rows, db_fields = read_csv(DATABASE)
    audit_rows, _ = read_csv(AUDIT)
    candidates = {
        row["hunt_code"]: row
        for row in audit_rows
        if row.get("promotion_recommendation") == "SAFE_BLANK_CANDIDATE_REVIEW_REQUIRED"
    }

    promoted_rows: list[dict[str, object]] = []
    action_counts: Counter[str] = Counter()
    for row in db_rows:
        code = row.get("hunt_code", "")
        source = candidates.get(code)
        if not source:
            continue
        before = {
            "old_permits_2025_res": row.get("permits_2025_res", ""),
            "old_permits_2025_nr": row.get("permits_2025_nr", ""),
            "old_permits_2025_total": row.get("permits_2025_total", ""),
            "old_permits_2025_source": row.get("permits_2025_source", ""),
        }
        if any(before[field] for field in ["old_permits_2025_res", "old_permits_2025_nr", "old_permits_2025_total"]):
            action = "SKIPPED_POPULATED_DATABASE_VALUE"
        else:
            row["permits_2025_res"] = source.get("resident_total_permits", "")
            row["permits_2025_nr"] = source.get("nonresident_total_permits", "")
            row["permits_2025_total"] = source.get("total_public_draw_permits", "")
            row["permits_2025_source"] = SOURCE_LABEL
            action = "PROMOTED_BLANK_2025_PERMIT_FIELDS"
        action_counts[action] += 1
        promoted_rows.append(
            {
                "hunt_code": code,
                "hunt_name": row.get("hunt_name", ""),
                "action": action,
                **before,
                "new_permits_2025_res": row.get("permits_2025_res", ""),
                "new_permits_2025_nr": row.get("permits_2025_nr", ""),
                "new_permits_2025_total": row.get("permits_2025_total", ""),
                "new_permits_2025_source": row.get("permits_2025_source", ""),
                "source_file": source.get("source_file", ""),
                "source_page": source.get("source_page", ""),
            }
        )

    write_csv(DATABASE, db_rows, db_fields)
    audit_fields = [
        "hunt_code",
        "hunt_name",
        "action",
        "old_permits_2025_res",
        "old_permits_2025_nr",
        "old_permits_2025_total",
        "old_permits_2025_source",
        "new_permits_2025_res",
        "new_permits_2025_nr",
        "new_permits_2025_total",
        "new_permits_2025_source",
        "source_file",
        "source_page",
    ]
    write_csv(OUT_CSV, promoted_rows, audit_fields)

    summary = {
        "artifact": "draw_odds_2024_blank_2025_permits_promoted",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "candidate_count": len(candidates),
        "promoted_row_count": action_counts.get("PROMOTED_BLANK_2025_PERMIT_FIELDS", 0),
        "skipped_populated_count": action_counts.get("SKIPPED_POPULATED_DATABASE_VALUE", 0),
        "action_counts": dict(sorted(action_counts.items())),
        "promoted_codes": [row["hunt_code"] for row in promoted_rows if row["action"] == "PROMOTED_BLANK_2025_PERMIT_FIELDS"],
        "source_label": SOURCE_LABEL,
        "guardrail": "Only blank broad permits_2025 fields are filled. Populated historical 2025 values are never overwritten.",
        "outputs": {
            "audit_csv": OUT_CSV.relative_to(ROOT).as_posix(),
            "summary_json": OUT_JSON.relative_to(ROOT).as_posix(),
            "report_md": OUT_MD.relative_to(ROOT).as_posix(),
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# 2024 Draw Odds Blank 2025 Permit Promotion",
        "",
        f"- Candidate rows: `{summary['candidate_count']}`",
        f"- Promoted rows: `{summary['promoted_row_count']}`",
        f"- Promoted codes: `{', '.join(summary['promoted_codes'])}`",
        "",
        str(summary["guardrail"]),
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
