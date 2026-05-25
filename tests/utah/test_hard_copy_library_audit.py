import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit-hard-copy-library.py"
REPORT = ROOT / "processed_data" / "hard_copy_library_audit_report.json"
ISSUES = ROOT / "processed_data" / "hard_copy_library_audit_issues.csv"
REPORT_MD = ROOT / "processed_data" / "hard_copy_library_audit_report.md"


def test_hard_copy_library_audit_outputs_and_counts():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)

    assert REPORT.exists()
    assert ISSUES.exists()
    assert REPORT_MD.exists()

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["artifact"] == "hard_copy_library_audit"
    assert report["counts"]["master_csv_records"] == 328
    assert report["counts"]["processed_pdf_manifest"] == 405
    assert report["counts"]["public_pdf_manifest"] == 405
    assert report["counts"]["public_documents"] == 9

    with ISSUES.open(newline="", encoding="utf-8") as handle:
        issues = list(csv.DictReader(handle))
    assert len(issues) == report["blocker_count"] + report["warning_count"]


def test_hard_copy_library_audit_identifies_publish_readiness_state():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)
    report = json.loads(REPORT.read_text(encoding="utf-8"))

    assert report["status"] in {"PUBLISH_SAFE", "NOT_PUBLISH_SAFE"}
    assert "guardrails" in report
    assert any("read-only" in item for item in report["guardrails"])
