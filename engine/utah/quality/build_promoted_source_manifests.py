from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_AUDIT = REPO_ROOT / "data_model/quality/raw_pdf_inventory_audit.csv"

OUT_QUALITY = REPO_ROOT / "data_model/quality/promoted_quality_sources.csv"
OUT_DRAW = REPO_ROOT / "data_model/quality/promoted_draw_sources.csv"
OUT_SUMMARY = REPO_ROOT / "data_model/quality/promoted_source_summary.json"

EXPECTED_QUALITY_ROWS = 253
EXPECTED_DRAW_ROWS = 204

OUTPUT_FIELDS = [
    "source_file",
    "source_sha256",
    "inferred_species",
    "inferred_year",
    "source_class",
    "report_type",
    "file_size_bytes",
    "page_count",
    "extraction_priority",
    "extraction_strategy",
    "confidence",
    "reason",
]


@dataclass
class ManifestRow:
    source_file: str
    source_sha256: str
    inferred_species: str
    inferred_year: str
    source_class: str
    report_type: str
    file_size_bytes: str
    page_count: str
    extraction_priority: str
    extraction_strategy: str
    confidence: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "inferred_species": self.inferred_species,
            "inferred_year": self.inferred_year,
            "source_class": self.source_class,
            "report_type": self.report_type,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "extraction_priority": self.extraction_priority,
            "extraction_strategy": self.extraction_strategy,
            "confidence": self.confidence,
            "reason": self.reason,
        }


def is_known_year(year: str) -> bool:
    if not year.isdigit() or len(year) != 4:
        return False
    y = int(year)
    return 2010 <= y <= 2035


def is_pdf(path: str) -> bool:
    return path.lower().endswith(".pdf")


def looks_tabular(path: str) -> bool:
    low = path.lower()
    return low.endswith(".csv") or low.endswith(".tsv") or low.endswith(".xlsx") or low.endswith(".xls")


def strategy_for_row(source_class: str, report_type: str, source_file: str) -> str:
    if report_type in {"winter_trend", "winter_population", "preseason_classification", "average_age"}:
        return "wide_year_table"
    if source_class in {"draw_results", "harvest_results", "permit_data"}:
        if looks_tabular(source_file):
            return "structured_table"
        if is_pdf(source_file):
            return "structured_table"
        return "text_parse"
    if is_pdf(source_file):
        return "text_parse"
    return "manual_review_needed"


def confidence_for_row(
    source_class: str,
    report_type: str,
    inferred_year: str,
    inferred_species: str,
    extraction_strategy: str,
) -> str:
    clear_core = source_class != "unknown" and report_type != "unknown" and is_known_year(inferred_year)
    weak_fields = 0
    if source_class == "unknown":
        weak_fields += 1
    if report_type == "unknown":
        weak_fields += 1
    if not is_known_year(inferred_year):
        weak_fields += 1
    if not inferred_species or inferred_species == "Unknown":
        weak_fields += 1

    if extraction_strategy == "manual_review_needed":
        return "LOW"
    if clear_core and weak_fields <= 1:
        return "HIGH"
    if weak_fields <= 2:
        return "MEDIUM"
    return "LOW"


def priority_for_row(
    source_class: str,
    report_type: str,
    inferred_year: str,
    source_file: str,
    page_count: str,
    extraction_status: str,
    extraction_strategy: str,
) -> str:
    known_core = source_class != "unknown" and report_type != "unknown" and is_known_year(inferred_year)
    readable_pdf = is_pdf(source_file) and page_count.isdigit() and int(page_count) > 0 and extraction_status != "raw_pdf_page_count_unavailable"
    structured_non_pdf = (not is_pdf(source_file)) and looks_tabular(source_file)

    if known_core and extraction_strategy != "manual_review_needed" and (readable_pdf or structured_non_pdf):
        return "HIGH"
    if extraction_strategy in {"text_parse", "manual_review_needed"}:
        return "LOW"
    return "MEDIUM"


