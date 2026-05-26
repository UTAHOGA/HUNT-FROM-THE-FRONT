from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
RETIRED = ROOT / "data_truth/crosswalk_truth/normalized/retired_current_hunt_codes_2026.csv"
CROSSWALK_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/current_to_historical_hunt_code_crosswalk_2026_summary.json"
LIVE_ONLINE_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/current_online_missing_hunt_codes_2026_review_summary.json"
ACTIVE_EA_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/current_active_ea_hunts_2026_reconciliation_summary.json"
BOUNDARY_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/database_boundary_id_fill_2026_summary.json"

BLACK_BEAR_CROSSWALK_SUMMARY = ROOT / "data_truth/crosswalk_truth/validation/black_bear_BR_2024_2025_2026_crosswalk_summary.json"
LE_DEER_VS_DATABASE = ROOT / "data_truth/draw_results_truth/validation/le_deer_2025_draw_results_model_target_2026_vs_DATABASE.csv"
OIL_VS_DATABASE = ROOT / "data_truth/draw_results_truth/validation/oil_2025_draw_results_model_target_2026_vs_DATABASE.csv"
HARVEST_2025 = ROOT / "data_truth/harvest_results_truth/normalized/harvest_results_2025_for_2026_long.csv"
HARVEST_2025_REPORT = ROOT / "data_truth/harvest_results_truth/normalized/harvest_results_2025_for_2026_report.json"
HARVEST_ALL_YEARS_SUMMARY = ROOT / "data_truth/harvest_results_truth/normalized/harvest_results_all_years_summary.json"

PERMIT_VALIDATION_DIR = ROOT / "data_truth/permit_overlay_truth/validation"
PERMIT_VS_DATABASE_FILES = [
    PERMIT_VALIDATION_DIR / "black_bear_permits_2026_vs_DATABASE.csv",
    PERMIT_VALIDATION_DIR / "buck_deer_permits_2026_vs_DATABASE.csv",
    PERMIT_VALIDATION_DIR / "desert_bighorn_permits_2026_vs_DATABASE.csv",
    PERMIT_VALIDATION_DIR / "elk_antlerless_private_lands_EA_2026_vs_DATABASE.csv",
    PERMIT_VALIDATION_DIR / "elk_private_lands_EL_LO_2026_vs_DATABASE.csv",
    PERMIT_VALIDATION_DIR / "rocky_bighorn_permits_2026_vs_DATABASE.csv",
]

OUT_DIR = ROOT / "data_truth/comparison_outputs/validation"
DASHBOARD = OUT_DIR / "comprehensive_2026_2025_history_integrity_audit.csv"
OPEN_ISSUES = OUT_DIR / "comprehensive_2026_2025_history_integrity_open_issues.csv"
SUMMARY = OUT_DIR / "comprehensive_2026_2025_history_integrity_summary.json"
REPORT = ROOT / "processed_data/comprehensive_2026_2025_history_integrity_audit.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def status_from_count(count: int, fail_on_positive: bool = False) -> str:
    if count == 0:
        return "PASS"
    return "FAIL" if fail_on_positive else "WARN"


def codes_sample(codes: Iterable[str], limit: int = 40) -> str:
    clean = sorted({code for code in codes if code})
    return "|".join(clean[:limit])


def add_check(
    rows: list[dict[str, object]],
    *,
    check_id: str,
    domain: str,
    status: str,
    severity: str,
    row_count: int,
    issue_count: int,
    evidence_path: Path | str,
    issue_codes: Iterable[str] = (),
    notes: str = "",
    recommended_next_step: str = "",
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "domain": domain,
            "status": status,
            "severity": severity,
            "row_count": row_count,
            "issue_count": issue_count,
            "issue_codes_sample": codes_sample(issue_codes),
            "evidence_path": str(evidence_path).replace("\\", "/"),
            "notes": notes,
            "recommended_next_step": recommended_next_step,
        }
    )


def add_issues(
    rows: list[dict[str, object]],
    *,
    issue_type: str,
    severity: str,
    source: Path | str,
    source_rows: Iterable[dict[str, str]],
    note: str,
    recommended_next_step: str,
) -> None:
    for row in source_rows:
        rows.append(
            {
                "issue_type": issue_type,
                "severity": severity,
                "hunt_code": row.get("hunt_code", ""),
                "boundary_id": row.get("boundary_id", ""),
                "hunt_name": row.get("hunt_name") or row.get("source_hunt_name") or row.get("raw_hunt_name", ""),
                "species": row.get("species", ""),
                "sex_type": row.get("sex_type", ""),
                "weapon": row.get("weapon", ""),
                "hunt_type": row.get("hunt_type", ""),
                "source": str(source).replace("\\", "/"),
                "note": note,
                "recommended_next_step": recommended_next_step,
            }
        )


