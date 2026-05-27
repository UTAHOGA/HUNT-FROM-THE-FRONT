from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HARVEST_ISSUES = (
    ROOT / "data_truth/comparison_outputs/validation/comprehensive_2026_2025_history_integrity_open_issues.csv"
)
HARVEST_2025 = ROOT / "data_truth/harvest_results_truth/normalized/harvest_results_2025_for_2026_long.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
LEDGER = ROOT / "data_truth/crosswalk_truth/normalized/harvest_only_2025_code_resolutions.csv"
SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/harvest_only_2025_code_resolutions_summary.json"
REPORT = ROOT / "processed_data/harvest_only_2025_code_resolutions.md"

RESOLUTIONS: dict[str, dict[str, str]] = {
    "BI0001": {
        "resolution_status": "RESOLVED_SPORTSMAN_CONSERVATION_BOUNDARY_EQUIVALENT",
        "mapped_hunt_code": "BI1000",
        "mapped_boundary_id": "5000",
        "maps_to_draw_odds_code": "YES_SPORTSMAN_STATEWIDE_EQUIVALENT",
        "evidence": "User review indicates BI0001 is likely the statewide/sportsman-conservation bison permit boundary equivalent. DATABASE carries current statewide hunters choice bison as BI1000; conservation may share the boundary authority without its own distinct hunt code.",
        "source_evidence_files": "data/bison_hunt_table_official.json;pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    },
    "DB1774": {
        "resolution_status": "DISCONTINUED_2026_NO_DEFINITE_ONE_TO_ONE_MATCH",
        "mapped_hunt_code": "DB1774",
        "mapped_boundary_id": "",
        "maps_to_draw_odds_code": "NO_CURRENT_2026_DRAW_CODE",
        "evidence": "DB1774 appears in historical draw_reality_engine/harvest evidence, but no definite one-to-one 2026 DATABASE match exists. The old combined Chalk Creek/East Canyon/Morgan-South Rich Dedicated Hunter harvest code appears split across current unit-specific Dedicated Hunter rows, so it is discontinued as a single hunt code.",
        "source_evidence_files": "processed_data/draw_reality_engine.csv;data_truth/harvest_results_truth/normalized/harvest_results_2025_for_2026_long.csv",
    },
    "PB5343": {
        "resolution_status": "DISCONTINUED_2026_NO_DEFINITE_ONE_TO_ONE_MATCH",
        "mapped_hunt_code": "PB5343",
        "mapped_boundary_id": "919",
        "maps_to_draw_odds_code": "NO_CURRENT_2026_DRAW_CODE",
        "evidence": "PB5343 appears in historical official pronghorn table/point-ladder evidence for Prohibition Springs CWMU, but no current 2026 DATABASE row has a definite hunt-name, weapon, species, and sex-type match. Treat as discontinued effective 2026.",
        "source_evidence_files": "data/pronghorn_hunt_table_official.json;point_ladder_view.csv;data_truth/harvest_results_truth/normalized/harvest_results_2025_for_2026_long.csv",
    },
    "PD1041": {
        "resolution_status": "RESOLVED_RECODED_TO_CURRENT_HEIST_CWMU_DOE_ROW",
        "mapped_hunt_code": "PD1052",
        "mapped_boundary_id": "201",
        "maps_to_draw_odds_code": "YES_HISTORICAL_AND_CURRENT_RECODE",
        "evidence": "PD1041 appears in official pronghorn hunt table and draw_reality_engine for Heist CWMU doe; current DATABASE carries Heist CWMU doe as PD1052.",
        "source_evidence_files": "data/pronghorn_hunt_table_official.json;processed_data/draw_reality_engine.csv;pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    },
}

FIELDS = [
    "resolved_at_utc",
    "reported_hunt_year",
    "model_target_year",
    "source_hunt_code",
    "source_hunt_name",
    "source_species",
    "source_sex_type",
    "source_weapon",
    "source_hunt_type",
    "source_permits",
    "source_harvest",
    "source_file",
    "source_page",
    "source_row",
    "resolution_status",
    "mapped_hunt_code",
    "mapped_boundary_id",
    "mapped_hunt_name",
    "mapped_species",
    "mapped_sex_type",
    "mapped_weapon",
    "mapped_hunt_type",
    "maps_to_draw_odds_code",
    "evidence",
    "source_evidence_files",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> int:
    resolved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    issue_rows = [
        row
        for row in read_csv(HARVEST_ISSUES)
        if row.get("issue_type") == "HARVEST_2025_CODE_NOT_IN_ACTIVE_DATABASE"
    ]
    if not issue_rows:
        issue_rows = [
            {
                "hunt_code": row.get("hunt_code", ""),
                "hunt_name": row.get("hunt_name", ""),
                "species": row.get("species", ""),
                "sex_type": row.get("sex_type", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "source": row.get("source_file", ""),
                "source_permits": row.get("source_permits", ""),
                "source_harvest": row.get("harvest", ""),
                "source_page": row.get("source_page", ""),
                "source_row": row.get("source_row", ""),
            }
            for row in read_csv(HARVEST_2025)
            if row.get("hunt_code") in RESOLUTIONS
        ]
    database = {row["hunt_code"]: row for row in read_csv(DATABASE)}

    issue_codes = {row["hunt_code"] for row in issue_rows}
    unresolved = sorted(issue_codes - set(RESOLUTIONS))
    if unresolved:
        raise RuntimeError(f"Harvest-only issue codes missing reviewed resolution: {unresolved}")

    rows: list[dict[str, Any]] = []
    for issue in sorted(issue_rows, key=lambda row: row["hunt_code"]):
        code = issue["hunt_code"]
        resolution = RESOLUTIONS[code]
        mapped = database.get(resolution["mapped_hunt_code"], {})
        rows.append(
            {
                "resolved_at_utc": resolved_at,
                "reported_hunt_year": "2025",
                "model_target_year": "2026",
                "source_hunt_code": code,
                "source_hunt_name": issue.get("hunt_name", ""),
                "source_species": issue.get("species", ""),
                "source_sex_type": issue.get("sex_type", ""),
                "source_weapon": issue.get("weapon", ""),
                "source_hunt_type": issue.get("hunt_type", ""),
                "source_permits": issue.get("source_permits", ""),
                "source_harvest": issue.get("source_harvest", ""),
                "source_file": issue.get("source", ""),
                "source_page": issue.get("source_page", ""),
                "source_row": issue.get("source_row", ""),
                **resolution,
                "mapped_hunt_name": mapped.get("hunt_name", ""),
                "mapped_species": mapped.get("species", ""),
                "mapped_sex_type": mapped.get("sex_type", ""),
                "mapped_weapon": mapped.get("weapon", ""),
                "mapped_hunt_type": mapped.get("hunt_type", ""),
            }
        )

    write_csv(LEDGER, rows, FIELDS)

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["resolution_status"]] = status_counts.get(row["resolution_status"], 0) + 1
    summary = {
        "artifact": "harvest_only_2025_code_resolutions",
        "generated_at_utc": resolved_at,
        "resolved_code_count": len(rows),
        "resolved_codes": [row["source_hunt_code"] for row in rows],
        "status_counts": status_counts,
        "draw_odds_mapping_status_counts": {
            status: sum(1 for row in rows if row["maps_to_draw_odds_code"] == status)
            for status in sorted({row["maps_to_draw_odds_code"] for row in rows})
        },
        "guardrail": "Reviewed harvest-code resolution ledger only. Does not modify DATABASE.csv, website feeds, prediction files, or 2026 permit/allotment values.",
        "outputs": {
            "ledger_csv": LEDGER.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY.relative_to(ROOT).as_posix(),
            "report_md": REPORT.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Harvest-Only 2025 Code Resolutions",
        "",
        f"- Generated UTC: `{resolved_at}`",
        f"- Resolved harvest-only codes: `{len(rows)}`",
        "- This ledger resolves harvest-source code presence warnings without changing 2026 permit/allotment truth.",
        "",
        "| Source code | Source hunt | Resolution | Mapped code | Boundary ID | Draw odds mapping |",
        "|---|---|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['source_hunt_code']} | {row['source_hunt_name']} | {row['resolution_status']} | "
            f"{row['mapped_hunt_code']} | {row['mapped_boundary_id']} | {row['maps_to_draw_odds_code']} |"
        )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
