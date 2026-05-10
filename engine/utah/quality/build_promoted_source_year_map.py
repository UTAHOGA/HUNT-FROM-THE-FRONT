from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

INPUT_PROMOTED_QUALITY = REPO_ROOT / "data_model/quality/promoted_quality_sources.csv"
INPUT_PROMOTED_DRAW = REPO_ROOT / "data_model/quality/promoted_draw_sources.csv"
INPUT_AUDIT = REPO_ROOT / "data_model/quality/raw_pdf_inventory_audit.csv"

OUT_YEAR_MAP = REPO_ROOT / "data_model/quality/promoted_source_year_map.csv"
OUT_REPORT = REPO_ROOT / "data_model/quality/promoted_source_year_map_report.json"

OUTPUT_FIELDS = [
    "source_file",
    "source_sha256",
    "folder_year",
    "publish_year",
    "inferred_year",
    "reported_hunt_year_inferred",
    "model_target_year",
    "year_inference_method",
    "year_confidence",
    "source_class",
    "report_type",
    "quality_engine_use",
    "draw_engine_use",
    "extraction_priority",
    "extraction_strategy",
    "confidence",
    "reason",
]


YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
RANGE_SHORT_RE = re.compile(r"(?<!\d)(20\d{2})\s*[-_]\s*(\d{2})(?!\d)")
TWO_DIGIT_TOKEN_RE = re.compile(r"(?<!\d)(\d{2})(?!\d)")
HUNT_DB_FOLDER_YEAR_RE = re.compile(r"hunt_unit_database[/\\](20\d{2})(?:[/\\]|$)", re.IGNORECASE)
ANY_FOLDER_YEAR_RE = re.compile(r"[/\\](20\d{2})(?:[/\\]|$)")


@dataclass
class YearMapRow:
    source_file: str
    source_sha256: str
    folder_year: str
    publish_year: str
    inferred_year: str
    reported_hunt_year_inferred: str
    model_target_year: str
    year_inference_method: str
    year_confidence: str
    source_class: str
    report_type: str
    quality_engine_use: str
    draw_engine_use: str
    extraction_priority: str
    extraction_strategy: str
    confidence: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "folder_year": self.folder_year,
            "publish_year": self.publish_year,
            "inferred_year": self.inferred_year,
            "reported_hunt_year_inferred": self.reported_hunt_year_inferred,
            "model_target_year": self.model_target_year,
            "year_inference_method": self.year_inference_method,
            "year_confidence": self.year_confidence,
            "source_class": self.source_class,
            "report_type": self.report_type,
            "quality_engine_use": self.quality_engine_use,
            "draw_engine_use": self.draw_engine_use,
            "extraction_priority": self.extraction_priority,
            "extraction_strategy": self.extraction_strategy,
            "confidence": self.confidence,
            "reason": self.reason,
        }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def key(source_file: str, source_sha256: str) -> tuple[str, str]:
    return (source_file.strip(), source_sha256.strip())


def extract_folder_year(source_file: str) -> str:
    m = HUNT_DB_FOLDER_YEAR_RE.search(source_file)
    if m:
        return m.group(1)
    m_any = ANY_FOLDER_YEAR_RE.search(source_file)
    return m_any.group(1) if m_any else ""