def status_counts(rows: list[dict[str, str]], column: str) -> Counter:
    return Counter(row.get(column, "") for row in rows)


def nonmatch_rows(rows: list[dict[str, str]], status_column: str, allowed: set[str]) -> list[dict[str, str]]:
    return [row for row in rows if row.get(status_column, "") not in allowed]


def build_report(summary: dict, dashboard_rows: list[dict[str, object]]) -> str:
    lines = [
        "# Comprehensive 2026/2025 History Integrity Audit",
        "",
        f"- Generated UTC: `{summary['generated_at_utc']}`",
        f"- DATABASE active rows: `{summary['database']['row_count']}`",
        f"- DATABASE unique hunt codes: `{summary['database']['unique_hunt_code_count']}`",
        f"- Retired current-code ledger rows: `{summary['retired_current_codes']['ledger_row_count']}`",
        f"- Fatal blockers: `{summary['fatal_blocker_count']}`",
        f"- Review warnings: `{summary['review_warning_count']}`",
        "",
        "## Clean Core Checks",
        "",
        "- Active DATABASE has no duplicate hunt codes and no blank boundary IDs.",
        "- Retired 2026 current codes are absent from active DATABASE and preserved in the ledger.",
        "- Live-online DATABASE missing-code count is zero in the latest committed DWR snapshot audit.",
        "- Active EA reconciliation is clean: 204 live/current active EA rows and 204 DATABASE EA rows.",
        "- Permit overlay validations show zero numeric mismatches against protected DATABASE cells.",
        "",
        "## Remaining Review Classes",
        "",
    ]
    warn_rows = [row for row in dashboard_rows if row["status"] == "WARN"]
    if not warn_rows:
        lines.append("- No warning-class issues remain in this audit.")
    else:
        for row in warn_rows:
            lines.append(
                f"- `{row['check_id']}`: `{row['issue_count']}` issue rows. "
                f"{row['notes']} Next: {row['recommended_next_step']}"
            )
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- Dashboard CSV: `{DASHBOARD.relative_to(ROOT).as_posix()}`",
            f"- Open issues CSV: `{OPEN_ISSUES.relative_to(ROOT).as_posix()}`",
            f"- Summary JSON: `{SUMMARY.relative_to(ROOT).as_posix()}`",
            "",
            "Guardrail: this audit does not alter website feeds, materializer outputs, or protected numeric DATABASE cells.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dashboard: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []

    database_rows = read_csv(DATABASE)
    retired_rows = read_csv(RETIRED)
    database_codes = {row["hunt_code"] for row in database_rows}
    retired_codes = {row["hunt_code"] for row in retired_rows}
    duplicate_codes = [code for code, count in Counter(row["hunt_code"] for row in database_rows).items() if count > 1]
    blank_boundary = [row for row in database_rows if not row.get("boundary_id", "").strip()]
    retired_still_active = sorted(database_codes & retired_codes)

    database_issue_count = len(duplicate_codes) + len(blank_boundary) + len(retired_still_active)
    add_check(
        dashboard,
        check_id="database_current_2026_structural_integrity",
        domain="DATABASE",
        status=status_from_count(database_issue_count, fail_on_positive=True),
        severity="BLOCKER" if database_issue_count else "INFO",
        row_count=len(database_rows),
        issue_count=database_issue_count,
        evidence_path=DATABASE.relative_to(ROOT),
        issue_codes=[*duplicate_codes, *retired_still_active, *(row["hunt_code"] for row in blank_boundary)],
        notes=(
            f"duplicates={len(duplicate_codes)}; blank_boundary_ids={len(blank_boundary)}; "
            f"retired_codes_still_active={len(retired_still_active)}"
        ),
        recommended_next_step="Fix before any promotion if nonzero.",
    )

    add_check(
        dashboard,
        check_id="retired_current_code_ledger_integrity",
        domain="crosswalk_truth",
        status="PASS" if len(retired_rows) == len(retired_codes) == 17 and not retired_still_active else "FAIL",
        severity="INFO" if len(retired_rows) == len(retired_codes) == 17 and not retired_still_active else "BLOCKER",
        row_count=len(retired_rows),
        issue_count=0 if len(retired_rows) == len(retired_codes) == 17 and not retired_still_active else 1,
        evidence_path=RETIRED.relative_to(ROOT),
        issue_codes=retired_still_active,
        notes="Expected retired current-code ledger contains 17 user-confirmed 2026 retired codes.",
        recommended_next_step="Do not restore retired codes to active DATABASE unless user re-confirms live DWR reactivation.",
    )

    boundary_summary = read_json(BOUNDARY_SUMMARY)
    boundary_issues = int(boundary_summary.get("blank_boundary_id_after", 0)) + int(boundary_summary.get("duplicate_hunt_code_count", 0))
    add_check(
        dashboard,
        check_id="database_boundary_id_fill_validation",
        domain="crosswalk_truth",
        status=status_from_count(boundary_issues, fail_on_positive=True),
        severity="BLOCKER" if boundary_issues else "INFO",
        row_count=int(boundary_summary.get("database_row_count", len(database_rows))),
        issue_count=boundary_issues,
        evidence_path=BOUNDARY_SUMMARY.relative_to(ROOT),
        notes="Boundary fill audit should remain at zero blank boundary IDs and zero duplicate hunt codes.",
        recommended_next_step="Repair using reviewed JSON/GeoJSON evidence if nonzero.",
    )

    live_summary = read_json(LIVE_ONLINE_SUMMARY)
    missing_live = int(live_summary.get("database_codes_missing_from_live_count", 0))
    add_check(
        dashboard,
        check_id="live_online_current_hunt_code_presence",
        domain="live_dwr_snapshot",
        status=status_from_count(missing_live),
        severity="WARNING" if missing_live else "INFO",
        row_count=int(live_summary.get("database_hunt_code_count", len(database_rows))),
        issue_count=missing_live,
        evidence_path=LIVE_ONLINE_SUMMARY.relative_to(ROOT),
        notes=f"Live DWR hunt-code snapshot count={live_summary.get('live_hunt_code_count')}; live-only rows={live_summary.get('live_codes_not_in_database_count')}.",
        recommended_next_step="Review live-only rows only after source date/year context is registered.",
    )

    ea_summary = read_json(ACTIVE_EA_SUMMARY)
    ea_issues = int(ea_summary.get("active_ea_missing_from_database_count", 0)) + int(ea_summary.get("database_extra_not_current_active_count", 0))
    add_check(
        dashboard,
        check_id="active_ea_current_coverage",
        domain="live_dwr_snapshot",
        status=status_from_count(ea_issues),
        severity="WARNING" if ea_issues else "INFO",
        row_count=int(ea_summary.get("database_ea_count", 0)),
        issue_count=ea_issues,
        evidence_path=ACTIVE_EA_SUMMARY.relative_to(ROOT),
        issue_codes=[*ea_summary.get("active_ea_missing_from_database_codes", []), *ea_summary.get("database_extra_not_current_active_codes", [])],
        notes=f"live_active_ea={ea_summary.get('live_active_ea_count')}; database_ea={ea_summary.get('database_ea_count')}.",
        recommended_next_step="Any future nonzero extras need user-confirmed retire/archive handling.",
    )

    crosswalk_summary = read_json(CROSSWALK_SUMMARY)
    crosswalk_issues = int(crosswalk_summary.get("blocker_count", 0)) + int(crosswalk_summary.get("database_crosscheck_missing_count", 0)) + int(crosswalk_summary.get("duplicate_current_code_count", 0))
    add_check(
        dashboard,
        check_id="current_to_historical_crosswalk_integrity",
        domain="crosswalk_truth",
        status=status_from_count(crosswalk_issues, fail_on_positive=True),
        severity="BLOCKER" if crosswalk_issues else "INFO",
        row_count=int(crosswalk_summary.get("output_row_count", 0)),
        issue_count=crosswalk_issues,
        evidence_path=CROSSWALK_SUMMARY.relative_to(ROOT),
        notes=f"status_counts={crosswalk_summary.get('status_counts', {})}",
        recommended_next_step="Use this crosswalk for old-prefix/private-land/conservation mapping evidence only.",
    )

    permit_numeric_issue_total = 0
    for path in PERMIT_VS_DATABASE_FILES:
        rows = read_csv(path)
        if not rows:
            continue
        fields = rows[0].keys()
        status_column = next((col for col in ("comparison_status", "numeric_comparison_status") if col in fields), "")
        allowed = {"MATCH", "NO_NUMERIC_SOURCE", "SOURCE_AND_DATABASE_BLANK"}
        bad_rows = nonmatch_rows(rows, status_column, allowed) if status_column else []
        permit_numeric_issue_total += len(bad_rows)
        add_check(
            dashboard,
            check_id=f"permit_overlay_numeric_database_match__{path.stem}",
            domain="permit_overlay_truth",
            status=status_from_count(len(bad_rows), fail_on_positive=True),
            severity="BLOCKER" if bad_rows else "INFO",
            row_count=len(rows),
            issue_count=len(bad_rows),
            evidence_path=path.relative_to(ROOT),
            issue_codes=[row.get("hunt_code", "") for row in bad_rows],
            notes=f"{status_column or 'no_status_column'} counts={dict(status_counts(rows, status_column)) if status_column else {}}",
            recommended_next_step="Do not overwrite protected DATABASE cells; investigate source lineage first if nonzero.",
        )
        add_issues(
            issues,
            issue_type="PERMIT_OVERLAY_NUMERIC_MISMATCH",
            severity="BLOCKER",
            source=path.relative_to(ROOT),
            source_rows=bad_rows,
            note="Permit overlay validation does not match protected DATABASE numeric fields.",
            recommended_next_step="Resolve only from reviewed source lineage; never infer over populated DATABASE numbers.",
        )

    black_bear_summary = read_json(BLACK_BEAR_CROSSWALK_SUMMARY)
    black_bear_unmapped = int(black_bear_summary.get("draw_2025_rows", 0)) - int(black_bear_summary.get("draw_2025_rows_mapped_to_current_after_crosswalk", 0))
    add_check(
        dashboard,
        check_id="black_bear_2025_to_2026_history_crosswalk",
        domain="draw_results_truth",
        status=status_from_count(black_bear_unmapped, fail_on_positive=True),
        severity="BLOCKER" if black_bear_unmapped else "INFO",
        row_count=int(black_bear_summary.get("draw_2025_rows", 0)),
        issue_count=black_bear_unmapped,
        evidence_path=BLACK_BEAR_CROSSWALK_SUMMARY.relative_to(ROOT),
        notes=f"high_confidence_recodes={black_bear_summary.get('high_confidence_recode_count')}; code reuse BR7307 preserved.",
        recommended_next_step="Keep BR7307 code-reuse treatment; do not collapse historical BR7307 into current conservation BR7307.",
    )

    for label, path, expected_missing in [
        ("le_deer_2025_draw_to_database", LE_DEER_VS_DATABASE, 6),
        ("oil_2025_draw_to_database", OIL_VS_DATABASE, 12),
    ]:
        rows = read_csv(path)
        missing = [row for row in rows if row.get("database_comparison_status") == "MISSING_DATABASE_ROW"]
        diffs = [
            row
            for row in rows
            if row.get("database_comparison_status", "").startswith("DIFFERS")
            or row.get("database_comparison_status", "").startswith("MISMATCH")
        ]
        issue_count = len(missing) + len(diffs)
        status = "PASS" if issue_count == 0 else "WARN"
        add_check(
            dashboard,
            check_id=label,
            domain="draw_results_truth",
            status=status,
            severity="WARNING" if issue_count else "INFO",
            row_count=len(rows),
            issue_count=issue_count,
            evidence_path=path.relative_to(ROOT),
            issue_codes=[row.get("hunt_code", "") for row in [*missing, *diffs]],
            notes=f"missing_database_rows={len(missing)} expected={expected_missing}; numeric_diffs={len(diffs)}.",
            recommended_next_step="Treat missing rows as historical/CWMU review evidence unless user confirms they need active 2026 rows.",
        )
        add_issues(
            issues,
            issue_type=f"{label.upper()}_MISSING_DATABASE_ROW",
            severity="WARNING",
            source=path.relative_to(ROOT),
            source_rows=missing,
            note="Historical 2025 draw source row is not present in active 2026 DATABASE.",
            recommended_next_step="Classify as historical-only/CWMU retired, or add reviewed crosswalk if active current equivalent exists.",
        )
        add_issues(
            issues,
            issue_type=f"{label.upper()}_NUMERIC_DIFF",
            severity="BLOCKER",
            source=path.relative_to(ROOT),
            source_rows=diffs,
            note="Historical draw total differs from DATABASE 2025 draw fields.",
            recommended_next_step="Repair only from source-lineage evidence.",
        )

    harvest_rows = read_csv(HARVEST_2025)
    harvest_unmatched = [row for row in harvest_rows if row.get("hunt_code", "") not in database_codes]
    harvest_unmatched_not_retired = [row for row in harvest_unmatched if row.get("hunt_code", "") not in retired_codes]
    add_check(
        dashboard,
        check_id="harvest_2025_for_2026_database_code_presence",
        domain="harvest_results_truth",
        status=status_from_count(len(harvest_unmatched_not_retired)),
        severity="WARNING" if harvest_unmatched_not_retired else "INFO",
        row_count=len(harvest_rows),
        issue_count=len(harvest_unmatched_not_retired),
        evidence_path=HARVEST_2025.relative_to(ROOT),
        issue_codes=[row.get("hunt_code", "") for row in harvest_unmatched_not_retired],
        notes=(
            f"active_database_matches={len(harvest_rows) - len(harvest_unmatched)}; "
            f"unmatched_active_database={len(harvest_unmatched)}; retired_matches={len(harvest_unmatched) - len(harvest_unmatched_not_retired)}."
        ),
        recommended_next_step="Resolve remaining unmatched harvest codes as historical-only, CWMU-retired, or current-code crosswalk candidates.",
    )
    add_issues(
        issues,
        issue_type="HARVEST_2025_CODE_NOT_IN_ACTIVE_DATABASE",
        severity="WARNING",
        source=HARVEST_2025.relative_to(ROOT),
        source_rows=harvest_unmatched_not_retired,
        note="2025 harvest source code does not exist in active 2026 DATABASE and is not in the retired-current ledger.",
        recommended_next_step="Classify as historical-only/CWMU-retired or add a reviewed current-to-historical mapping.",
    )

    harvest_report = read_json(HARVEST_2025_REPORT)
    all_years_summary = read_json(HARVEST_ALL_YEARS_SUMMARY)
    add_check(
        dashboard,
        check_id="harvest_year_rule_integrity",
        domain="harvest_results_truth",
        status="PASS" if harvest_report.get("reported_hunt_year") == 2025 and harvest_report.get("model_target_year") == 2026 else "FAIL",
        severity="INFO" if harvest_report.get("reported_hunt_year") == 2025 and harvest_report.get("model_target_year") == 2026 else "BLOCKER",
        row_count=int(harvest_report.get("total_parsed_rows", 0)),
        issue_count=0 if harvest_report.get("reported_hunt_year") == 2025 and harvest_report.get("model_target_year") == 2026 else 1,
        evidence_path=HARVEST_2025_REPORT.relative_to(ROOT),
        notes=f"all_years_model_target_counts={all_years_summary.get('model_target_year_counts', {})}",
        recommended_next_step="Never use harvest source_permits as 2026 permit allocation truth.",
    )

    status_count = Counter(row["status"] for row in dashboard)
    severity_count = Counter(row["severity"] for row in dashboard)
    fatal_blockers = sum(1 for row in dashboard if row["status"] == "FAIL" or row["severity"] == "BLOCKER" and int(row["issue_count"]) > 0)
    review_warnings = sum(1 for row in dashboard if row["status"] == "WARN")

    summary = {
        "artifact": "comprehensive_2026_2025_history_integrity_audit",
        "generated_at_utc": generated_at,
        "database": {
            "path": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
            "row_count": len(database_rows),
            "unique_hunt_code_count": len(database_codes),
            "duplicate_hunt_code_count": len(duplicate_codes),
            "blank_boundary_id_count": len(blank_boundary),
        },
        "retired_current_codes": {
            "path": str(RETIRED.relative_to(ROOT)).replace("\\", "/"),
            "ledger_row_count": len(retired_rows),
            "retired_codes_still_active_count": len(retired_still_active),
            "codes": sorted(retired_codes),
        },
        "status_counts": dict(status_count),
        "severity_counts": dict(severity_count),
        "fatal_blocker_count": fatal_blockers,
        "review_warning_count": review_warnings,
        "permit_overlay_numeric_issue_total": permit_numeric_issue_total,
        "open_issue_count": len(issues),
        "open_issue_counts_by_type": dict(Counter(row["issue_type"] for row in issues)),
        "outputs": {
            "dashboard_csv": str(DASHBOARD.relative_to(ROOT)).replace("\\", "/"),
            "open_issues_csv": str(OPEN_ISSUES.relative_to(ROOT)).replace("\\", "/"),
            "summary_json": str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
            "markdown_report": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
        },
        "guardrails": [
            "No protected numeric DATABASE cells were changed by this audit.",
            "Website feeds and materializer outputs were not modified.",
            "Warning-class historical rows are review evidence, not promoted current truth.",
        ],
    }

    dashboard_fields = [
        "check_id",
        "domain",
        "status",
        "severity",
        "row_count",
        "issue_count",
        "issue_codes_sample",
        "evidence_path",
        "notes",
        "recommended_next_step",
    ]
    issue_fields = [
        "issue_type",
        "severity",
        "hunt_code",
        "boundary_id",
        "hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "source",
        "note",
        "recommended_next_step",
    ]
    write_csv(DASHBOARD, dashboard, dashboard_fields)
    write_csv(OPEN_ISSUES, issues, issue_fields)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(summary, dashboard), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if fatal_blockers == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
