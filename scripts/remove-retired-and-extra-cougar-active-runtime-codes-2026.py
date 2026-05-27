from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"

ACTIVE_SURFACES = {
    "hunt_master_enriched": ROOT / "processed_data" / "hunt_master_enriched.csv",
    "point_ladder_view": ROOT / "processed_data" / "point_ladder_view.csv",
    "hunt_master_enriched_2026_draw_subset": ROOT / "processed_data" / "hunt_master_enriched_2026_draw_subset.csv",
    "ml_draw_predictions_v1": ROOT / "processed_data" / "ml_draw_predictions_v1.csv",
    "draw_reality_engine_predictive_v2": ROOT / "processed_data" / "draw_reality_engine_predictive_v2.csv",
}

ARCHIVE = ROOT / "data_truth" / "crosswalk_truth" / "normalized" / "active_runtime_codes_removed_2026.csv"
SUMMARY = ROOT / "data_truth" / "crosswalk_truth" / "validation" / "active_runtime_codes_removed_2026_summary.json"
REPORT = ROOT / "processed_data" / "active_runtime_codes_removed_2026.md"

RETIRED_CODES = {
    "EA1007",
    "EA1053",
    "EA1287",
    "EA1288",
    "EA1289",
    "EA1290",
    "EA1291",
    "EA1292",
    "EA1293",
    "EA1294",
    "EA1295",
    "EA1296",
    "EA1297",
    "EA1298",
    "EA1299",
    "EA1300",
    "PD1039",
}

RETIRED_REASON = "USER_CONFIRMED_RETIRED_EFFECTIVE_2026"
COUGAR_REASON = "CURRENT_DWR_DATABASE_HAS_SINGLE_STATEWIDE_COUGAR_CODE_CG9999"


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def read_optional_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    return read_csv(path)


def hunt_code(row: dict[str, str]) -> str:
    return (row.get("hunt_code") or row.get("Hunt Code") or "").strip().upper()


def removal_reason(code: str) -> str:
    if code in RETIRED_CODES:
        return RETIRED_REASON
    if code.startswith("CG") and code != "CG9999":
        return COUGAR_REASON
    return ""


def unique_codes(rows: list[dict[str, str]]) -> set[str]:
    return {hunt_code(row) for row in rows if hunt_code(row)}


def count_duplicates(codes: set[str], rows: list[dict[str, str]]) -> list[str]:
    counts = Counter(hunt_code(row) for row in rows if hunt_code(row))
    return sorted(code for code in codes if counts[code] > 1)


def sample_value(rows: list[dict[str, str]], field: str) -> str:
    for row in rows:
        value = (row.get(field) or "").strip()
        if value:
            return value
    return ""


