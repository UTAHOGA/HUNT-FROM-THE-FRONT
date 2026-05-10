from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]

SCAN_DIRS = [
    REPO_ROOT / "pipeline/RAW/",
    REPO_ROOT / "pipeline/RAW/hunt_unit_database/",
    REPO_ROOT / "pipeline/RAW/hunt_unit_database/2025/",
    REPO_ROOT / "pipeline/RAW/hunt_unit_database/2025/formatted_tables/",
]

OUT_CSV = REPO_ROOT / "data_model/quality/raw_pdf_inventory.csv"
OUT_JSON = REPO_ROOT / "data_model/quality/raw_pdf_inventory.json"
OUT_REPORT = REPO_ROOT / "data_model/quality/raw_pdf_inventory_report.json"

# "PDF or extracted source file"
INCLUDED_EXTS = {
    ".pdf",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".json",
    ".geojson",
    ".txt",
}

SPECIES_HINTS = [
    ("black_bear", "Black Bear"),
    ("bear", "Black Bear"),
    ("elk", "Elk"),
    ("deer", "Deer"),
    ("bison", "Bison"),
    ("pronghorn", "Pronghorn"),
    ("moose", "Moose"),
    ("goat", "Mountain Goat"),
    ("sheep", "Bighorn Sheep"),
    ("turkey", "Turkey"),
    ("cougar", "Cougar"),
]


@dataclass
class InventoryRow:
    path: str
    filename: str
    inferred_species: str
    inferred_year: str
    inferred_report_type: str
    file_size_bytes: int
    modified_time: str
    sha256: str
    page_count: int | None
    extraction_status: str
    likely_metric_families: list[str]

    def to_csv_row(self) -> dict[str, str]:
        return {
            "path": self.path,
            "filename": self.filename,
            "inferred_species": self.inferred_species,
            "inferred_year": self.inferred_year,
            "inferred_report_type": self.inferred_report_type,
            "file_size_bytes": str(self.file_size_bytes),
            "modified_time": self.modified_time,
            "sha256": self.sha256,
            "page_count": "" if self.page_count is None else str(self.page_count),
            "extraction_status": self.extraction_status,
            "likely_metric_families": ";".join(self.likely_metric_families),
        }

    def to_json_row(self) -> dict[str, object]:
        return {
            "path": self.path,
            "filename": self.filename,
            "inferred_species": self.inferred_species,
            "inferred_year": self.inferred_year,
            "inferred_report_type": self.inferred_report_type,
            "file_size_bytes": self.file_size_bytes,
            "modified_time": self.modified_time,
            "sha256": self.sha256,
            "page_count": self.page_count,
            "extraction_status": self.extraction_status,
            "likely_metric_families": self.likely_metric_families,
        }


def to_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def iter_target_files(scan_dirs: Iterable[Path]) -> list[Path]:
    files: set[Path] = set()
    for root in scan_dirs:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in INCLUDED_EXTS:
                continue
            files.add(path.resolve())
    return sorted(files)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def infer_species(path: Path) -> str:
    text = f"{path.parent.as_posix()} {path.name}".lower()
    for token, species in SPECIES_HINTS:
        if token in text:
            return species
    return "Unknown"


def infer_year(path: Path) -> str:
    text = f"{path.parent.as_posix()} {path.name}"
    matches = re.findall(r"(20\d{2})", text)
    return matches[0] if matches else ""


def infer_report_type(path: Path) -> str:
    text = f"{path.parent.as_posix()} {path.name}".lower()
    if "draw" in text or "odds" in text or "permit" in text:
        return "permit_or_draw_related"
    if "average age" in text or "average_age" in text or "avg_age" in text:
        return "average_age"
    if "preseason" in text or "calf per 100 cows" in text or "classification" in text:
        return "preseason_classification"
    if "winter population" in text:
        return "winter_population"
    if "winter trend" in text:
        return "winter_trend"
    if "harvest" in text and ("by unit" in text or "management unit" in text):
        return "harvest_by_unit"
    if "harvest" in text:
        return "harvest_result"
    return "unknown"


