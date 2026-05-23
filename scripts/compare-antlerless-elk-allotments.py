"""Compare current RAC antlerless elk allotments against DATABASE/runtime values."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_ROOT = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv"
PROCESSED = ROOT / "processed_data"

CURRENT_RAC = CSV_ROOT / "2026_rac_antlerless_elk_permits.csv"
DATABASE = CSV_ROOT / "DATABASE.csv"
REFERENCE = PROCESSED / "hunt_unit_reference_linked.csv"

OUT_CSV = PROCESSED / "antlerless_elk_current_rac_allotment_vs_database_runtime.csv"
OUT_JSON = PROCESSED / "antlerless_elk_current_rac_allotment_vs_database_runtime.json"
OUT_MD = PROCESSED / "antlerless_elk_current_rac_allotment_vs_database_runtime.md"

FIELDS = [
    "hunt_code",
    "hunt_name",
    "weapon",
    "hunt_type",
    "season_dates_2026",
    "permits_2025_res",
    "permits_2025_nr",
    "permits_2025_total",
    "permits_2026_res_allotted",
    "permits_2026_nr_allotted",
    "permits_2026_total_allotted",
    "database_2026_res",
    "database_2026_nr",
    "database_2026_total",
    "runtime_2026_res",
    "runtime_2026_nr",
    "runtime_2026_total",
    "database_delta_res",
    "database_delta_nr",
    "database_delta_total",
    "runtime_delta_res",
    "runtime_delta_nr",
    "runtime_delta_total",
    "database_status",
    "runtime_status",
    "significant_database_difference",
    "significant_runtime_difference",
    "source_document",
    "source_note",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def to_int(value: object) -> int | None:
    text = clean(value).replace(",", "")
    if not text or text in {"-", "–", "—"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def delta(allotted: object, compared: object) -> str:
    left = to_int(allotted)
    right = to_int(compared)
    if left is None or right is None:
        return ""
    return str(right - left)


def database_index() -> dict[str, dict[str, str]]:
    return {clean(row.get("hunt_code")): row for row in read_csv(DATABASE) if clean(row.get("hunt_code"))}


def runtime_index() -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(REFERENCE):
        code = clean(row.get("hunt_code"))
        if code:
            grouped.setdefault(code, []).append(row)
    index: dict[str, dict[str, str]] = {}
    for code, rows in grouped.items():
        resident = next((row for row in rows if clean(row.get("residency")) == "Resident"), {})
        nonresident = next((row for row in rows if clean(row.get("residency")) == "Nonresident"), {})
        index[code] = {
            "res": clean(resident.get("permits_2026_res")) or clean(resident.get("public_permits_2026")),
            "nr": clean(resident.get("permits_2026_nr")) or clean(nonresident.get("public_permits_2026")),
            "total": clean(resident.get("permits_2026_total")) or clean(nonresident.get("permits_2026_total")),
        }
    return index


def status_for(row: dict[str, str], prefix: str) -> str:
    if not row[f"{prefix}_2026_total"]:
        return "MISSING"
    deltas = [row[f"{prefix}_delta_res"], row[f"{prefix}_delta_nr"], row[f"{prefix}_delta_total"]]
    if all(value in {"", "0"} for value in deltas):
        return "MATCH"
    return "DIFFERS"


def significant(row: dict[str, str], prefix: str) -> str:
    total = to_int(row[f"{prefix}_delta_total"])
    return "YES" if total is not None and abs(total) > 5 else "NO"


def build_rows() -> tuple[list[dict[str, str]], dict[str, object]]:
    db = database_index()
    runtime = runtime_index()
    output_rows: list[dict[str, str]] = []

    for source in read_csv(CURRENT_RAC):
        code = clean(source.get("hunt_code"))
        db_row = db.get(code, {})
        runtime_row = runtime.get(code, {})
        row = {
            "hunt_code": code,
            "hunt_name": clean(source.get("hunt_name")),
            "weapon": clean(source.get("weapon")),
            "hunt_type": "General Season",
            "season_dates_2026": clean(source.get("season_dates_2026")),
            "permits_2025_res": clean(source.get("permits_2025_res")),
            "permits_2025_nr": clean(source.get("permits_2025_nr")),
            "permits_2025_total": clean(source.get("permits_2025_total")),
            "permits_2026_res_allotted": clean(source.get("permits_2026_res")),
            "permits_2026_nr_allotted": clean(source.get("permits_2026_nr")),
            "permits_2026_total_allotted": clean(source.get("permits_2026_total")),
            "database_2026_res": clean(db_row.get("permits_2026_res")),
            "database_2026_nr": clean(db_row.get("permits_2026_nr")),
            "database_2026_total": clean(db_row.get("permits_2026_total")),
            "runtime_2026_res": runtime_row.get("res", ""),
            "runtime_2026_nr": runtime_row.get("nr", ""),
            "runtime_2026_total": runtime_row.get("total", ""),
            "source_document": clean(source.get("source_document")),
            "source_note": clean(source.get("source_note")),
        }
        row["database_delta_res"] = delta(row["permits_2026_res_allotted"], row["database_2026_res"])
        row["database_delta_nr"] = delta(row["permits_2026_nr_allotted"], row["database_2026_nr"])
        row["database_delta_total"] = delta(row["permits_2026_total_allotted"], row["database_2026_total"])
        row["runtime_delta_res"] = delta(row["permits_2026_res_allotted"], row["runtime_2026_res"])
        row["runtime_delta_nr"] = delta(row["permits_2026_nr_allotted"], row["runtime_2026_nr"])
        row["runtime_delta_total"] = delta(row["permits_2026_total_allotted"], row["runtime_2026_total"])
        row["database_status"] = status_for(row, "database")
        row["runtime_status"] = status_for(row, "runtime")
        row["significant_database_difference"] = significant(row, "database")
        row["significant_runtime_difference"] = significant(row, "runtime")
        output_rows.append(row)

    database_status_counts = Counter(row["database_status"] for row in output_rows)
    runtime_status_counts = Counter(row["runtime_status"] for row in output_rows)
    database_diffs = [row for row in output_rows if row["database_status"] != "MATCH"]
    runtime_diffs = [row for row in output_rows if row["runtime_status"] != "MATCH"]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_allotment_file": str(CURRENT_RAC.relative_to(ROOT)),
        "database_file": str(DATABASE.relative_to(ROOT)),
        "runtime_file": str(REFERENCE.relative_to(ROOT)),
        "row_count": len(output_rows),
        "unique_hunt_codes": len({row["hunt_code"] for row in output_rows}),
        "database_status_counts": dict(database_status_counts),
        "runtime_status_counts": dict(runtime_status_counts),
        "database_difference_rows": len(database_diffs),
        "runtime_difference_rows": len(runtime_diffs),
        "significant_database_difference_rows_abs_total_delta_gt_5": sum(
            1 for row in output_rows if row["significant_database_difference"] == "YES"
        ),
        "significant_runtime_difference_rows_abs_total_delta_gt_5": sum(
            1 for row in output_rows if row["significant_runtime_difference"] == "YES"
        ),
        "database_missing_hunt_codes": [row["hunt_code"] for row in output_rows if row["database_status"] == "MISSING"],
        "runtime_missing_hunt_codes": [row["hunt_code"] for row in output_rows if row["runtime_status"] == "MISSING"],
    }
    return output_rows, summary


def write_outputs(rows: list[dict[str, str]], summary: dict[str, object]) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    OUT_JSON.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")

    lines = [
        "# Current RAC Antlerless Elk Allotment Vs DATABASE / Runtime",
        "",
        "## Summary",
        "",
        f"- RAC rows compared: `{summary['row_count']}`",
        f"- Unique hunt codes: `{summary['unique_hunt_codes']}`",
        f"- DATABASE difference rows: `{summary['database_difference_rows']}`",
        f"- Runtime difference rows: `{summary['runtime_difference_rows']}`",
        f"- Significant DATABASE differences, abs total delta > 5: `{summary['significant_database_difference_rows_abs_total_delta_gt_5']}`",
        f"- Significant runtime differences, abs total delta > 5: `{summary['significant_runtime_difference_rows_abs_total_delta_gt_5']}`",
        "",
        "## DATABASE Status Counts",
        "",
    ]
    for key, value in sorted(summary["database_status_counts"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Runtime Status Counts", ""])
    for key, value in sorted(summary["runtime_status_counts"].items()):
        lines.append(f"- `{key}`: `{value}`")

    diffs = sorted(
        [row for row in rows if row["database_status"] != "MATCH"],
        key=lambda row: abs(to_int(row.get("database_delta_total")) or 0),
        reverse=True,
    )
    lines.extend(["", "## DATABASE Differences", ""])
    if diffs:
        lines.append("| Hunt code | Hunt name | RAC total | DATABASE total | Delta | Status |")
        lines.append("|---|---|---:|---:|---:|---|")
        for row in diffs:
            lines.append(
                f"| {row['hunt_code']} | {row['hunt_name']} | {row['permits_2026_total_allotted']} | "
                f"{row['database_2026_total']} | {row['database_delta_total']} | {row['database_status']} |"
            )
    else:
        lines.append("None.")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows, summary = build_rows()
    write_outputs(rows, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