def infer_from_filename(filename: str) -> tuple[str, str]:
    text = filename.replace("%20", " ")
    explicit_years = [int(y) for y in YEAR_RE.findall(text)]
    if explicit_years:
        return str(max(explicit_years)), "FILENAME"

    range_hits = RANGE_SHORT_RE.findall(text)
    if range_hits:
        expanded: list[int] = []
        for full_start, short_end in range_hits:
            start = int(full_start)
            century = (start // 100) * 100
            end = century + int(short_end)
            if end < start:
                end += 100
            expanded.extend([start, end])
        if expanded:
            return str(max(expanded)), "FILENAME"

    base = Path(text).name
    m_prefix = re.match(r"^(\d{2})(?=[^0-9])", base)
    if m_prefix:
        yy = int(m_prefix.group(1))
        if 0 <= yy <= 40:
            return str(2000 + yy), "FILENAME"

    tokens = [int(t) for t in TWO_DIGIT_TOKEN_RE.findall(base)]
    plausible = [2000 + t for t in tokens if 0 <= t <= 40]
    if plausible:
        return str(max(plausible)), "FILENAME"

    return "", "UNKNOWN"


def infer_year_fields(source_file: str, filename: str, inferred_year: str) -> tuple[str, str, str, str]:
    folder_year = extract_folder_year(source_file)
    publish_year = folder_year

    filename_year, filename_method = infer_from_filename(filename)
    reported_year = ""
    method = "UNKNOWN"
    confidence = "UNKNOWN"

    if filename_year:
        reported_year = filename_year
        method = filename_method
        confidence = "HIGH"
    elif inferred_year and inferred_year != folder_year:
        reported_year = inferred_year
        method = "TITLE_OR_CONTENT"
        confidence = "MEDIUM"
    elif folder_year:
        reported_year = folder_year
        method = "FOLDER_ONLY"
        confidence = "LOW"

    if method == "UNKNOWN":
        return folder_year, publish_year, "", "UNKNOWN"

    if not reported_year.isdigit():
        return folder_year, publish_year, "", "UNKNOWN"

    return folder_year, publish_year, reported_year, confidence


def model_target(reported_year: str) -> str:
    if not reported_year or not reported_year.isdigit():
        return ""
    return str(int(reported_year) + 1)


def normalize_yes_no_maybe(value: str) -> str:
    v = (value or "").strip().upper()
    if v in {"YES", "NO", "MAYBE"}:
        return v
    return "NO"


def build_rows() -> tuple[list[YearMapRow], dict[str, object]]:
    if not INPUT_PROMOTED_QUALITY.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_PROMOTED_QUALITY}")
    if not INPUT_PROMOTED_DRAW.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_PROMOTED_DRAW}")
    if not INPUT_AUDIT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_AUDIT}")

    promoted_quality = read_csv(INPUT_PROMOTED_QUALITY)
    promoted_draw = read_csv(INPUT_PROMOTED_DRAW)
    audit_rows = read_csv(INPUT_AUDIT)

    audit_index: dict[tuple[str, str], dict[str, str]] = {}
    for row in audit_rows:
        k = key(row.get("path", ""), row.get("sha256", ""))
        if not k[0] or not k[1]:
            continue
        audit_index[k] = row

    promoted_combined: dict[tuple[str, str], dict[str, str]] = {}
    for row in promoted_quality + promoted_draw:
        k = key(row.get("source_file", ""), row.get("source_sha256", ""))
        if not k[0] or not k[1]:
            continue
        if k not in promoted_combined:
            promoted_combined[k] = row

    output_rows: list[YearMapRow] = []
    year_conflict_count = 0
    year_unknown_count = 0
    quality_promoted_count = 0
    draw_promoted_count = 0
    missing_audit_rows: list[str] = []

    for k, p_row in sorted(promoted_combined.items(), key=lambda item: item[0][0].lower()):
        source_file, source_sha = k
        audit = audit_index.get(k)
        if not audit:
            missing_audit_rows.append(source_file)
            continue

        promotion_status = (audit.get("promotion_status") or "").strip().upper()
        quality_use = normalize_yes_no_maybe(audit.get("quality_engine_use", ""))
        draw_use = normalize_yes_no_maybe(audit.get("draw_engine_use", ""))

        if promotion_status != "PROMOTE":
            continue
        if quality_use != "YES" and draw_use != "YES":
            continue

        if quality_use == "YES":
            quality_promoted_count += 1
        if draw_use == "YES":
            draw_promoted_count += 1

        filename = (audit.get("filename") or Path(source_file).name).strip()
        inferred_year = (audit.get("inferred_year") or "").strip()
        source_class = (audit.get("source_class") or p_row.get("source_class") or "").strip()
        report_type = (audit.get("inferred_report_type") or p_row.get("report_type") or "").strip()
        reason = (audit.get("reason") or p_row.get("reason") or "").strip()

        folder_year, publish_year, reported_year, year_confidence = infer_year_fields(
            source_file=source_file,
            filename=filename,
            inferred_year=inferred_year,
        )

        if not reported_year:
            year_method = "UNKNOWN"
            year_confidence = "UNKNOWN"
            year_unknown_count += 1
            reason = f"{reason} | YEAR_UNKNOWN".strip(" |")
        else:
            # Re-evaluate method based on final selected source.
            filename_year, _ = infer_from_filename(filename)
            if filename_year and filename_year == reported_year:
                year_method = "FILENAME"
            elif folder_year and reported_year == folder_year:
                year_method = "FOLDER_ONLY"
            elif inferred_year and reported_year == inferred_year and inferred_year != folder_year:
                year_method = "TITLE_OR_CONTENT"
            else:
                year_method = "UNKNOWN"

            if folder_year and reported_year and folder_year != reported_year:
                year_method = "CONFLICT"
                if year_confidence == "UNKNOWN":
                    year_confidence = "MEDIUM"
                year_conflict_count += 1
                reason = f"{reason} | YEAR_CONFLICT".strip(" |")

        output_rows.append(
            YearMapRow(
                source_file=source_file,
                source_sha256=source_sha,
                folder_year=folder_year,
                publish_year=publish_year,
                inferred_year=inferred_year,
                reported_hunt_year_inferred=reported_year,
                model_target_year=model_target(reported_year),
                year_inference_method=year_method,
                year_confidence=year_confidence,
                source_class=source_class,
                report_type=report_type,
                quality_engine_use=quality_use,
                draw_engine_use=draw_use,
                extraction_priority=(p_row.get("extraction_priority") or "").strip(),
                extraction_strategy=(p_row.get("extraction_strategy") or "").strip(),
                confidence=(p_row.get("confidence") or "").strip(),
                reason=reason,
            )
        )

    counters = {
        "quality_promoted_rows": quality_promoted_count,
        "draw_promoted_rows": draw_promoted_count,
        "year_conflict_rows": year_conflict_count,
        "year_unknown_rows": year_unknown_count,
        "missing_audit_rows": len(missing_audit_rows),
        "total_output_rows": len(output_rows),
    }
    return output_rows, {"counters": counters, "missing_audit_sources": sorted(missing_audit_rows)}


