from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROCESSED = REPO / "processed_data"

MB = 1024 * 1024
SMALL_CANONICAL_LIMIT = 5 * MB
LARGE_LIMIT = 25 * MB
VERY_LARGE_LIMIT = 100 * MB

ACTIONS = {
    "KEEP_IN_GITHUB",
    "KEEP_IN_GITHUB_SMALL_CANONICAL_DATA",
    "KEEP_IN_GITHUB_REBUILD_SCRIPT_OR_TEST",
    "KEEP_IN_GITHUB_DOC_OR_SCHEMA",
    "ONLINE_STATIC_SITE",
    "CLOUDFLARE_R2_RUNTIME_DATA",
    "CLOUDFLARE_R2_ARCHIVE_DATA",
    "LOCAL_ARCHIVE_ONLY",
    "DELETE_AFTER_BACKUP",
    "REVIEW_REQUIRED",
}

ROOT_STATIC_FILES = {
    "index.html",
    "research.html",
    "hunt-research.html",
    "verify.html",
    "hard-copy.html",
    "hard-data.html",
    "coverage.html",
    "builder.html",
    "vetting.html",
    "app.js",
    "config.js",
    "data.js",
    "boundary-resolver.js",
    "embed-mode.js",
    "event-handlers.js",
    "google-basemap.js",
    "header-layout.js",
    "hunt-research.js",
    "map-engine.js",
    "ownership-dock.js",
    "sentry-browser-init.js",
    "style.css",
    "ui.js",
    "uoga-analytics.js",
    "coverage.js",
    "manifest.json",
    "favicon.ico",
    "CNAME",
    ".nojekyll",
}

DOC_FILES = {
    "agents.md",
    "engine_rules_spec.md",
    "hybrid_ml_v1.md",
    "hybrid_ml_v1_rollout.md",
    "utah_draw_model_v1.md",
    "codex_utah_engine_build_prompt.md",
    "work_log.md",
    "readme.md",
    "harvest_and_report_year_rules.md",
    "locked_canonical_2026.md",
    "canonical json rules.md",
}

RUNTIME_DATA = {
    "processed_data/draw_reality_engine_predictive_v2.csv",
    "processed_data/ml_draw_predictions_v1.csv",
    "processed_data/point_ladder_view.csv",
    "processed_data/hunt_master_enriched.csv",
    "processed_data/hunt_unit_reference_linked.csv",
    "processed_data/harvest_results_all_years_long.csv",
    "processed_data/harvest_quality_features_all_years_by_hunt_code.csv",
}

GITHUB_ALWAYS_KEEP = {
    "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
}

LFS_RECOMMENDED_PATHS = {
    "processed_data/ml_draw_predictions_v1.csv",
    "processed_data/draw_reality_engine_predictive_v2.csv",
    "processed_data/draw_reality_engine_v2.csv",
    "processed_data/draw_reality_engine.csv",
    "processed_data/hunt_master_enriched.csv",
    "processed_data/point_ladder_view.csv",
    "processed_data/statewide_composite_boundaries_2026.geojson",
    "processed_data/composite_hunt_unit_mapping_2026.geojson",
    "processed_data/hunt_research_2026.json",
    "processed_data/harvest_results_all_years_long.csv",
    "processed_data/draw_system_coverage_report.csv",
}

SKIP_DIRS = {".git", "node_modules"}

GIT_TRACKED: set[str] | None = None
GIT_STATUS: dict[str, str] = {}