def build_manifest_rows(filtered_rows: list[dict[str, str]]) -> list[ManifestRow]:
    out: list[ManifestRow] = []
    for row in filtered_rows:
        source_file = (row.get("path") or "").strip()
        source_sha = (row.get("sha256") or "").strip()
        inferred_species = (row.get("inferred_species") or "").strip()
        inferred_year = (row.get("inferred_year") or "").strip()
        source_class = (row.get("source_class") or "").strip()
        report_type = (row.get("inferred_report_type") or "").strip()
        file_size = (row.get("file_size_bytes") or "").strip()
        page_count = (row.get("page_count") or "").strip()
        extraction_status = (row.get("extraction_status") or "").strip()
        base_reason = (row.get("reason") or "").strip()

        strategy = strategy_for_row(source_class, report_type, source_file)
        confidence = confidence_for_row(
            source_class=source_class,
            report_type=report_type,
            inferred_year=inferred_year,
            inferred_species=inferred_species,
            extraction_strategy=strategy,
        )
        priority = priority_for_row(
            source_class=source_class,
            report_type=report_type,
            inferred_year=inferred_year,
            source_file=source_file,
            page_count=page_count,
            extraction_status=extraction_status,
            extraction_strategy=strategy,
        )

        reason = base_reason
        if reason:
            reason = f"{reason} | Step1C strategy={strategy}; priority={priority}; confidence={confidence}"
        else:
            reason = f"Step1C strategy={strategy}; priority={priority}; confidence={confidence}"

        out.append(
            ManifestRow(
                source_file=source_file,
                source_sha256=source_sha,
                inferred_species=inferred_species,
                inferred_year=inferred_year,
                source_class=source_class,
                report_type=report_type,
                file_size_bytes=file_size,
                page_count=page_count,
                extraction_priority=priority,
                extraction_strategy=strategy,
                confidence=confidence,
                reason=reason,
            )
        )
    return out


