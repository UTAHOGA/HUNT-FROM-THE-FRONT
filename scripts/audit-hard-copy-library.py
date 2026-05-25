#!/usr/bin/env python3
"""Audit the hard-copy/document-library database and publish readiness.

This is read-only against the library inputs. It intentionally does not rebuild
`hard-copy/`, `public/hard-copy/`, `generated/pages`, or `pages-dist`.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "processed_data" / "hard_copy_library_audit_report.json"
OUT_MD = ROOT / "processed_data" / "hard_copy_library_audit_report.md"
OUT_CSV = ROOT / "processed_data" / "hard_copy_library_audit_issues.csv"

PATHS = {
    "master_csv": ROOT / "pipeline/RAW/hunt_unit_database/library-master.csv",
    "master_json": ROOT / "pipeline/RAW/hunt_unit_database/library-master.json",
    "master_summary": ROOT / "pipeline/RAW/hunt_unit_database/library-master-summary.json",
    "source_documents": ROOT / "hard-copy/documents.json",
    "public_documents": ROOT / "public/hard-copy/data/documents.json",
    "generated_page": ROOT / "generated/pages/hard-copies.json",
    "canonical_page": ROOT / "canonical/hard-copies-2026.json",
    "processed_pdf_manifest": ROOT / "processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json",
    "public_pdf_manifest": ROOT / "public/hard-copy/manifests/hard_copy_pdf_manifest.web.json",
    "pages_dist_pdf_manifest": ROOT / "pages-dist/processed_data/hard_data_exports/hard_copy_pdf_manifest.web.json",
    "processed_hard_data_manifest": ROOT / "processed_data/hard_data_exports/hard_data_manifest.web.json",
    "public_hard_data_manifest": ROOT / "public/hard-copy/manifests/hard_data_manifest.web.json",
    "pages_dist_hard_data_manifest": ROOT / "pages-dist/processed_data/hard_data_exports/hard_data_manifest.web.json",
    "pages_dist_public_documents": ROOT / "pages-dist/hard-copy/data/documents.json",
    "hard_copy_html": ROOT / "hard-copy.html",
    "pages_dist_hard_copy_html": ROOT / "pages-dist/hard-copy.html",
}

ISSUE_FIELDS = ["severity", "code", "path", "detail"]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def add_issue(issues: list[dict[str, str]], severity: str, code: str, path: Path | str, detail: str) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "path": rel(path) if isinstance(path, Path) else path,
            "detail": detail,
        }
    )


def list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def resolve_site_href(href: str, base: Path) -> Path:
    clean = (href or "").strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        return Path("__external__")
    clean = clean.split("#", 1)[0].split("?", 1)[0]
    if clean.startswith("./"):
        clean = clean[2:]
    if clean.startswith("/"):
        clean = clean[1:]
    return base / clean


def duplicate_count(records: list[dict[str, Any]], fields: list[str]) -> tuple[int, list[str]]:
    keys = Counter(tuple(str(row.get(field, "")).strip() for field in fields) for row in records)
    duplicates = ["|".join(key) for key, count in keys.items() if count > 1 and any(key)]
    return sum(keys[tuple(item.split("|"))] - 1 for item in duplicates), duplicates[:20]


def audit_href_records(
    records: list[dict[str, Any]],
    href_field: str,
    base: Path,
    label: str,
    issues: list[dict[str, str]],
    companion_field: str | None = None,
) -> dict[str, int]:
    checked = 0
    missing = 0
    external = 0
    for index, row in enumerate(records):
        href = str(row.get(href_field, "")).strip()
        if not href:
            missing += 1
            add_issue(issues, "ERROR", "MISSING_HREF", label, f"row {index + 1} has blank {href_field}")
            continue
        target = resolve_site_href(href, base)
        if str(target) == "__external__":
            external += 1
            continue
        checked += 1
        if not target.exists():
            missing += 1
            add_issue(issues, "ERROR", "BROKEN_HREF", label, f"{href_field}={href} does not resolve under {rel(base)}")
        if companion_field:
            companion = str(row.get(companion_field, "")).strip()
            if companion:
                companion_target = resolve_site_href(companion, base)
                checked += 1
                if str(companion_target) != "__external__" and not companion_target.exists():
                    missing += 1
                    add_issue(
                        issues,
                        "ERROR",
                        "BROKEN_COMPANION_HREF",
                        label,
                        f"{companion_field}={companion} does not resolve under {rel(base)}",
                    )
    return {"checked": checked, "missing": missing, "external": external}


def extract_generated_library(page_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(page_payload, dict):
        return []
    library = page_payload.get("library")
    if isinstance(library, list):
        return library
    if isinstance(library, dict):
        for key in ("items", "records", "documents"):
            if isinstance(library.get(key), list):
                return library[key]
    return []


def main() -> None:
    issues: list[dict[str, str]] = []
    files = {name: {"path": rel(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0} for name, path in PATHS.items()}
    for name, path in PATHS.items():
        if not path.exists():
            severity = "ERROR" if name in {"master_csv", "master_json", "public_documents", "hard_copy_html"} else "WARN"
            add_issue(issues, severity, "MISSING_EXPECTED_FILE", path, f"{name} is missing")

    master_rows = read_csv(PATHS["master_csv"]) if PATHS["master_csv"].exists() else []
    master_json = read_json(PATHS["master_json"]) if PATHS["master_json"].exists() else {}
    master_summary = read_json(PATHS["master_summary"]) if PATHS["master_summary"].exists() else {}
    public_docs = read_json(PATHS["public_documents"]) if PATHS["public_documents"].exists() else []
    processed_pdf_manifest = read_json(PATHS["processed_pdf_manifest"]) if PATHS["processed_pdf_manifest"].exists() else []
    public_pdf_manifest = read_json(PATHS["public_pdf_manifest"]) if PATHS["public_pdf_manifest"].exists() else []
    pages_dist_pdf_manifest = read_json(PATHS["pages_dist_pdf_manifest"]) if PATHS["pages_dist_pdf_manifest"].exists() else []
    processed_hard_data_manifest = read_json(PATHS["processed_hard_data_manifest"]) if PATHS["processed_hard_data_manifest"].exists() else []
    public_hard_data_manifest = read_json(PATHS["public_hard_data_manifest"]) if PATHS["public_hard_data_manifest"].exists() else []
    generated_page = read_json(PATHS["generated_page"]) if PATHS["generated_page"].exists() else {}
    canonical_page = read_json(PATHS["canonical_page"]) if PATHS["canonical_page"].exists() else {}
    generated_library = extract_generated_library(generated_page)
    canonical_library = extract_generated_library(canonical_page)

    source_documents_text = read_text(PATHS["source_documents"]) if PATHS["source_documents"].exists() else ""
    if source_documents_text.strip() == "documents.json":
        add_issue(
            issues,
            "ERROR",
            "SOURCE_DOCUMENTS_STUB",
            PATHS["source_documents"],
            "hard-copy/documents.json contains only the literal stub text 'documents.json'",
        )

    if isinstance(master_json, dict) and master_json.get("record_count") != len(master_rows):
        add_issue(
            issues,
            "ERROR",
            "MASTER_COUNT_MISMATCH",
            PATHS["master_json"],
            f"master_json record_count={master_json.get('record_count')} but CSV rows={len(master_rows)}",
        )

    for label, records in [
        ("master_csv", master_rows),
        ("public_documents", public_docs if isinstance(public_docs, list) else []),
        ("processed_pdf_manifest", processed_pdf_manifest if isinstance(processed_pdf_manifest, list) else []),
        ("generated_page_library", generated_library),
    ]:
        dup_count, examples = duplicate_count(records, ["id"] if label == "public_documents" else ["href", "title", "year", "group", "type"])
        if dup_count:
            add_issue(issues, "WARN", "DUPLICATE_RECORD_KEYS", label, f"{dup_count} duplicate keys; examples: {examples}")

    root_href_audit = audit_href_records(
        processed_pdf_manifest if isinstance(processed_pdf_manifest, list) else [],
        "href",
        ROOT,
        "processed_pdf_manifest_root",
        issues,
        "companion_href",
    )
    pages_dist_href_audit = audit_href_records(
        pages_dist_pdf_manifest if isinstance(pages_dist_pdf_manifest, list) else [],
        "href",
        ROOT / "pages-dist",
        "pages_dist_pdf_manifest",
        issues,
        "companion_href",
    )
    public_docs_href_audit = audit_href_records(
        public_docs if isinstance(public_docs, list) else [],
        "pdfUrl",
        ROOT / "public",
        "public_documents",
        issues,
    )
    pages_dist_public_docs_href_audit = audit_href_records(
        public_docs if isinstance(public_docs, list) else [],
        "pdfUrl",
        ROOT / "pages-dist",
        "pages_dist_public_documents_expected",
        issues,
    )

    if list_count(processed_pdf_manifest) != list_count(public_pdf_manifest):
        add_issue(
            issues,
            "ERROR",
            "PROCESSED_PUBLIC_MANIFEST_COUNT_MISMATCH",
            "hard_copy_pdf_manifest.web.json",
            f"processed={list_count(processed_pdf_manifest)} public={list_count(public_pdf_manifest)}",
        )
    if list_count(processed_pdf_manifest) != list_count(pages_dist_pdf_manifest):
        add_issue(
            issues,
            "ERROR",
            "PROCESSED_PAGES_DIST_MANIFEST_COUNT_MISMATCH",
            "hard_copy_pdf_manifest.web.json",
            f"processed={list_count(processed_pdf_manifest)} pages_dist={list_count(pages_dist_pdf_manifest)}",
        )
    if list_count(processed_hard_data_manifest) != list_count(public_hard_data_manifest):
        add_issue(
            issues,
            "ERROR",
            "HARD_DATA_MANIFEST_COUNT_MISMATCH",
            "hard_data_manifest.web.json",
            f"processed={list_count(processed_hard_data_manifest)} public={list_count(public_hard_data_manifest)}",
        )

    if PATHS["hard_copy_html"].exists():
        html = read_text(PATHS["hard_copy_html"])
        if 'const DOCUMENTS_URL = "/hard-copy/data/documents.json"' in html and not PATHS["pages_dist_public_documents"].exists():
            add_issue(
                issues,
                "ERROR",
                "PAGES_DIST_MISSING_LIBRARY_DATA_ROUTE",
                PATHS["pages_dist_public_documents"],
                "hard-copy.html fetches /hard-copy/data/documents.json, but pages-dist does not contain that route",
            )

    severity_counts = Counter(issue["severity"] for issue in issues)
    code_counts = Counter(issue["code"] for issue in issues)
    report = {
        "artifact": "hard_copy_library_audit",
        "status": "PUBLISH_SAFE" if severity_counts.get("ERROR", 0) == 0 else "NOT_PUBLISH_SAFE",
        "blocker_count": severity_counts.get("ERROR", 0),
        "warning_count": severity_counts.get("WARN", 0),
        "issue_code_counts": dict(sorted(code_counts.items())),
        "files": files,
        "counts": {
            "master_csv_records": len(master_rows),
            "master_json_record_count": master_json.get("record_count") if isinstance(master_json, dict) else None,
            "master_summary_record_count": master_summary.get("record_count") if isinstance(master_summary, dict) else None,
            "public_documents": list_count(public_docs),
            "processed_pdf_manifest": list_count(processed_pdf_manifest),
            "public_pdf_manifest": list_count(public_pdf_manifest),
            "pages_dist_pdf_manifest": list_count(pages_dist_pdf_manifest),
            "processed_hard_data_manifest": list_count(processed_hard_data_manifest),
            "public_hard_data_manifest": list_count(public_hard_data_manifest),
            "canonical_page_library": len(canonical_library),
            "generated_page_library": len(generated_library),
        },
        "href_audits": {
            "processed_pdf_manifest_root": root_href_audit,
            "pages_dist_pdf_manifest": pages_dist_href_audit,
            "public_documents_public_root": public_docs_href_audit,
            "public_documents_pages_dist_root": pages_dist_public_docs_href_audit,
        },
        "issues": issues,
        "guardrails": [
            "This audit is read-only against hard-copy library inputs.",
            "No hard-copy source files, generated pages, pages-dist files, or publish scripts are modified.",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ISSUE_FIELDS)
        writer.writeheader()
        writer.writerows(issues)

    lines = [
        "# Hard-Copy Library Audit",
        "",
        f"- Status: `{report['status']}`",
        f"- Blockers: `{report['blocker_count']}`",
        f"- Warnings: `{report['warning_count']}`",
        f"- Master library records: `{report['counts']['master_csv_records']}`",
        f"- Public document records: `{report['counts']['public_documents']}`",
        f"- Processed PDF manifest records: `{report['counts']['processed_pdf_manifest']}`",
        f"- Pages-dist PDF manifest records: `{report['counts']['pages_dist_pdf_manifest']}`",
        f"- Generated page library records: `{report['counts']['generated_page_library']}`",
        "",
        "## Issue Counts",
        "",
    ]
    for code, count in sorted(code_counts.items()):
        lines.append(f"- `{code}`: `{count}`")
    lines.extend(["", "## Publish Readiness", ""])
    if report["status"] == "PUBLISH_SAFE":
        lines.append("The hard-copy library audit did not find publish blockers.")
    else:
        lines.append("The hard-copy library is not publish-safe until the ERROR issues are resolved.")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