def likely_metric_families(report_type: str) -> list[str]:
    if report_type == "permit_or_draw_related":
        return ["draw_odds", "permits", "applicants", "points", "residency_split"]
    if report_type in {"harvest_result", "harvest_by_unit"}:
        return ["harvest", "hunters_afield", "success_rate", "mean_days_hunted", "permits"]
    if report_type == "average_age":
        return ["average_age", "year_series"]
    if report_type == "preseason_classification":
        return ["calves_per_100_cows", "bulls_per_100_cows", "classification_ratio"]
    if report_type == "winter_population":
        return ["winter_population", "year_series"]
    if report_type == "winter_trend":
        return ["winter_trend", "year_series", "trend_index"]
    return []


def get_pdf_page_count(path: Path) -> tuple[int | None, str]:
    if path.suffix.lower() != ".pdf":
        return None, "extracted_source_file"
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        return len(reader.pages), "raw_pdf_unparsed"
    except Exception:
        return None, "raw_pdf_page_count_unavailable"


def iso_mtime(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def build_inventory() -> list[InventoryRow]:
    files = iter_target_files(SCAN_DIRS)
    rows: list[InventoryRow] = []
    for path in files:
        page_count, status = get_pdf_page_count(path)
        rep_type = infer_report_type(path)
        rows.append(
            InventoryRow(
                path=to_rel(path),
                filename=path.name,
                inferred_species=infer_species(path),
                inferred_year=infer_year(path),
                inferred_report_type=rep_type,
                file_size_bytes=path.stat().st_size,
                modified_time=iso_mtime(path),
                sha256=sha256_of(path),
                page_count=page_count,
                extraction_status=status,
                likely_metric_families=likely_metric_families(rep_type),
            )
        )
    return rows


def write_outputs(rows: list[InventoryRow]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    csv_fields = [
        "path",
        "filename",
        "inferred_species",
        "inferred_year",
        "inferred_report_type",
        "file_size_bytes",
        "modified_time",
        "sha256",
        "page_count",
        "extraction_status",
        "likely_metric_families",
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump([r.to_json_row() for r in rows], f, indent=2)


def write_report(rows: list[InventoryRow]) -> None:
    by_sha: defaultdict[str, list[str]] = defaultdict(list)
    by_name_to_sha: defaultdict[str, set[str]] = defaultdict(set)
    missing_year: list[str] = []
    unknown_type: list[str] = []

    for r in rows:
        by_sha[r.sha256].append(r.path)
        by_name_to_sha[r.filename].add(r.sha256)
        if not r.inferred_year:
            missing_year.append(r.path)
        if r.inferred_report_type == "unknown":
            unknown_type.append(r.path)

    duplicate_sha256_files = [
        {"sha256": sha, "paths": paths, "count": len(paths)}
        for sha, paths in by_sha.items()
        if len(paths) > 1
    ]

    same_filename_different_sha256 = [
        {"filename": name, "sha256_count": len(hashes), "sha256_values": sorted(hashes)}
        for name, hashes in by_name_to_sha.items()
        if len(hashes) > 1
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_dirs": [to_rel(p) for p in SCAN_DIRS],
        "included_extensions": sorted(INCLUDED_EXTS),
        "inventory_count": len(rows),
        "validation": {
            "duplicate_sha256_files_count": len(duplicate_sha256_files),
            "duplicate_sha256_files": duplicate_sha256_files,
            "same_filename_different_sha256_count": len(same_filename_different_sha256),
            "same_filename_different_sha256": same_filename_different_sha256,
            "missing_inferred_year_count": len(missing_year),
            "missing_inferred_year_paths": sorted(missing_year),
            "unknown_report_type_count": len(unknown_type),
            "unknown_report_type_paths": sorted(unknown_type),
        },
        "output_files": {
            "inventory_csv": to_rel(OUT_CSV),
            "inventory_json": to_rel(OUT_JSON),
            "report_json": to_rel(OUT_REPORT),
        },
    }

    with OUT_REPORT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def main() -> None:
    rows = build_inventory()
    write_outputs(rows)
    write_report(rows)
    print(f"Wrote {to_rel(OUT_CSV)}")
    print(f"Wrote {to_rel(OUT_JSON)}")
    print(f"Wrote {to_rel(OUT_REPORT)}")
    print(f"Inventory rows: {len(rows)}")


if __name__ == "__main__":
    main()
