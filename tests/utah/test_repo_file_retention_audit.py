from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "processed_data" / "repo_file_retention_audit.csv"
SUMMARY = ROOT / "processed_data" / "repo_file_retention_audit.json"
REPORT = ROOT / "processed_data" / "repo_file_retention_audit.md"
CLOUDFLARE = ROOT / "processed_data" / "repo_file_retention_cloudflare_manifest.csv"
GITHUB_KEEP = ROOT / "processed_data" / "repo_file_retention_github_keep_manifest.csv"
DELETE = ROOT / "processed_data" / "repo_file_retention_delete_after_backup_manifest.csv"
REVIEW = ROOT / "processed_data" / "repo_file_retention_review_required_manifest.csv"


def run_audit() -> None:
    subprocess.run(
        ["python", "scripts/audit-repo-file-retention.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def by_path(path: Path) -> dict[str, dict[str, str]]:
    return {row["path"]: row for row in read_csv(path)}


def test_audit_script_runs_and_writes_required_files() -> None:
    run_audit()
    for path in [AUDIT, SUMMARY, REPORT, CLOUDFLARE, GITHUB_KEEP, DELETE, REVIEW]:
        assert path.exists()
        assert path.stat().st_size > 0


def test_work_log_is_doc_or_schema() -> None:
    row = by_path(AUDIT)["WORK_LOG.md"]
    assert row["recommended_action"] == "KEEP_IN_GITHUB_DOC_OR_SCHEMA"


def test_engine_files_are_rebuild_scripts_or_tests() -> None:
    row = by_path(AUDIT)["engine/utah_predictive_mixed/materialize.py"]
    assert row["recommended_action"] == "KEEP_IN_GITHUB_REBUILD_SCRIPT_OR_TEST"


def test_tests_files_are_rebuild_scripts_or_tests() -> None:
    row = by_path(AUDIT)["tests/utah_predictive_mixed/test_materialized_outputs.py"]
    assert row["recommended_action"] == "KEEP_IN_GITHUB_REBUILD_SCRIPT_OR_TEST"


def test_predictive_runtime_is_not_delete_candidate() -> None:
    row = by_path(AUDIT)["processed_data/draw_reality_engine_predictive_v2.csv"]
    assert row["recommended_action"] != "DELETE_AFTER_BACKUP"


def test_large_processed_runtime_csvs_go_to_cloudflare_runtime() -> None:
    rows = by_path(AUDIT)
    assert rows["processed_data/draw_reality_engine_predictive_v2.csv"]["recommended_action"] == "CLOUDFLARE_R2_RUNTIME_DATA"
    assert rows["processed_data/ml_draw_predictions_v1.csv"]["recommended_action"] == "CLOUDFLARE_R2_RUNTIME_DATA"


def test_raw_pdfs_are_not_online_static_site() -> None:
    pdf_rows = [row for row in read_csv(AUDIT) if row["extension"] == ".pdf" and row["path"].startswith("pipeline/RAW/")]
    assert pdf_rows
    assert all(row["recommended_action"] != "ONLINE_STATIC_SITE" for row in pdf_rows)


def test_zip_files_are_not_kept_in_github_by_default() -> None:
    zip_rows = [row for row in read_csv(AUDIT) if row["extension"] == ".zip"]
    assert zip_rows
    assert all(not row["recommended_action"].startswith("KEEP_IN_GITHUB") for row in zip_rows)


def test_pycache_and_pyc_are_delete_after_backup() -> None:
    rows = [row for row in read_csv(AUDIT) if "__pycache__" in row["path"] or row["extension"] == ".pyc"]
    assert rows
    assert all(row["recommended_action"] == "DELETE_AFTER_BACKUP" for row in rows)


def test_cloudflare_manifest_contains_suggested_r2_keys() -> None:
    rows = read_csv(CLOUDFLARE)
    assert rows
    assert all(row["suggested_r2_key"] for row in rows)


def test_delete_manifest_never_includes_database() -> None:
    paths = {row["path"] for row in read_csv(DELETE)}
    assert "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv" not in paths


def test_github_keep_manifest_includes_database() -> None:
    paths = {row["path"] for row in read_csv(GITHUB_KEEP)}
    assert "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv" in paths


def test_report_lists_largest_files() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "## Largest 100 Files" in text


def test_report_includes_proposed_gitignore_changes() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "## Exact Proposed .gitignore Additions" in text
    assert "data_model/runtime_drafts/*.csv" in text
