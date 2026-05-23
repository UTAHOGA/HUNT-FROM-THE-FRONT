"""Build cumulative harvest truth databases from available yearly harvest packages."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUT_TRUTH = ROOT / "data_truth" / "harvest_results_truth" / "normalized"
OUT_PROCESSED = ROOT / "processed_data"
OUT_MODEL = ROOT / "data_model" / "harvest_quality"
OUT_OVERLAY = ROOT / "data_model" / "permit_overlays"
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
HARVEST_ROOT = ROOT / "pipeline" / "RAW" / "hunt_unit_database"
SOURCE_BUNDLE_ROOT = ROOT / "data_truth" / "harvest_results_truth" / "source_package_bundles"


NORMALIZED_FIELDS = [
    "reported_hunt_year",
    "model_target_year",
    "hunt_code",
    "species",
    "sex_type",
    "hunt_name",
    "hunt_type",
    "weapon",
    "permits",
    "hunters_afield",
    "harvest_total",
    "harvest_male",
    "harvest_female",
    "harvest_young",
    "harvest_unknown",
    "percent_success",
    "average_days",
    "hunter_satisfaction",
    "average_age",
    "male_harvest",
    "female_harvest",
    "harvest_objective",
    "source_file",
    "source_page",
    "source_container",
    "source_member",
    "source_kind",
    "source_priority",
    "source_status",
    "parse_status",
    "do_not_use_for_permit_quota",
    "do_not_use_directly_for_p_draw",
    "trend_feature_eligible",
    "data_quality_flags",
    "recommended_use",
]


def read_csv_rows_from_text(text: str) -> tuple[list[dict[str, str]], list[str]]:
    handle = io.StringIO(text)
    reader = csv.DictReader(handle)
    return list(reader), reader.fieldnames or []


def read_csv_file(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def read_database_codes() -> set[str]:
    if not DATABASE.exists():
        return set()
    rows, _ = read_csv_file(DATABASE)
    return {row["hunt_code"].strip() for row in rows if row.get("hunt_code", "").strip()}


def read_database_rows() -> dict[str, dict[str, str]]:
    if not DATABASE.exists():
        return {}
    rows, _ = read_csv_file(DATABASE)
    return {row["hunt_code"].strip(): row for row in rows if row.get("hunt_code", "").strip()}


def zip_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def harvest_zip_candidates() -> list[Path]:
    candidates = []
    for search_root in [HARVEST_ROOT, SOURCE_BUNDLE_ROOT]:
        if not search_root.exists():
            continue
        for path in search_root.rglob("*.zip"):
            name = path.name.lower()
            if "harvest" in name and ("database" in name or "turkey_harvest" in name or "supplement" in name):
                candidates.append(path)
    # De-dupe duplicate ZIP copies by SHA, preferring the path with an explicit year folder.
    by_sha: dict[str, Path] = {}
    for path in sorted(candidates, key=lambda p: (len(p.parts), str(p))):
        digest = zip_sha(path)
        current = by_sha.get(digest)
        if current is None or "\\20" in str(path) or "/20" in str(path):
            by_sha[digest] = path
    return sorted(by_sha.values())


def normalize_antlerless_hr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.reader(handle))
    header_index = None
    for index, row in enumerate(raw_rows):
        if len(row) >= 9 and row[0].strip() == "Species" and row[1].strip() == "Hunt #":
            header_index = index
            break
    if header_index is None:
        return []
    rows: list[dict[str, str]] = []
    for raw in raw_rows[header_index + 1 :]:
        if len(raw) < 9 or not raw[1].strip():
            continue
        rows.append(
            {
                "reported_hunt_year": "2023",
                "model_target_year": "2024",
                "species": raw[0].strip(),
                "hunt_code": raw[1].strip(),
                "hunt_name": raw[2].strip(),
                "weapon": raw[3].strip(),
                "permits": raw[4].strip(),
                "hunters_afield": raw[5].strip(),
                "harvest_total": raw[6].strip(),
                "percent_success": raw[7].strip(),
                "average_days": raw[8].strip(),
                "source_file": path.name,
                "source_kind": "positional_normalized_antlerless",
                "parse_status": "POSITIONAL_HEADER_NORMALIZED",
                "do_not_use_for_permit_quota": "True",
                "do_not_use_directly_for_p_draw": "True",
            }
        )
    return rows


def candidate_csv_members() -> list[tuple[str, Path | None, str | None, str, int]]:
    """Return candidates as (container, filesystem_path, zip_member, source_kind, priority)."""
    candidates: list[tuple[str, Path | None, str | None, str, int]] = []

    # Expanded 2023 uploaded/all-source files are the richest 2023 source and should outrank the older ZIP.
    expanded_dir = HARVEST_ROOT / "2024" / "csv" / "Harvest Results"
    for name, kind, priority in [
        ("harvest_results_2023_hunt_code_keyed_all_sources.csv", "expanded_2023_keyed_all_sources", 100),
        ("harvest_quality_features_by_hunt_code_2023_uploaded_reports.csv", "expanded_2023_quality_uploaded", 95),
        ("harvest_results_2023_uploaded_reports_all_long.csv", "expanded_2023_uploaded_long", 90),
        ("2024_antlerless_hr.csv", "expanded_2023_antlerless_positional", 85),
        ("turkey_hunt_code_keyed_2024_for_2025.csv", "turkey_2024_keyed", 80),
        ("turkey_quality_features_2023_24_for_2025.csv", "turkey_2023_24_quality", 75),
        ("turkey_harvest_results_2023_24_for_2025_all_long.csv", "turkey_2023_24_long", 70),
    ]:
        path = expanded_dir / name
        if path.exists():
            candidates.append((str(path.relative_to(ROOT)), path, None, kind, priority))

    standalone_antlerless = HARVEST_ROOT / "2024" / "csv" / "2024_antlerless_hr.csv"
    if standalone_antlerless.exists():
        candidates.append(
            (
                str(standalone_antlerless.relative_to(ROOT)),
                standalone_antlerless,
                None,
                "expanded_2023_antlerless_positional",
                84,
            )
        )

    # Extracted 2024/2025 keyed files, if present, are easier to audit than ZIP members.
    for rel, kind, priority in [
        (
            "2025/csv/harvest data/harvest_results_2024_for_2025_hunt_code_keyed.csv",
            "extracted_2024_keyed",
            100,
        ),
        (
            "2025/csv/harvest data/harvest_quality_features_by_hunt_code_2024_for_2025.csv",
            "extracted_2024_quality",
            95,
        ),
        (
            "2025/csv/harvest data/harvest_results_2025_for_2026_hunt_code_keyed.csv",
            "extracted_2025_keyed",
            100,
        ),
        (
            "2025/csv/harvest data/harvest_quality_features_by_hunt_code_2025_for_2026.csv",
            "extracted_2025_quality",
            95,
        ),
    ]:
        path = HARVEST_ROOT / rel
        if path.exists():
            candidates.append((str(path.relative_to(ROOT)), path, None, kind, priority))

    # ZIP members cover 2021, 2022, older 2023, 2024, 2025, and turkey packages.
    for zip_path in harvest_zip_candidates():
        with ZipFile(zip_path) as archive:
            for info in archive.infolist():
                name = info.filename
                lower = name.lower()
                if not lower.endswith(".csv"):
                    continue
                if "summary" in lower or "source_inventory" in lower:
                    continue
                if "hunt_code_keyed" in lower:
                    priority = 80
                    kind = "zip_keyed"
                elif "quality_features" in lower:
                    priority = 75
                    kind = "zip_quality"
                elif "all_long" in lower:
                    priority = 60
                    kind = "zip_long"
                else:
                    priority = 45
                    kind = "zip_species_or_supplement"
                candidates.append((str(zip_path.relative_to(ROOT)), None, name, kind, priority))
    return candidates


def read_candidate(container: str, path: Path | None, member: str | None) -> tuple[list[dict[str, str]], list[str]]:
    if path is not None:
        if path.name.lower() == "2024_antlerless_hr.csv":
            rows = normalize_antlerless_hr(path)
            return rows, list(rows[0].keys()) if rows else []
        return read_csv_file(path)
    assert member is not None
    zip_path = ROOT / container
    with ZipFile(zip_path) as archive:
        text = archive.read(member).decode("utf-8-sig")
    return read_csv_rows_from_text(text)


def first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")
        if str(value).strip():
            return str(value).strip()
    return ""


def truthy_flag(value: str, default: str = "True") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    return "True" if text.lower() in {"true", "yes", "1", "y"} else "False" if text.lower() in {"false", "no", "0", "n"} else text


def infer_year(value: str) -> str:
    value = str(value or "").strip()
    if value and value.replace(".", "", 1).isdigit():
        return str(int(float(value)))
    return value


def normalize_row(
    row: dict[str, str], container: str, member: str | None, source_kind: str, priority: int
) -> dict[str, str] | None:
    hunt_code = first(row, "hunt_code", "Hunt #", "hunt_number", "selected_hunt_code")
    if not hunt_code:
        return None
    reported_year = infer_year(first(row, "reported_hunt_year", "harvest_quality_year"))
    model_year = infer_year(first(row, "model_target_year"))
    if reported_year and not model_year:
        model_year = str(int(reported_year) + 1)
    if not reported_year and model_year:
        reported_year = str(int(model_year) - 1)
    if not reported_year:
        return None

    normalized = {
        "reported_hunt_year": reported_year,
        "model_target_year": model_year,
        "hunt_code": hunt_code,
        "species": first(row, "species", "matched_species"),
        "sex_type": first(row, "sex_type"),
        "hunt_name": first(row, "hunt_name", "matched_hunt_name"),
        "hunt_type": first(row, "hunt_type", "source_family", "harvest_family", "report_family"),
        "weapon": first(row, "weapon"),
        "permits": first(row, "permits", "permits_or_permits_sold", "total_permits", "quota"),
        "hunters_afield": first(row, "hunters_afield", "harvest_hunters", "hunters_afield_or_total_hunters", "total_hunters"),
        "harvest_total": first(row, "harvest_total", "harvest", "total_harvest"),
        "harvest_male": first(row, "harvest_male", "male_harvest"),
        "harvest_female": first(row, "harvest_female", "female_harvest"),
        "harvest_young": first(row, "harvest_young"),
        "harvest_unknown": first(row, "unknown_harvest"),
        "percent_success": first(row, "percent_success", "harvest_success_percent"),
        "average_days": first(row, "average_days", "average_days_hunted", "harvest_average_days", "mean_days_afield"),
        "hunter_satisfaction": first(row, "hunter_satisfaction", "harvest_satisfaction"),
        "average_age": first(row, "average_age", "age_of_sheep", "age_of_sheep_decimal"),
        "male_harvest": first(row, "male_harvest"),
        "female_harvest": first(row, "female_harvest"),
        "harvest_objective": first(row, "harvest_objective"),
        "source_file": first(row, "source_file") or (member or Path(container).name),
        "source_page": first(row, "source_page", "source_page_id"),
        "source_container": container,
        "source_member": member or "",
        "source_kind": source_kind,
        "source_priority": str(priority),
        "source_status": first(row, "source_status"),
        "parse_status": first(row, "parse_status"),
        "do_not_use_for_permit_quota": truthy_flag(first(row, "do_not_use_for_permit_quota")),
        "do_not_use_directly_for_p_draw": truthy_flag(
            first(row, "do_not_use_directly_for_p_draw", "do_not_use_for_p_draw_directly")
        ),
        "trend_feature_eligible": first(row, "trend_feature_eligible"),
        "data_quality_flags": first(row, "data_quality_flags"),
        "recommended_use": first(row, "recommended_use"),
    }
    return normalized


def row_score(row: dict[str, str]) -> tuple[int, int, int]:
    priority = int(row.get("source_priority") or 0)
    filled = sum(1 for field in ["permits", "hunters_afield", "harvest_total", "percent_success", "average_days"] if row.get(field))
    has_quality = 1 if row.get("percent_success") or row.get("average_days") or row.get("hunter_satisfaction") else 0
    return (priority, filled, has_quality)


def special_permit_overlay_class(row: dict[str, str], database_row: dict[str, str] | None = None) -> str:
    text = " ".join(
        [
            row.get("hunt_code", ""),
            row.get("hunt_name", ""),
            row.get("hunt_type", ""),
            row.get("source_file", ""),
            row.get("source_kind", ""),
            (database_row or {}).get("hunt_name", ""),
            (database_row or {}).get("hunt_type", ""),
            (database_row or {}).get("season", ""),
        ]
    ).lower()
    if "expo" in text:
        return "EXPO"
    if "conservation" in text:
        return "CONSERVATION"
    if "sportsman" in text or "sportsmen" in text:
        return "SPORTSMAN"
    if "cwmu" in text:
        return "CWMU"
    return ""


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    database_rows = read_database_rows()
    active_codes = set(database_rows)
    source_audit: list[dict[str, object]] = []
    all_rows: list[dict[str, str]] = []

    for container, path, member, source_kind, priority in candidate_csv_members():
        rows, headers = read_candidate(container, path, member)
        normalized_rows = []
        for row in rows:
            normalized = normalize_row(row, container, member, source_kind, priority)
            if normalized:
                normalized_rows.append(normalized)
        all_rows.extend(normalized_rows)
        codes = {row["hunt_code"] for row in normalized_rows}
        years = sorted({row["reported_hunt_year"] for row in normalized_rows})
        source_audit.append(
            {
                "container": container,
                "member": member or "",
                "source_kind": source_kind,
                "source_priority": priority,
                "raw_rows": len(rows),
                "normalized_rows": len(normalized_rows),
                "unique_hunt_codes": len(codes),
                "active_database_codes": len(codes & active_codes),
                "reported_hunt_years": "|".join(years),
                "header_count": len(headers),
            }
        )

    all_rows.sort(key=lambda row: (row["reported_hunt_year"], row["hunt_code"], row["source_container"], row["source_member"]))

    best: dict[tuple[str, str], dict[str, str]] = {}
    for row in all_rows:
        key = (row["reported_hunt_year"], row["hunt_code"])
        current = best.get(key)
        if current is None or row_score(row) > row_score(current):
            best[key] = row
    best_rows = [best[key] for key in sorted(best)]

    year_counts = Counter(row["reported_hunt_year"] for row in best_rows)
    model_year_counts = Counter(row["model_target_year"] for row in best_rows)
    active_by_year = defaultdict(int)
    for row in best_rows:
        if row["hunt_code"] in active_codes:
            active_by_year[row["reported_hunt_year"]] += 1

    OUT_TRUTH.mkdir(parents=True, exist_ok=True)
    OUT_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT_MODEL.mkdir(parents=True, exist_ok=True)
    OUT_OVERLAY.mkdir(parents=True, exist_ok=True)
    long_path = OUT_TRUTH / "harvest_results_all_years_long.csv"
    best_path = OUT_TRUTH / "harvest_quality_features_all_years_by_hunt_code.csv"
    source_audit_path = OUT_TRUTH / "harvest_results_all_years_source_audit.csv"
    write_csv(long_path, all_rows, NORMALIZED_FIELDS)
    write_csv(best_path, best_rows, NORMALIZED_FIELDS)
    write_csv(
        source_audit_path,
        [{key: str(value) for key, value in row.items()} for row in source_audit],
        [
            "container",
            "member",
            "source_kind",
            "source_priority",
            "raw_rows",
            "normalized_rows",
            "unique_hunt_codes",
            "active_database_codes",
            "reported_hunt_years",
            "header_count",
        ],
    )

    # Convenience processed copies for current tooling.
    write_csv(OUT_PROCESSED / "harvest_results_all_years_long.csv", all_rows, NORMALIZED_FIELDS)
    write_csv(OUT_PROCESSED / "harvest_quality_features_all_years_by_hunt_code.csv", best_rows, NORMALIZED_FIELDS)
    write_csv(OUT_MODEL / "harvest_results_all_years_long.csv", all_rows, NORMALIZED_FIELDS)
    write_csv(OUT_MODEL / "harvest_quality_features_all_years_by_hunt_code.csv", best_rows, NORMALIZED_FIELDS)

    overlay_rows: list[dict[str, str]] = []
    for row in best_rows:
        overlay_class = special_permit_overlay_class(row, database_rows.get(row["hunt_code"]))
        if not overlay_class:
            continue
        overlay_rows.append(
            {
                "reported_hunt_year": row["reported_hunt_year"],
                "model_target_year": row["model_target_year"],
                "hunt_code": row["hunt_code"],
                "species": row["species"],
                "hunt_name": row["hunt_name"],
                "hunt_type": row["hunt_type"],
                "permits": row["permits"],
                "permit_overlay_class": overlay_class,
                "permit_overlay_use": "TOTAL_PERMIT_RECONCILIATION_ONLY",
                "public_draw_odds_use": "NO",
                "p_draw_math_use": "NO",
                "source_file": row["source_file"],
                "source_container": row["source_container"],
            }
        )
    overlay_fields = [
        "reported_hunt_year",
        "model_target_year",
        "hunt_code",
        "species",
        "hunt_name",
        "hunt_type",
        "permits",
        "permit_overlay_class",
        "permit_overlay_use",
        "public_draw_odds_use",
        "p_draw_math_use",
        "source_file",
        "source_container",
    ]
    write_csv(OUT_OVERLAY / "special_permit_overlay_classes_all_years.csv", overlay_rows, overlay_fields)
    write_csv(OUT_PROCESSED / "special_permit_overlay_classes_all_years.csv", overlay_rows, overlay_fields)

    duplicate_keys = len(all_rows) - len({(row["reported_hunt_year"], row["hunt_code"], row["source_container"], row["source_member"]) for row in all_rows})
    summary = {
        "source_candidates": len(source_audit),
        "normalized_long_rows": len(all_rows),
        "best_by_year_hunt_code_rows": len(best_rows),
        "unique_reported_hunt_years": sorted(year_counts),
        "reported_hunt_year_counts": dict(sorted(year_counts.items())),
        "model_target_year_counts": dict(sorted(model_year_counts.items())),
        "active_database_hunt_codes": len(active_codes),
        "active_database_coverage_by_reported_hunt_year": dict(sorted(active_by_year.items())),
        "unique_hunt_codes_all_years": len({row["hunt_code"] for row in best_rows}),
        "special_permit_overlay_rows": len(overlay_rows),
        "special_permit_overlay_class_counts": dict(Counter(row["permit_overlay_class"] for row in overlay_rows)),
        "duplicate_source_key_count": duplicate_keys,
        "outputs": {
            "long_csv": str(long_path.relative_to(ROOT)),
            "best_by_hunt_code_csv": str(best_path.relative_to(ROOT)),
            "source_audit_csv": str(source_audit_path.relative_to(ROOT)),
            "processed_long_csv": "processed_data/harvest_results_all_years_long.csv",
            "processed_best_by_hunt_code_csv": "processed_data/harvest_quality_features_all_years_by_hunt_code.csv",
            "data_model_long_csv": "data_model/harvest_quality/harvest_results_all_years_long.csv",
            "data_model_best_by_hunt_code_csv": "data_model/harvest_quality/harvest_quality_features_all_years_by_hunt_code.csv",
            "special_permit_overlay_csv": "data_model/permit_overlays/special_permit_overlay_classes_all_years.csv",
            "summary_json": "data_truth/harvest_results_truth/normalized/harvest_results_all_years_summary.json",
            "summary_md": "data_truth/harvest_results_truth/normalized/harvest_results_all_years_summary.md",
        },
        "guardrails": [
            "Harvest permits remain harvest-report context and are not current-year draw allotments.",
            "Harvest rows are marked do_not_use_for_permit_quota=True and do_not_use_directly_for_p_draw=True by default.",
            "Reported hunt year drives model target year as reported_hunt_year + 1 when model_target_year is missing.",
        ],
    }
    (OUT_TRUTH / "harvest_results_all_years_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = ["# All-Years Harvest Results Database", "", "## Summary"]
    for key, value in summary.items():
        if isinstance(value, dict):
            md.append(f"- {key}: {value}")
        elif isinstance(value, list):
            md.append(f"- {key}: {', '.join(map(str, value))}")
        else:
            md.append(f"- {key}: {value}")
    (OUT_TRUTH / "harvest_results_all_years_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