def validate(rows: list[YearMapRow]) -> dict[str, object]:
    blockers: list[str] = []

    missing_source_file = sum(1 for r in rows if not r.source_file)
    missing_source_sha = sum(1 for r in rows if not r.source_sha256)
    missing_source_class = sum(1 for r in rows if not r.source_class)
    invalid_engine_flag = sum(
        1 for r in rows if r.quality_engine_use != "YES" and r.draw_engine_use != "YES"
    )

    folder_year_supported_rows = sum(1 for r in rows if bool(HUNT_DB_FOLDER_YEAR_RE.search(r.source_file)))
    missing_folder_year_supported = sum(
        1
        for r in rows
        if HUNT_DB_FOLDER_YEAR_RE.search(r.source_file) and not r.folder_year
    )

    bad_target_math = sum(
        1
        for r in rows
        if r.reported_hunt_year_inferred
        and (
            not r.model_target_year
            or not r.model_target_year.isdigit()
            or int(r.model_target_year) != int(r.reported_hunt_year_inferred) + 1
        )
    )

    if missing_source_file:
        blockers.append(f"Rows missing source_file: {missing_source_file}")
    if missing_source_sha:
        blockers.append(f"Rows missing source_sha256: {missing_source_sha}")
    if missing_source_class:
        blockers.append(f"Rows missing source_class: {missing_source_class}")
    if invalid_engine_flag:
        blockers.append(f"Rows without quality_engine_use=YES or draw_engine_use=YES: {invalid_engine_flag}")
    if missing_folder_year_supported:
        blockers.append(
            f"Rows missing folder_year where path supports it: {missing_folder_year_supported}/{folder_year_supported_rows}"
        )
    if bad_target_math:
        blockers.append(f"Rows with invalid model_target_year math: {bad_target_math}")

    year_method_counts = Counter(r.year_inference_method for r in rows)
    year_confidence_counts = Counter(r.year_confidence for r in rows)
    source_class_counts = Counter(r.source_class for r in rows)
    report_type_counts = Counter(r.report_type for r in rows)
    inferred_year_counts = Counter(r.inferred_year for r in rows if r.inferred_year)

    return {
        "checks": {
            "rows_total": len(rows),
            "missing_source_file": missing_source_file,
            "missing_source_sha256": missing_source_sha,
            "missing_source_class": missing_source_class,
            "invalid_engine_flag_rows": invalid_engine_flag,
            "folder_year_supported_rows": folder_year_supported_rows,
            "missing_folder_year_supported_rows": missing_folder_year_supported,
            "invalid_model_target_math_rows": bad_target_math,
            "year_conflict_rows": year_method_counts.get("CONFLICT", 0),
            "year_unknown_rows": year_method_counts.get("UNKNOWN", 0),
            "quality_promoted_rows": sum(1 for r in rows if r.quality_engine_use == "YES"),
            "draw_promoted_rows": sum(1 for r in rows if r.draw_engine_use == "YES"),
        },
        "counts": {
            "year_inference_method": dict(year_method_counts),
            "year_confidence": dict(year_confidence_counts),
            "source_class": dict(source_class_counts),
            "report_type": dict(report_type_counts),
            "inferred_year": dict(inferred_year_counts),
        },
        "blockers": blockers,
        "passed": not blockers,
    }


def write_outputs(rows: list[YearMapRow], report_data: dict[str, object], validation: dict[str, object]) -> None:
    OUT_YEAR_MAP.parent.mkdir(parents=True, exist_ok=True)
    with OUT_YEAR_MAP.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "promoted_quality_sources_csv": INPUT_PROMOTED_QUALITY.relative_to(REPO_ROOT).as_posix(),
            "promoted_draw_sources_csv": INPUT_PROMOTED_DRAW.relative_to(REPO_ROOT).as_posix(),
            "raw_pdf_inventory_audit_csv": INPUT_AUDIT.relative_to(REPO_ROOT).as_posix(),
        },
        "outputs": {
            "promoted_source_year_map_csv": OUT_YEAR_MAP.relative_to(REPO_ROOT).as_posix(),
            "promoted_source_year_map_report_json": OUT_REPORT.relative_to(REPO_ROOT).as_posix(),
        },
        "summary": report_data,
        "validation": validation,
    }
    with OUT_REPORT.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main() -> None:
    rows, report_data = build_rows()
    validation = validate(rows)
    write_outputs(rows, report_data, validation)

    print(f"Wrote {OUT_YEAR_MAP.relative_to(REPO_ROOT).as_posix()}")
    print(f"Wrote {OUT_REPORT.relative_to(REPO_ROOT).as_posix()}")
    print(
        "rows="
        f"{len(rows)} "
        f"quality={validation['checks']['quality_promoted_rows']} "
        f"draw={validation['checks']['draw_promoted_rows']} "
        f"year_conflict={validation['checks']['year_conflict_rows']} "
        f"year_unknown={validation['checks']['year_unknown_rows']} "
        f"passed={validation['passed']}"
    )


if __name__ == "__main__":
    main()
