"""Import harvest ZIP packages into truth/model source folders.

This intentionally unpacks existing package artifacts only. It does not parse or
re-extract PDFs.
"""

from __future__ import annotations

import csv
import hashlib
import re
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
HARVEST_ROOT = ROOT / "pipeline" / "RAW" / "hunt_unit_database"
TRUTH_RAW = ROOT / "data_truth" / "harvest_results_truth" / "raw_packages"
MODEL_RAW = ROOT / "data_model" / "harvest_quality" / "raw_packages"
TRUTH_BUNDLES = ROOT / "data_truth" / "harvest_results_truth" / "source_package_bundles"
MODEL_BUNDLES = ROOT / "data_model" / "harvest_quality" / "source_package_bundles"
MASTER_BUNDLE = HARVEST_ROOT / "HUNTS_harvest_truth_and_overlay_packages_for_codex.zip"
MANIFEST_CSV = ROOT / "data_truth" / "harvest_results_truth" / "raw_packages_manifest.csv"
MANIFEST_JSON = ROOT / "data_truth" / "harvest_results_truth" / "raw_packages_manifest.json"
SUMMARY_MD = ROOT / "data_truth" / "harvest_results_truth" / "raw_packages_manifest.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def season_end_year(start_year_text: str, end_year_text: str) -> str:
    """Return the ending year for split seasons like 2023_24 or 23-24."""
    start_year = int(start_year_text)
    if len(end_year_text) == 4:
        return str(int(end_year_text))
    century = (start_year // 100) * 100
    end_year = century + int(end_year_text)
    if end_year < start_year:
        end_year += 100
    return str(end_year)


def infer_years(name: str) -> tuple[str, str]:
    lower = name.lower()
    # Most packages follow harvest_results_YYYY_for_YYYY_database.
    # Split seasons use the ending season year as the reported hunt year.
    match = re.search(r"harvest_results_(\d{4})[_-](\d{2}|\d{4})_for_(\d{4})", lower)
    if match:
        return season_end_year(match.group(1), match.group(2)), match.group(3)

    match = re.search(r"harvest_results_(\d{4})_for_(\d{4})", lower)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"harvest_results_(\d{4})_all_species", lower)
    if match:
        year = match.group(1)
        return year, str(int(year) + 1)
    match = re.search(r"expo_.*?(\d{4})", lower)
    if match:
        year = match.group(1)
        return year, year
    match = re.search(r"conservation_.*?(\d{4})", lower)
    if match:
        year = match.group(1)
        return year, year
    match = re.search(r"(\d{4})_(\d{4})", lower)
    if match:
        return match.group(2), match.group(2)
    return "", ""


def materialize_master_bundle_zip_candidates() -> list[Path]:
    if not MASTER_BUNDLE.exists():
        return []
    bundle_name = MASTER_BUNDLE.stem
    truth_dest = TRUTH_BUNDLES / bundle_name
    model_dest = MODEL_BUNDLES / bundle_name
    if truth_dest.exists():
        shutil.rmtree(truth_dest)
    truth_dest.mkdir(parents=True, exist_ok=True)
    with ZipFile(MASTER_BUNDLE) as archive:
        for member in archive.infolist():
            if member.is_dir() or not member.filename.lower().endswith(".zip"):
                continue
            target = truth_dest / Path(member.filename).name
            resolved = target.resolve()
            if not str(resolved).startswith(str(truth_dest.resolve())):
                raise ValueError(f"Unsafe nested ZIP path: {member.filename}")
            with archive.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    if model_dest.exists():
        shutil.rmtree(model_dest)
    shutil.copytree(truth_dest, model_dest)
    return sorted(truth_dest.glob("*.zip"))