def summarize_removed_rows(surface: str, rows: list[dict[str, str]], timestamp: str) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(hunt_code(row), []).append(row)

    archive_rows: list[dict[str, str]] = []
    for code in sorted(grouped):
        code_rows = grouped[code]
        archive_rows.append(
            {
                "removed_at_utc": timestamp,
                "effective_year": "2026",
                "surface": surface,
                "hunt_code": code,
                "removal_reason": removal_reason(code),
                "removed_row_count": str(len(code_rows)),
                "hunt_name": sample_value(code_rows, "hunt_name"),
                "species": sample_value(code_rows, "species"),
                "sex_type": sample_value(code_rows, "sex_type"),
                "weapon": sample_value(code_rows, "weapon"),
                "hunt_class": sample_value(code_rows, "hunt_class"),
                "hunt_type": sample_value(code_rows, "hunt_type"),
                "season": sample_value(code_rows, "season") or sample_value(code_rows, "season_dates"),
                "permits_2026_res": sample_value(code_rows, "permits_2026_res"),
                "permits_2026_nr": sample_value(code_rows, "permits_2026_nr"),
                "permits_2026_total": sample_value(code_rows, "permits_2026_total"),
                "source_status": sample_value(code_rows, "data_status") or sample_value(code_rows, "status"),
            }
        )
    return archive_rows


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    database_rows, _ = read_csv(DATABASE)
    database_codes = unique_codes(database_rows)

    database_cougar_codes = sorted(code for code in database_codes if code.startswith("CG"))
    if database_cougar_codes != ["CG9999"]:
        raise SystemExit(f"DATABASE.csv must carry only CG9999 for current cougar; found {database_cougar_codes}")
    if database_codes & RETIRED_CODES:
        raise SystemExit(f"DATABASE.csv still contains retired 2026 codes: {sorted(database_codes & RETIRED_CODES)}")

    new_archive_rows: list[dict[str, str]] = []
    surface_summaries: dict[str, dict[str, object]] = {}
    blocker_messages: list[str] = []

    for surface, path in ACTIVE_SURFACES.items():
        rows, columns = read_csv(path)
        before_codes = unique_codes(rows)
        removable_rows = [row for row in rows if removal_reason(hunt_code(row))]
        kept_rows = [row for row in rows if not removal_reason(hunt_code(row))]
        write_csv(path, kept_rows, columns)

        after_codes = unique_codes(kept_rows)
        remaining_retired = sorted(after_codes & RETIRED_CODES)
        remaining_extra_cougar = sorted(code for code in after_codes if code.startswith("CG") and code != "CG9999")
        missing_database_codes = sorted(database_codes - after_codes) if surface in {"hunt_master_enriched", "point_ladder_view"} else []
        extra_database_codes = sorted(after_codes - database_codes) if surface in {"hunt_master_enriched", "point_ladder_view"} else []

        if remaining_retired:
            blocker_messages.append(f"{surface} still has retired codes: {remaining_retired}")
        if remaining_extra_cougar:
            blocker_messages.append(f"{surface} still has non-CG9999 cougar codes: {remaining_extra_cougar}")
        if missing_database_codes:
            blocker_messages.append(f"{surface} is missing current DATABASE codes: {missing_database_codes[:20]}")
        if extra_database_codes:
            blocker_messages.append(f"{surface} still has active extras not in DATABASE: {extra_database_codes[:20]}")

        surface_archive_rows = summarize_removed_rows(surface, removable_rows, timestamp)
        new_archive_rows.extend(surface_archive_rows)
        surface_summaries[surface] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "row_count_before": len(rows),
            "row_count_after": len(kept_rows),
            "row_delta": len(kept_rows) - len(rows),
            "unique_hunt_codes_before": len(before_codes),
            "unique_hunt_codes_after": len(after_codes),
            "removed_row_count": len(removable_rows),
            "removed_unique_hunt_code_count": len({row["hunt_code"] for row in surface_archive_rows}),
            "removed_retired_code_count": len({row["hunt_code"] for row in surface_archive_rows if row["removal_reason"] == RETIRED_REASON}),
            "removed_extra_cougar_code_count": len({row["hunt_code"] for row in surface_archive_rows if row["removal_reason"] == COUGAR_REASON}),
            "remaining_retired_codes": remaining_retired,
            "remaining_extra_cougar_codes": remaining_extra_cougar,
            "missing_database_code_count": len(missing_database_codes),
            "extra_database_code_count": len(extra_database_codes),
        }

    archive_columns = [
        "removed_at_utc",
        "effective_year",
        "surface",
        "hunt_code",
        "removal_reason",
        "removed_row_count",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_class",
        "hunt_type",
        "season",
        "permits_2026_res",
        "permits_2026_nr",
        "permits_2026_total",
        "source_status",
    ]
    existing_archive_rows, _ = read_optional_csv(ARCHIVE)
    archive_by_key: dict[tuple[str, str, str], dict[str, str]] = {
        (row.get("surface", ""), row.get("hunt_code", ""), row.get("removal_reason", "")): row
        for row in existing_archive_rows
    }
    for row in new_archive_rows:
        archive_by_key[(row["surface"], row["hunt_code"], row["removal_reason"])] = row
    archive_rows = sorted(
        archive_by_key.values(),
        key=lambda row: (row.get("surface", ""), row.get("removal_reason", ""), row.get("hunt_code", "")),
    )
    write_csv(ARCHIVE, archive_rows, archive_columns)

    retired_removed_codes = sorted({row["hunt_code"] for row in archive_rows if row["removal_reason"] == RETIRED_REASON})
    extra_cougar_removed_codes = sorted({row["hunt_code"] for row in archive_rows if row["removal_reason"] == COUGAR_REASON})
    newly_retired_removed_codes = sorted({row["hunt_code"] for row in new_archive_rows if row["removal_reason"] == RETIRED_REASON})
    newly_extra_cougar_removed_codes = sorted({row["hunt_code"] for row in new_archive_rows if row["removal_reason"] == COUGAR_REASON})

    summary = {
        "artifact": "active_runtime_codes_removed_2026",
        "timestamp_utc": timestamp,
        "database_path": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
        "archive_path": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
        "database_row_count": len(database_rows),
        "database_unique_hunt_code_count": len(database_codes),
        "database_cougar_codes": database_cougar_codes,
        "requested_retired_codes": sorted(RETIRED_CODES),
        "retired_codes_removed_from_active_surfaces": retired_removed_codes,
        "extra_cougar_codes_removed_from_active_surfaces": extra_cougar_removed_codes,
        "newly_removed_archive_row_count": len(new_archive_rows),
        "total_removed_archive_row_count": len(archive_rows),
        "surface_summaries": surface_summaries,
        "newly_retired_codes_removed_from_active_surfaces": newly_retired_removed_codes,
        "newly_extra_cougar_codes_removed_from_active_surfaces": newly_extra_cougar_removed_codes,
        "blocker_count": len(blocker_messages),
        "blockers": blocker_messages,
        "guardrail": "DATABASE.csv was validation input only and was not modified.",
    }

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Active Runtime Code Cleanup 2026",
        "",
        f"- Timestamp UTC: `{timestamp}`",
        f"- DATABASE current hunt codes: `{len(database_codes)}`",
        f"- DATABASE cougar codes: `{', '.join(database_cougar_codes)}`",
        f"- New archive rows written this run: `{len(new_archive_rows)}`",
        f"- Total archive rows: `{len(archive_rows)}`",
        f"- Retired codes archived: `{len(retired_removed_codes)}`",
        f"- Extra cougar codes archived: `{len(extra_cougar_removed_codes)}`",
        f"- Blockers: `{len(blocker_messages)}`",
        "",
        "## Surface Results",
        "",
    ]
    for surface, detail in surface_summaries.items():
        lines.append(
            f"- `{surface}`: rows `{detail['row_count_before']}` -> `{detail['row_count_after']}`, "
            f"unique hunt codes `{detail['unique_hunt_codes_before']}` -> `{detail['unique_hunt_codes_after']}`, "
            f"removed rows `{detail['removed_row_count']}`"
        )
    lines.extend(["", "## Removed Code Sets", ""])
    lines.append(f"- Retired EA/PD codes: `{';'.join(retired_removed_codes)}`")
    lines.append(f"- Non-current cougar codes: `{';'.join(extra_cougar_removed_codes)}`")
    if blocker_messages:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {message}" for message in blocker_messages)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if blocker_messages else 0


if __name__ == "__main__":
    raise SystemExit(main())