def write_manifest(path: Path, rows: list[ManifestRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def validate_manifest(
    source_rows: list[dict[str, str]],
    manifest_rows: list[ManifestRow],
    *,
    expected_count: int,
    require_engine_flag: str,
    engine_column_name: str,
) -> dict[str, object]:
    checks: dict[str, object] = {}
    blockers: list[str] = []

    checks["row_count_actual"] = len(manifest_rows)
    checks["row_count_expected"] = expected_count
    checks["row_count_matches_expected"] = len(manifest_rows) == expected_count
    if not checks["row_count_matches_expected"]:
        blockers.append(f"Row count mismatch: expected {expected_count}, got {len(manifest_rows)}")

    non_promote = [
        r
        for r in source_rows
        if r.get("promotion_status") != "PROMOTE"
    ]
    checks["source_non_promote_rows_after_filter"] = len(non_promote)
    checks["only_promote_rows_used"] = len(non_promote) == 0
    if non_promote:
        blockers.append(f"Found {len(non_promote)} non-PROMOTE rows in filtered source set")

    wrong_engine = [
        r
        for r in source_rows
        if r.get(engine_column_name) != require_engine_flag
    ]
    checks[f"{engine_column_name}_wrong_rows_after_filter"] = len(wrong_engine)
    checks[f"only_{require_engine_flag}_{engine_column_name}"] = len(wrong_engine) == 0
    if wrong_engine:
        blockers.append(f"Found {len(wrong_engine)} rows with wrong {engine_column_name} value")

    key_counts = Counter((r.source_file, r.source_sha256) for r in manifest_rows)
    duplicates = [k for k, c in key_counts.items() if c > 1]
    checks["duplicate_source_rows_count"] = len(duplicates)
    checks["no_duplicate_source_rows"] = len(duplicates) == 0
    if duplicates:
        blockers.append(f"Found duplicate source rows: {len(duplicates)}")

    missing_required = [
        r
        for r in manifest_rows
        if not r.source_file or not r.source_sha256
    ]
    checks["rows_missing_source_file_or_sha256"] = len(missing_required)
    checks["all_rows_have_source_file_and_sha256"] = len(missing_required) == 0
    if missing_required:
        blockers.append(f"Found {len(missing_required)} rows missing source_file or source_sha256")

    checks["blockers"] = blockers
    checks["passed"] = not blockers
    return checks


def main() -> None:
    if not INPUT_AUDIT.exists():
        raise FileNotFoundError(f"Missing input audit file: {INPUT_AUDIT}")

    with INPUT_AUDIT.open("r", encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.DictReader(f))

    quality_source = [
        r
        for r in all_rows
        if r.get("promotion_status") == "PROMOTE" and r.get("quality_engine_use") == "YES"
    ]
    draw_source = [
        r
        for r in all_rows
        if r.get("promotion_status") == "PROMOTE" and r.get("draw_engine_use") == "YES"
    ]

    quality_manifest = build_manifest_rows(quality_source)
    draw_manifest = build_manifest_rows(draw_source)

    write_manifest(OUT_QUALITY, quality_manifest)
    write_manifest(OUT_DRAW, draw_manifest)

    quality_validation = validate_manifest(
        source_rows=quality_source,
        manifest_rows=quality_manifest,
        expected_count=EXPECTED_QUALITY_ROWS,
        require_engine_flag="YES",
        engine_column_name="quality_engine_use",
    )
    draw_validation = validate_manifest(
        source_rows=draw_source,
        manifest_rows=draw_manifest,
        expected_count=EXPECTED_DRAW_ROWS,
        require_engine_flag="YES",
        engine_column_name="draw_engine_use",
    )

    blockers = []
    blockers.extend([f"quality: {b}" for b in quality_validation["blockers"]])  # type: ignore[index]
    blockers.extend([f"draw: {b}" for b in draw_validation["blockers"]])  # type: ignore[index]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_audit_file": INPUT_AUDIT.relative_to(REPO_ROOT).as_posix(),
        "outputs": {
            "promoted_quality_sources_csv": OUT_QUALITY.relative_to(REPO_ROOT).as_posix(),
            "promoted_draw_sources_csv": OUT_DRAW.relative_to(REPO_ROOT).as_posix(),
            "promoted_source_summary_json": OUT_SUMMARY.relative_to(REPO_ROOT).as_posix(),
        },
        "counts": {
            "quality_manifest_rows": len(quality_manifest),
            "draw_manifest_rows": len(draw_manifest),
            "expected_quality_rows": EXPECTED_QUALITY_ROWS,
            "expected_draw_rows": EXPECTED_DRAW_ROWS,
        },
        "validation": {
            "quality": quality_validation,
            "draw": draw_validation,
            "all_checks_passed": not blockers,
        },
        "promotion_blockers": blockers,
        "extraction_priority_counts": {
            "quality": dict(Counter(r.extraction_priority for r in quality_manifest)),
            "draw": dict(Counter(r.extraction_priority for r in draw_manifest)),
        },
        "extraction_strategy_counts": {
            "quality": dict(Counter(r.extraction_strategy for r in quality_manifest)),
            "draw": dict(Counter(r.extraction_strategy for r in draw_manifest)),
        },
        "confidence_counts": {
            "quality": dict(Counter(r.confidence for r in quality_manifest)),
            "draw": dict(Counter(r.confidence for r in draw_manifest)),
        },
    }

    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SUMMARY.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {OUT_QUALITY.relative_to(REPO_ROOT).as_posix()}")
    print(f"Wrote {OUT_DRAW.relative_to(REPO_ROOT).as_posix()}")
    print(f"Wrote {OUT_SUMMARY.relative_to(REPO_ROOT).as_posix()}")
    print(
        f"quality_rows={len(quality_manifest)} draw_rows={len(draw_manifest)} "
        f"all_checks_passed={summary['validation']['all_checks_passed']}"
    )


if __name__ == "__main__":
    main()