def package_candidates() -> list[Path]:
    candidates: list[Path] = []
    master_candidates = materialize_master_bundle_zip_candidates()
    master_names = {path.name for path in master_candidates}
    for path in HARVEST_ROOT.rglob("*.zip"):
        if path.name in master_names:
            continue
        name = path.name.lower()
        if "harvest" in name and ("database" in name or "turkey_harvest" in name):
            candidates.append(path)
    candidates.extend(master_candidates)
    return sorted(candidates)


def safe_extract_zip(zip_path: Path, destination: Path) -> int:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    with ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = destination / member.filename
            resolved = target.resolve()
            if not str(resolved).startswith(str(destination.resolve())):
                raise ValueError(f"Unsafe ZIP path: {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    return count


def main() -> int:
    by_sha: dict[str, list[Path]] = {}
    for path in package_candidates():
        by_sha.setdefault(sha256(path), []).append(path)

    manifest: list[dict[str, object]] = []
    for digest, paths in sorted(by_sha.items(), key=lambda item: sorted(str(p) for p in item[1])[0]):
        canonical = sorted(paths, key=lambda p: (0 if any(part.isdigit() and len(part) == 4 for part in p.parts) else 1, len(p.parts), str(p)))[0]
        reported_year, model_year = infer_years(canonical.name)
        package_id = f"{reported_year or 'unknown'}_for_{model_year or 'unknown'}_{canonical.stem}"
        truth_dest = TRUTH_RAW / package_id
        model_dest = MODEL_RAW / package_id
        extracted_files = safe_extract_zip(canonical, truth_dest)
        # Mirror CSV/JSON/MD/SQLite package content into data_model for feature-source provenance.
        if model_dest.exists():
            shutil.rmtree(model_dest)
        shutil.copytree(truth_dest, model_dest)
        with ZipFile(canonical) as archive:
            names = [info.filename for info in archive.infolist() if not info.is_dir()]
            csv_count = sum(1 for name in names if name.lower().endswith(".csv"))
            sqlite_count = sum(1 for name in names if name.lower().endswith(".sqlite"))
            pdf_count = sum(1 for name in names if name.lower().endswith(".pdf"))
        manifest.append(
            {
                "package_id": package_id,
                "canonical_zip": str(canonical.relative_to(ROOT)),
                "duplicate_zip_paths": "|".join(str(path.relative_to(ROOT)) for path in paths if path != canonical),
                "sha256": digest,
                "reported_hunt_year": reported_year,
                "model_target_year": model_year,
                "truth_extract_dir": str(truth_dest.relative_to(ROOT)),
                "model_extract_dir": str(model_dest.relative_to(ROOT)),
                "extracted_files": extracted_files,
                "csv_files": csv_count,
                "sqlite_files": sqlite_count,
                "pdf_files": pdf_count,
                "pdf_reextraction_performed": "NO",
            }
        )

    MANIFEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(manifest[0].keys()) if manifest else ["package_id"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "unique_packages_imported": len(manifest),
        "duplicate_package_paths": sum(1 for row in manifest if row["duplicate_zip_paths"]),
        "total_extracted_files": sum(int(row["extracted_files"]) for row in manifest),
        "total_csv_files": sum(int(row["csv_files"]) for row in manifest),
        "total_sqlite_files": sum(int(row["sqlite_files"]) for row in manifest),
        "total_pdf_files": sum(int(row["pdf_files"]) for row in manifest),
        "pdf_reextraction_performed": "NO",
        "packages": manifest,
    }
    MANIFEST_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = ["# Harvest Package Import Manifest", "", f"- unique_packages_imported: {summary['unique_packages_imported']}"]
    lines.append(f"- total_extracted_files: {summary['total_extracted_files']}")
    lines.append(f"- pdf_reextraction_performed: {summary['pdf_reextraction_performed']}")
    lines.append("")
    lines.append("## Packages")
    for row in manifest:
        lines.append(
            f"- {row['package_id']}: files={row['extracted_files']}; reported={row['reported_hunt_year']}; "
            f"model={row['model_target_year']}; source={row['canonical_zip']}"
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