def git_command() -> list[str] | None:
    candidates = [
        ["git"],
        [r"C:\Program Files\Git\cmd\git.exe"],
        [r"C:\Program Files\Git\bin\git.exe"],
        [r"C:\Program Files (x86)\Git\cmd\git.exe"],
    ]
    for candidate in candidates:
        try:
            result = subprocess.run(
                [*candidate, "--version"],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
        except (FileNotFoundError, OSError):
            continue
        if result.returncode == 0:
            return candidate
    return None


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def run_git(args: list[str], input_text: str | None = None) -> tuple[bool, str]:
    command = git_command()
    if command is None:
        return False, ""
    try:
        result = subprocess.run(
            [*command, *args],
            cwd=REPO,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return False, ""
    if result.returncode not in (0, 1):
        return False, ""
    return True, result.stdout


def load_git_metadata() -> None:
    global GIT_TRACKED, GIT_STATUS
    ok, output = run_git(["ls-files"])
    GIT_TRACKED = set(output.splitlines()) if ok else None
    ok, output = run_git(["status", "--short"])
    if ok:
        for line in output.splitlines():
            if not line.strip():
                continue
            status = line[:2].strip() or "UNKNOWN"
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            GIT_STATUS[path.replace("\\", "/")] = status


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root, dirs, names in os.walk(REPO):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            files.append(root_path / name)
    return sorted(files, key=lambda p: rel(p).lower())


def is_under(path: str, prefix: str) -> bool:
    return path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")


def ext(path: str) -> str:
    name = Path(path).name
    if name.startswith(".") and name.count(".") == 1:
        return name.lower()
    return Path(path).suffix.lower()


def is_cache_or_temp(path: str) -> bool:
    lower = path.lower()
    name = Path(lower).name
    return (
        "/__pycache__/" in f"/{lower}"
        or "/.pytest_cache/" in f"/{lower}"
        or name.endswith(".pyc")
        or name.endswith(".pyo")
        or name.endswith(".tmp")
        or name.endswith(".bak")
        or ".bak-" in name
        or name == ".coverage"
    )


def likely_role(path: str, extension: str) -> str:
    if is_cache_or_temp(path):
        return "cache_or_temporary_file"
    if is_under(path, "engine") or is_under(path, "scripts") or is_under(path, "tests"):
        return "rebuild_script_or_test"
    if is_under(path, "docs") or is_under(path, "schemas") or Path(path).name.lower() in DOC_FILES:
        return "documentation_or_schema"
    if path in ROOT_STATIC_FILES or is_under(path, "assets"):
        return "online_static_site_asset"
    if path in RUNTIME_DATA or is_under(path, "data_model/runtime_drafts"):
        return "frontend_runtime_data"
    if is_under(path, "processed_data/boundaries") or is_under(path, "processed_data/hunt_research_2026_split"):
        return "generated_frontend_runtime_data"
    if extension in {".pdf", ".xlsx", ".xls"} and is_under(path, "pipeline/RAW"):
        return "raw_source_archive"
    if extension in {".zip", ".sqlite", ".db"}:
        return "archive_or_database_package"
    if is_under(path, "data_truth") and "/normalized/" in path:
        return "normalized_truth_data"
    if is_under(path, "processed_data"):
        return "processed_report_or_runtime_artifact"
    if is_under(path, "canonical") or is_under(path, "data"):
        return "canonical_or_site_data"
    return "unclear_project_file"


def duplicate_hint(path: str, by_basename: dict[str, list[dict[str, object]]], sha: str) -> tuple[bool, str]:
    name = Path(path).name.lower()
    peers = by_basename.get(name, [])
    if len(peers) <= 1:
        return False, ""
    different = [p for p in peers if p["sha256"] != sha]
    if different:
        return True, "DUPLICATE_BASENAME_DIFFERENT_HASH"
    return True, "DUPLICATE_BASENAME_SAME_HASH"


def classify(path: str, size: int, extension: str, sha: str, by_basename: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    lower = path.lower()
    name = Path(path).name
    name_lower = name.lower()
    role = likely_role(path, extension)
    notes: list[str] = []
    duplicate, duplicate_reason = duplicate_hint(path, by_basename, sha)

    action = "REVIEW_REQUIRED"
    reason = "ROLE_UNCLEAR"

    if is_cache_or_temp(path) or size == 0:
        action = "DELETE_AFTER_BACKUP"
        reason = "CACHE_TEMP_OR_EMPTY_ARTIFACT" if size else "ZERO_BYTE_BROKEN_ARTIFACT"
    elif path in ROOT_STATIC_FILES or is_under(path, "assets"):
        action = "ONLINE_STATIC_SITE"
        reason = "LIVE_WEBSITE_SHELL_OR_ASSET"
    elif is_under(path, "engine") or is_under(path, "scripts") or is_under(path, "tests"):
        action = "KEEP_IN_GITHUB_REBUILD_SCRIPT_OR_TEST"
        reason = "REBUILD_SCRIPT_OR_TEST"
    elif is_under(path, "docs") or is_under(path, "schemas") or name_lower in DOC_FILES:
        action = "KEEP_IN_GITHUB_DOC_OR_SCHEMA"
        reason = "DOC_OR_SCHEMA"
    elif path in GITHUB_ALWAYS_KEEP:
        action = "KEEP_IN_GITHUB_SMALL_CANONICAL_DATA"
        reason = "CURRENT_CANONICAL_DATABASE"
    elif path == "canonical/hunt-planner-2026.json":
        action = "ONLINE_STATIC_SITE"
        reason = "FRONTEND_CANONICAL_DATA_REFERENCE"
    elif path.startswith("generated/pages/") and extension == ".json":
        if size > SMALL_CANONICAL_LIMIT:
            action = "CLOUDFLARE_R2_RUNTIME_DATA"
            reason = "GITHUB_PAGES_SIZE_RISK"
        else:
            action = "ONLINE_STATIC_SITE"
            reason = "GENERATED_PAGE_DATA"
    elif (
        path in RUNTIME_DATA
        or is_under(path, "processed_data/boundaries")
        or is_under(path, "processed_data/hunt_research_2026_split")
        or (is_under(path, "data_model/runtime_drafts") and extension in {".csv", ".json"})
    ):
        action = "CLOUDFLARE_R2_RUNTIME_DATA"
        reason = "FRONTEND_FETCHED_DATA" if path in RUNTIME_DATA else "LARGE_RUNTIME_DATA"
    elif extension in {".zip"}:
        action = "CLOUDFLARE_R2_ARCHIVE_DATA"
        reason = "PACKAGE_ARCHIVE_NOT_GITHUB"
    elif extension in {".sqlite", ".db"}:
        action = "CLOUDFLARE_R2_ARCHIVE_DATA"
        reason = "SQLITE_ARCHIVE_PRIVATE"
    elif extension in {".pdf", ".xlsx", ".xls"} and is_under(path, "pipeline/RAW"):
        action = "LOCAL_ARCHIVE_ONLY"
        reason = "RAW_SOURCE_ARCHIVE"
    elif (is_under(path, "data_truth") and ("/raw_packages/" in path or "/sqlite/" in path)) or size > VERY_LARGE_LIMIT:
        action = "CLOUDFLARE_R2_ARCHIVE_DATA"
        reason = "LARGE_SOURCE_ARCHIVE"
    elif size > LARGE_LIMIT and extension in {".csv", ".json", ".geojson"}:
        if is_under(path, "processed_data") or is_under(path, "pages-dist") or is_under(path, "generated"):
            action = "CLOUDFLARE_R2_RUNTIME_DATA"
            reason = "LARGE_RUNTIME_DATA"
        else:
            action = "CLOUDFLARE_R2_ARCHIVE_DATA"
            reason = "LARGE_ARCHIVE_DATA"
    elif (
        is_under(path, "data_truth")
        and "/normalized/" in path
        and extension in {".csv", ".json", ".md"}
        and size < SMALL_CANONICAL_LIMIT
    ):
        action = "KEEP_IN_GITHUB_SMALL_CANONICAL_DATA"
        reason = "NORMALIZED_TRUTH_LAYER"
    elif is_under(path, "data_model") and Path(path).name.startswith("promoted_") and size < SMALL_CANONICAL_LIMIT:
        action = "KEEP_IN_GITHUB_SMALL_CANONICAL_DATA"
        reason = "PROMOTED_MODEL_INPUT"
    elif is_under(path, "canonical") and extension == ".json" and size < SMALL_CANONICAL_LIMIT:
        action = "KEEP_IN_GITHUB_SMALL_CANONICAL_DATA"
        reason = "SMALL_CANONICAL_JSON"
    elif is_under(path, "processed_data") and (
        name_lower.endswith("_summary.json")
        or name_lower.endswith("_report.json")
        or name_lower.endswith("_audit.json")
        or name_lower.endswith("_summary.md")
        or name_lower.endswith("_report.md")
        or name_lower.endswith("_audit.md")
    ) and size < SMALL_CANONICAL_LIMIT:
        action = "KEEP_IN_GITHUB_SMALL_CANONICAL_DATA"
        reason = "SMALL_AUDIT_OR_SUMMARY"
    elif is_under(path, "pages-dist"):
        action = "ONLINE_STATIC_SITE" if size <= LARGE_LIMIT else "CLOUDFLARE_R2_RUNTIME_DATA"
        reason = "PAGES_DIST_BUILD_ARTIFACT" if size <= LARGE_LIMIT else "GITHUB_PAGES_SIZE_RISK"
    elif duplicate and " (1)" in name_lower:
        action = "DELETE_AFTER_BACKUP"
        reason = duplicate_reason or "DUPLICATE_COPY"
    elif size > LARGE_LIMIT:
        action = "REVIEW_REQUIRED"
        reason = "LARGE_ROLE_UNCLEAR"
    elif extension in {"", ".lnk"}:
        action = "REVIEW_REQUIRED"
        reason = "UNKNOWN_EXTENSION_OR_SHORTCUT"
    elif size < SMALL_CANONICAL_LIMIT and extension in {".js", ".html", ".css", ".json", ".md", ".csv", ".txt", ".ps1", ".bat", ".sh", ".yml", ".yaml"}:
        action = "KEEP_IN_GITHUB"
        reason = "SMALL_PROJECT_FILE"

    if size > VERY_LARGE_LIMIT and action.startswith("KEEP_IN_GITHUB"):
        action = "REVIEW_REQUIRED"
        reason = "TRACKED_OVER_100MB_REVIEW"
    if duplicate and action not in {"DELETE_AFTER_BACKUP", "LOCAL_ARCHIVE_ONLY"}:
        notes.append(duplicate_reason)

    online_needed = action == "ONLINE_STATIC_SITE"
    cloudflare_needed = action in {"CLOUDFLARE_R2_RUNTIME_DATA", "CLOUDFLARE_R2_ARCHIVE_DATA"}
    github_needed = action.startswith("KEEP_IN_GITHUB") or action == "ONLINE_STATIC_SITE"
    local_archive_needed = action in {"LOCAL_ARCHIVE_ONLY", "CLOUDFLARE_R2_ARCHIVE_DATA"}
    delete_candidate = action == "DELETE_AFTER_BACKUP"

    if action == "CLOUDFLARE_R2_RUNTIME_DATA" and size > LARGE_LIMIT:
        notes.append("Serve from R2 to avoid GitHub Pages file-size risk.")
    if path in LFS_RECOMMENDED_PATHS or is_under(path, "processed_data/boundaries") or is_under(path, "processed_data/hunt_research_2026_split"):
        notes.append("Git LFS recommended for repository storage.")
    if action == "LOCAL_ARCHIVE_ONLY":
        notes.append("Keep outside web/runtime; do not serve online.")
    if "DATABASE.csv" in path and action == "DELETE_AFTER_BACKUP":
        action = "REVIEW_REQUIRED"
        reason = "DATABASE_NEVER_AUTO_DELETE"

    return {
        "likely_file_role": role,
        "recommended_action": action,
        "reason_code": reason,
        "online_needed": str(online_needed).upper(),
        "cloudflare_needed": str(cloudflare_needed).upper(),
        "github_needed": str(github_needed).upper(),
        "local_archive_needed": str(local_archive_needed).upper(),
        "delete_candidate": str(delete_candidate).upper(),
        "notes": " | ".join(notes),
    }


def r2_key(path: str, action: str) -> str:
    name = Path(path).name
    frontend_live_keys = {
        "processed_data/draw_reality_engine_predictive_v2.csv": "processed_data/draw_reality_engine_predictive_v2.csv",
        "processed_data/draw_reality_engine_v2.csv": "processed_data/draw_reality_engine_v2.csv",
        "processed_data/point_ladder_view.csv": "point_ladder_view.csv",
        "processed_data/hunt_master_enriched.csv": "hunt_master_enriched.csv",
        "processed_data/hunt_unit_reference_linked.csv": "hunt_unit_reference_linked.csv",
        "processed_data/composite_hunt_unit_mapping_2026.geojson": "processed_data/composite_hunt_unit_mapping_2026.geojson",
        "processed_data/statewide_composite_boundaries_2026.geojson": "processed_data/statewide_composite_boundaries_2026.geojson",
    }
    if path in frontend_live_keys:
        return frontend_live_keys[path]
    if path.startswith("processed_data/boundaries/"):
        return path
    if path.startswith("processed_data/hunt_research_2026_split/"):
        return path
    if action == "CLOUDFLARE_R2_RUNTIME_DATA":
        if path.startswith("processed_data/harvest_") or path.startswith("data_model/harvest_quality/"):
            return f"runtime/harvest/{name}"
        return f"runtime/2026/{name}"
    if path.endswith(".zip"):
        return f"archive/packages/{name}"
    if "report" in name.lower() or "audit" in name.lower():
        return f"archive/reports/{name}"
    return f"archive/source/{path}"


def content_type(path: str) -> str:
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


def cache_policy(path: str, action: str) -> str:
    if action == "CLOUDFLARE_R2_RUNTIME_DATA":
        if any(token in path for token in ("mixed_predictive_engine_2026", "runtime_drafts")):
            return "public, max-age=31536000, immutable"
        return "public, max-age=300"
    if path.endswith((".pdf", ".zip", ".sqlite", ".db")):
        return "private/restricted archive"
    return "public, max-age=31536000, immutable"


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    load_git_metadata()
    paths = iter_files()
    pre_rows: list[dict[str, object]] = []
    by_basename: dict[str, list[dict[str, object]]] = defaultdict(list)
    for path in paths:
        relative = rel(path)
        try:
            stat = path.stat()
            sha = sha256_file(path)
        except OSError:
            continue
        item = {"path": relative, "size_bytes": stat.st_size, "sha256": sha}
        pre_rows.append(item)
        by_basename[Path(relative).name.lower()].append(item)

    rows: list[dict[str, object]] = []
    for item in pre_rows:
        path = str(item["path"])
        size = int(item["size_bytes"])
        extension = ext(path)
        git_tracked = "UNKNOWN" if GIT_TRACKED is None else str(path in GIT_TRACKED).upper()
        modified = GIT_STATUS.get(path, "UNKNOWN" if GIT_TRACKED is None else "")
        classification = classify(path, size, extension, str(item["sha256"]), by_basename)
        row = {
            "path": path,
            "directory": str(Path(path).parent).replace("\\", "/") if str(Path(path).parent) != "." else "",
            "file_name": Path(path).name,
            "extension": extension,
            "size_bytes": size,
            "size_mb": f"{size / MB:.3f}",
            "git_tracked": git_tracked,
            "modified_status": modified,
            "sha256": item["sha256"],
            **classification,
        }
        rows.append(row)

    fields = [
        "path",
        "directory",
        "file_name",
        "extension",
        "size_bytes",
        "size_mb",
        "git_tracked",
        "modified_status",
        "sha256",
        "likely_file_role",
        "recommended_action",
        "reason_code",
        "online_needed",
        "cloudflare_needed",
        "github_needed",
        "local_archive_needed",
        "delete_candidate",
        "notes",
    ]

    write_csv(PROCESSED / "repo_file_retention_audit.csv", rows, fields)

    action_counts = Counter(str(row["recommended_action"]) for row in rows)
    top_dirs: dict[str, dict[str, object]] = {}
    for row in rows:
        top = str(row["path"]).split("/", 1)[0]
        entry = top_dirs.setdefault(top, {"directory": top, "file_count": 0, "size_bytes": 0})
        entry["file_count"] = int(entry["file_count"]) + 1
        entry["size_bytes"] = int(entry["size_bytes"]) + int(row["size_bytes"])
    summary_rows = []
    for entry in top_dirs.values():
        entry["size_mb"] = f"{int(entry['size_bytes']) / MB:.3f}"
        summary_rows.append(entry)
    summary_rows.sort(key=lambda r: int(r["size_bytes"]), reverse=True)
    write_csv(
        PROCESSED / "repo_file_retention_summary_by_directory.csv",
        summary_rows,
        ["directory", "file_count", "size_bytes", "size_mb"],
    )

    cloudflare_rows = []
    github_rows = []
    delete_rows = []
    review_rows = []
    for row in rows:
        action = str(row["recommended_action"])
        path = str(row["path"])
        if action in {"CLOUDFLARE_R2_RUNTIME_DATA", "CLOUDFLARE_R2_ARCHIVE_DATA"}:
            cloudflare_rows.append(
                {
                    "path": path,
                    "suggested_r2_key": r2_key(path, action),
                    "cache_policy": cache_policy(path, action),
                    "content_type": content_type(path),
                    "size_bytes": row["size_bytes"],
                    "reason_code": row["reason_code"],
                    "frontend_referenced": str(path in RUNTIME_DATA or action == "CLOUDFLARE_R2_RUNTIME_DATA").upper(),
                    "upload_required": "TRUE",
                }
            )
        if action.startswith("KEEP_IN_GITHUB") or action == "ONLINE_STATIC_SITE":
            github_rows.append(
                {
                    "path": path,
                    "reason_code": row["reason_code"],
                    "size_bytes": row["size_bytes"],
                    "must_track": "TRUE",
                    "rebuild_critical": str(action in {"KEEP_IN_GITHUB_REBUILD_SCRIPT_OR_TEST", "KEEP_IN_GITHUB_SMALL_CANONICAL_DATA"}).upper(),
                    "online_static": str(action == "ONLINE_STATIC_SITE").upper(),
                    "notes": row["notes"],
                }
            )
        if action == "DELETE_AFTER_BACKUP":
            delete_rows.append(
                {
                    "path": path,
                    "reason_code": row["reason_code"],
                    "size_bytes": row["size_bytes"],
                    "backup_required": "TRUE",
                    "safe_delete_after": "manual backup verification",
                    "duplicate_of": "",
                    "notes": row["notes"],
                }
            )
        if action == "REVIEW_REQUIRED":
            review_rows.append(row)

    write_csv(
        PROCESSED / "repo_file_retention_cloudflare_manifest.csv",
        cloudflare_rows,
        ["path", "suggested_r2_key", "cache_policy", "content_type", "size_bytes", "reason_code", "frontend_referenced", "upload_required"],
    )
    write_csv(
        PROCESSED / "repo_file_retention_github_keep_manifest.csv",
        github_rows,
        ["path", "reason_code", "size_bytes", "must_track", "rebuild_critical", "online_static", "notes"],
    )
    write_csv(
        PROCESSED / "repo_file_retention_delete_after_backup_manifest.csv",
        delete_rows,
        ["path", "reason_code", "size_bytes", "backup_required", "safe_delete_after", "duplicate_of", "notes"],
    )
    write_csv(PROCESSED / "repo_file_retention_review_required_manifest.csv", review_rows, fields)

    total_size = sum(int(row["size_bytes"]) for row in rows)
    largest = sorted(rows, key=lambda r: int(r["size_bytes"]), reverse=True)
    tracked_over_25 = [r for r in rows if r["git_tracked"] == "TRUE" and int(r["size_bytes"]) > LARGE_LIMIT]
    tracked_over_100 = [r for r in rows if r["git_tracked"] == "TRUE" and int(r["size_bytes"]) > VERY_LARGE_LIMIT]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO),
        "total_repo_file_count": len(rows),
        "total_repo_size_bytes": total_size,
        "total_repo_size_mb": round(total_size / MB, 3),
        "git_available": GIT_TRACKED is not None,
        "action_counts": dict(sorted(action_counts.items())),
        "tracked_files_over_25mb": len(tracked_over_25),
        "tracked_files_over_100mb": len(tracked_over_100),
        "largest_100_files": [
            {
                "path": r["path"],
                "size_bytes": r["size_bytes"],
                "size_mb": r["size_mb"],
                "recommended_action": r["recommended_action"],
                "reason_code": r["reason_code"],
                "git_tracked": r["git_tracked"],
            }
            for r in largest[:100]
        ],
        "outputs": {
            "audit_csv": "processed_data/repo_file_retention_audit.csv",
            "cloudflare_manifest_csv": "processed_data/repo_file_retention_cloudflare_manifest.csv",
            "github_keep_manifest_csv": "processed_data/repo_file_retention_github_keep_manifest.csv",
            "delete_after_backup_manifest_csv": "processed_data/repo_file_retention_delete_after_backup_manifest.csv",
            "review_required_manifest_csv": "processed_data/repo_file_retention_review_required_manifest.csv",
        },
    }
    (PROCESSED / "repo_file_retention_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    ignore_recs = [
        "__pycache__/",
        ".pytest_cache/",
        "*.pyc",
        "*.tmp",
        "*.bak",
        "*.sqlite",
        "*.db",
        "*.zip",
        "data_truth/**/raw_packages/",
        "data_truth/**/sqlite/",
        "data_model/runtime_drafts/*.csv",
        "pipeline/RAW/**/*.pdf",
        "pipeline/RAW/**/*.xlsx",
        "pages-dist/",
        "generated/pages/*.json",
    ]
    lfs_recs = [
        "processed_data/point_ladder_view.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/boundaries/** filter=lfs diff=lfs merge=lfs -text",
        "processed_data/hunt_research_2026_split/** filter=lfs diff=lfs merge=lfs -text",
        "processed_data/ml_draw_predictions_v1.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/draw_reality_engine_predictive_v2.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/draw_reality_engine_v2.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/draw_reality_engine.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/hunt_master_enriched.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/statewide_composite_boundaries_2026.geojson filter=lfs diff=lfs merge=lfs -text",
        "processed_data/composite_hunt_unit_mapping_2026.geojson filter=lfs diff=lfs merge=lfs -text",
        "processed_data/hunt_research_2026.json filter=lfs diff=lfs merge=lfs -text",
        "processed_data/harvest_results_all_years_long.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/draw_system_coverage_report.csv filter=lfs diff=lfs merge=lfs -text",
        "processed_data/*.sqlite filter=lfs diff=lfs merge=lfs -text",
        "data_model/runtime_drafts/*.csv filter=lfs diff=lfs merge=lfs -text",
    ]
    md = [
        "# Repository File Retention Audit",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Total repo file count: `{len(rows)}`",
        f"- Total repo size: `{round(total_size / MB, 3)} MB`",
        f"- Git metadata available: `{report['git_available']}`",
        "",
        "## Action Counts",
        "",
    ]
    for action in sorted(ACTIONS):
        md.append(f"- `{action}`: `{action_counts.get(action, 0)}`")
    md.extend(["", "## Size By Top-Level Directory", ""])
    for row in summary_rows:
        md.append(f"- `{row['directory']}`: `{row['file_count']}` files, `{row['size_mb']} MB`")
    md.extend(["", "## Largest 100 Files", ""])
    for r in largest[:100]:
        md.append(f"- `{r['path']}`: `{r['size_mb']} MB`, `{r['recommended_action']}`, `{r['reason_code']}`")
    md.extend(["", "## Tracked Files Over 25 MB", ""])
    if tracked_over_25:
        for r in tracked_over_25:
            md.append(f"- `{r['path']}`: `{r['size_mb']} MB`")
    else:
        md.append("- None detected, or git metadata unavailable.")
    md.extend(["", "## Tracked Files Over 100 MB", ""])
    if tracked_over_100:
        for r in tracked_over_100:
            md.append(f"- `{r['path']}`: `{r['size_mb']} MB`")
    else:
        md.append("- None detected, or git metadata unavailable.")
    md.extend(["", "## Files Recommended For Cloudflare R2", ""])
    for r in cloudflare_rows[:200]:
        md.append(f"- `{r['path']}` -> `{r['suggested_r2_key']}`")
    md.extend(["", "## Files Recommended For GitHub", ""])
    for r in github_rows[:200]:
        md.append(f"- `{r['path']}`: `{r['reason_code']}`")
    md.extend(["", "## Files Recommended For Local Archive", ""])
    for r in [row for row in rows if row["recommended_action"] == "LOCAL_ARCHIVE_ONLY"][:200]:
        md.append(f"- `{r['path']}`: `{r['reason_code']}`")
    md.extend(["", "## Files Recommended Delete-After-Backup", ""])
    for r in delete_rows[:200]:
        md.append(f"- `{r['path']}`: `{r['reason_code']}`")
    md.extend(["", "## Review-Required Files", ""])
    for r in review_rows[:200]:
        md.append(f"- `{r['path']}`: `{r['size_mb']} MB, `{r['reason_code']}`")
    md.extend(
        [
            "",
            "## Exact Commands To Create Smaller ZIPs By Category",
            "",
            "```powershell",
            "Compress-Archive -Path processed_data\\repo_file_retention_cloudflare_manifest.csv -DestinationPath local_only\\cloudflare_manifest_review.zip -Force",
            "Compress-Archive -Path processed_data\\repo_file_retention_github_keep_manifest.csv -DestinationPath local_only\\github_keep_manifest_review.zip -Force",
            "Compress-Archive -Path processed_data\\repo_file_retention_delete_after_backup_manifest.csv -DestinationPath local_only\\delete_after_backup_manifest_review.zip -Force",
            "```",
            "",
            "## Exact Commands To Upload Cloudflare Manifest Later",
            "",
            "```powershell",
            "wrangler r2 object put <bucket>/runtime/2026/<filename> --file <local-file>",
            "wrangler r2 object put <bucket>/runtime/harvest/<filename> --file <local-file>",
            "wrangler r2 object put <bucket>/archive/source/<relative-path> --file <local-file>",
            "```",
            "",
            "## Exact Proposed .gitignore Additions",
            "",
            "Do not apply automatically until tracked-file impact is reviewed.",
            "",
            "```gitignore",
            *ignore_recs,
            "```",
            "",
            "## Exact Proposed Git LFS Additions",
            "",
            "Current `.gitattributes` should be reviewed before applying these. These are recommendations only.",
            "",
            "```gitattributes",
            *lfs_recs,
            "```",
            "",
            "## Notes",
            "",
            "- No files were deleted by this audit.",
            "- `pipeline/RAW` source documents are archive inputs, not online static-site files.",
            "- Runtime CSV/JSON files are retained as valuable data; large ones are recommended for Cloudflare R2 or Git LFS rather than deletion.",
            "- GitHub Pages skipped oversized prediction/runtime CSVs during `pages-dist` build; those files need Cloudflare R2 or LFS-backed publishing before any cleanup is acted on.",
        ]
    )
    (PROCESSED / "repo_file_retention_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
