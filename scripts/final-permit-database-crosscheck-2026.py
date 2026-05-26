"""Final all-species permit-number crosscheck for canonical DATABASE.csv.

This audit is read-only. It compares current 2026 permit totals, 2026
allotment totals, 2025 historical permit totals, and live DWR comparison
statuses across the full hunt-code universe.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
LIVE_COMPARISON = ROOT / "data_truth/crosswalk_truth/validation/live_dwr_permit_numbers_comprehensive_vs_DATABASE_2026.csv"
DETAIL_OUT = ROOT / "data_truth/comparison_outputs/validation/final_permit_database_crosscheck_2026.csv"
SPECIES_OUT = ROOT / "data_truth/comparison_outputs/validation/final_permit_database_crosscheck_2026_by_species.csv"
PREFIX_OUT = ROOT / "data_truth/comparison_outputs/validation/final_permit_database_crosscheck_2026_by_prefix.csv"
SUMMARY_OUT = ROOT / "data_truth/comparison_outputs/validation/final_permit_database_crosscheck_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/final_permit_database_crosscheck_2026.md"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("\ufeff", "")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def number(value: str) -> int | None:
    text = clean(value).replace(",", "")
    if text == "":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def prefix(code: str) -> str:
    return clean(code)[:2]


def add_metric(bucket: dict[str, object], row: dict[str, object]) -> None:
    bucket["hunt_code_count"] = int(bucket.get("hunt_code_count", 0)) + 1
    for field in (
        "permits_2026_total",
        "permit_allotment_2026_total",
        "permits_2025_total",
        "permits_2025_draw_total",
    ):
        value = row.get(field)
        if isinstance(value, int):
            bucket[f"{field}_row_count"] = int(bucket.get(f"{field}_row_count", 0)) + 1
            bucket[f"{field}_sum"] = int(bucket.get(f"{field}_sum", 0)) + value
    if row.get("live_comparison_status"):
        status_key = f"live_status_{row['live_comparison_status']}"
        bucket[status_key] = int(bucket.get(status_key, 0)) + 1


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    database_rows = read_csv(DATABASE)
    live_rows = {row["hunt_code"]: row for row in read_csv(LIVE_COMPARISON)}

    code_counts = Counter(row["hunt_code"] for row in database_rows)
    duplicate_codes = sorted(code for code, count in code_counts.items() if count > 1)
    blank_boundary_codes = sorted(row["hunt_code"] for row in database_rows if not row.get("boundary_id"))

    detail_rows: list[dict[str, object]] = []
    species_buckets: dict[str, dict[str, object]] = defaultdict(dict)
    prefix_buckets: dict[str, dict[str, object]] = defaultdict(dict)
    hunt_type_counts = Counter()
    species_counts = Counter()
    field_populated_counts = Counter()
    total_status_counts = Counter()
    live_status_counts = Counter()

    for row in database_rows:
        code = row["hunt_code"]
        live = live_rows.get(code, {})
        values = {
            "permits_2026_total": number(row.get("permits_2026_total", "")),
            "permit_allotment_2026_total": number(row.get("permit_allotment_2026_total", "")),
            "permits_2025_total": number(row.get("permits_2025_total", "")),
            "permits_2025_draw_total": number(row.get("permits_2025_draw_total", "")),
        }
        for field, value in values.items():
            if value is not None:
                field_populated_counts[field] += 1

        permits_2026_total = values["permits_2026_total"]
        allotment_2026_total = values["permit_allotment_2026_total"]
        permits_2025_total = values["permits_2025_total"]

        if permits_2026_total is not None and allotment_2026_total is not None:
            if permits_2026_total == allotment_2026_total:
                total_status = "2026_PERMIT_TOTAL_MATCHES_ALLOTMENT_TOTAL"
            else:
                total_status = "2026_PERMIT_TOTAL_DIFFERS_FROM_ALLOTMENT_TOTAL"
        elif permits_2026_total is not None:
            total_status = "2026_PERMIT_TOTAL_ONLY"
        elif allotment_2026_total is not None:
            total_status = "2026_ALLOTMENT_TOTAL_ONLY"
        else:
            total_status = "NO_2026_TOTAL"

        if permits_2026_total is not None and permits_2025_total is not None:
            if permits_2026_total > permits_2025_total:
                year_delta_status = "2026_GT_2025"
            elif permits_2026_total < permits_2025_total:
                year_delta_status = "2026_LT_2025"
            else:
                year_delta_status = "2026_EQ_2025"
            year_delta = permits_2026_total - permits_2025_total
        elif permits_2026_total is not None:
            year_delta_status = "ONLY_2026_TOTAL"
            year_delta = ""
        elif permits_2025_total is not None:
            year_delta_status = "ONLY_2025_TOTAL"
            year_delta = ""
        else:
            year_delta_status = "NO_2025_OR_2026_TOTAL"
            year_delta = ""

        live_status = live.get("comparison_status", "")
        if live_status:
            live_status_counts[live_status] += 1
        total_status_counts[total_status] += 1
        species_counts[row.get("species", "")] += 1
        hunt_type_counts[row.get("hunt_type", "")] += 1

        detail = {
            "snapshot_utc": timestamp,
            "hunt_code": code,
            "prefix": prefix(code),
            "boundary_id": row.get("boundary_id", ""),
            "hunt_name": row.get("hunt_name", ""),
            "species": row.get("species", ""),
            "sex_type": row.get("sex_type", ""),
            "weapon": row.get("weapon", ""),
            "hunt_type": row.get("hunt_type", ""),
            "season": row.get("season", ""),
            "permits_2026_total": permits_2026_total if permits_2026_total is not None else "",
            "permit_allotment_2026_total": allotment_2026_total if allotment_2026_total is not None else "",
            "permits_2025_total": permits_2025_total if permits_2025_total is not None else "",
            "permits_2025_draw_total": values["permits_2025_draw_total"] if values["permits_2025_draw_total"] is not None else "",
            "total_status": total_status,
            "year_delta_status": year_delta_status,
            "year_delta_2026_minus_2025": year_delta,
            "live_comparison_status": live_status,
            "live_shape_status": live.get("live_shape_status", ""),
            "permits_2026_source": row.get("permits_2026_source", ""),
            "permit_allotment_2026_source": row.get("permit_allotment_2026_source", ""),
            "permits_2025_source": row.get("permits_2025_source", ""),
        }
        detail_rows.append(detail)
        add_metric(species_buckets[row.get("species", "")], detail)
        add_metric(prefix_buckets[prefix(code)], detail)

    species_rows = [dict({"species": species}, **bucket) for species, bucket in sorted(species_buckets.items())]
    prefix_rows = [dict({"prefix": code_prefix}, **bucket) for code_prefix, bucket in sorted(prefix_buckets.items())]

    detail_fields = [
        "snapshot_utc",
        "hunt_code",
        "prefix",
        "boundary_id",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "season",
        "permits_2026_total",
        "permit_allotment_2026_total",
        "permits_2025_total",
        "permits_2025_draw_total",
        "total_status",
        "year_delta_status",
        "year_delta_2026_minus_2025",
        "live_comparison_status",
        "live_shape_status",
        "permits_2026_source",
        "permit_allotment_2026_source",
        "permits_2025_source",
    ]
    aggregate_fields = [
        "hunt_code_count",
        "permits_2026_total_row_count",
        "permits_2026_total_sum",
        "permit_allotment_2026_total_row_count",
        "permit_allotment_2026_total_sum",
        "permits_2025_total_row_count",
        "permits_2025_total_sum",
        "permits_2025_draw_total_row_count",
        "permits_2025_draw_total_sum",
        "live_status_MATCH",
        "live_status_TOTAL_MATCH_SPLIT_DIFFERS",
        "live_status_BOTH_BLANK",
        "live_status_LIVE_NO_QUOTA_DATABASE_PRESERVED",
        "live_status_DATABASE_ONLY",
    ]

    write_csv(DETAIL_OUT, detail_rows, detail_fields)
    write_csv(SPECIES_OUT, species_rows, ["species", *aggregate_fields])
    write_csv(PREFIX_OUT, prefix_rows, ["prefix", *aggregate_fields])

    total_mismatch_codes = [
        row["hunt_code"]
        for row in detail_rows
        if row["total_status"] == "2026_PERMIT_TOTAL_DIFFERS_FROM_ALLOTMENT_TOTAL"
    ]
    summary = {
        "artifact": "final_permit_database_crosscheck_2026",
        "snapshot_utc": timestamp,
        "database_path": DATABASE.relative_to(ROOT).as_posix(),
        "database_row_count": len(database_rows),
        "unique_hunt_code_count": len(code_counts),
        "duplicate_hunt_code_count": len(duplicate_codes),
        "duplicate_hunt_codes": duplicate_codes[:200],
        "blank_boundary_id_count": len(blank_boundary_codes),
        "blank_boundary_id_codes": blank_boundary_codes[:200],
        "species_counts": dict(sorted(species_counts.items())),
        "prefix_counts": dict(sorted(Counter(prefix(row["hunt_code"]) for row in database_rows).items())),
        "hunt_type_counts": dict(sorted(hunt_type_counts.items())),
        "field_populated_counts": dict(sorted(field_populated_counts.items())),
        "total_status_counts": dict(sorted(total_status_counts.items())),
        "year_delta_status_counts": dict(sorted(Counter(row["year_delta_status"] for row in detail_rows).items())),
        "live_comparison_status_counts": dict(sorted(live_status_counts.items())),
        "permit_vs_allotment_total_mismatch_count": len(total_mismatch_codes),
        "permit_vs_allotment_total_mismatch_codes": total_mismatch_codes[:200],
        "outputs": {
            "detail_csv": DETAIL_OUT.relative_to(ROOT).as_posix(),
            "species_csv": SPECIES_OUT.relative_to(ROOT).as_posix(),
            "prefix_csv": PREFIX_OUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_OUT.relative_to(ROOT).as_posix(),
            "report_md": REPORT_OUT.relative_to(ROOT).as_posix(),
        },
        "guardrail": "Read-only audit. No database, website, prediction, or materializer files are modified.",
    }
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Final Permit Database Crosscheck 2026",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- DATABASE rows: `{len(database_rows)}`",
        f"- Unique hunt codes: `{len(code_counts)}`",
        f"- Duplicate hunt codes: `{len(duplicate_codes)}`",
        f"- Blank boundary IDs: `{len(blank_boundary_codes)}`",
        f"- 2026 permit vs allotment total mismatches: `{len(total_mismatch_codes)}`",
        "",
        "## Populated Permit Fields",
        "",
    ]
    for field, count in sorted(field_populated_counts.items()):
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(["", "## Live DWR Comparison Status Counts", ""])
    for status, count in sorted(live_status_counts.items()):
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Total Status Counts", ""])
    for status, count in sorted(total_status_counts.items()):
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Species Hunt-Code Counts", ""])
    for species, count in sorted(species_counts.items()):
        lines.append(f"- `{species}`: `{count}`")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if duplicate_codes or blank_boundary_codes or total_mismatch_codes else 0


if __name__ == "__main__":
    raise SystemExit(main())
