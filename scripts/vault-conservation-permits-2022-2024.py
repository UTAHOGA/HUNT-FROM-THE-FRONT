from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = REPO_ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2023" / "pdf" / "regulation" / "9E134C35__2022-24_conservation_permits.pdf"
SOURCE_EXTRACTED_WORKBOOK = REPO_ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2023" / "2022_2024_conservation_permits_extracted.xlsx"
HELD_DUPLICATE_WORKBOOK = REPO_ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2023" / "csv" / "2022_2024_conservation_permits_extracted.xlsx"

VAULT_ROOT = REPO_ROOT / "data_truth" / "permit_overlay_truth" / "raw_sources" / "2022_2024_conservation_permits"
VAULT_SOURCE_DIR = VAULT_ROOT / "source_files"
VAULT_MANIFEST_JSON = VAULT_ROOT / "source_manifest.json"
VAULT_MANIFEST_CSV = VAULT_ROOT / "source_manifest.csv"
VAULT_README = VAULT_ROOT / "README.md"

VAULT_PDF = VAULT_SOURCE_DIR / "2022-24_conservation_permits.pdf"
VAULT_EXTRACTED_WORKBOOK = VAULT_SOURCE_DIR / "2022_2024_conservation_permits_extracted.xlsx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(
    *,
    role: str,
    status: str,
    source_path: Path,
    vault_path: Path | None,
    note: str,
) -> dict[str, object]:
    return {
        "role": role,
        "status": status,
        "source_path": str(source_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "vault_path": str(vault_path.relative_to(REPO_ROOT)).replace("\\", "/") if vault_path else "",
        "file_name": source_path.name,
        "file_size_bytes": source_path.stat().st_size,
        "sha256": sha256(source_path),
        "note": note,
    }


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    fieldnames = [
        "role",
        "status",
        "source_path",
        "vault_path",
        "file_name",
        "file_size_bytes",
        "sha256",
        "note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def validate_manifest(manifest: dict[str, object]) -> list[str]:
    failures: list[str] = []
    files = manifest["files"]

    promoted = [entry for entry in files if entry["status"] == "VAULTED_CANONICAL_COPY"]
    held_duplicates = [entry for entry in files if entry["status"] == "HELD_DUPLICATE_EXACT_SHA256"]

    if len(promoted) != 2:
        failures.append(f"Expected 2 vaulted canonical files, found {len(promoted)}.")
    if len(held_duplicates) != 1:
        failures.append(f"Expected 1 held duplicate record, found {len(held_duplicates)}.")

    for entry in promoted:
        vault_path = REPO_ROOT / str(entry["vault_path"])
        source_path = REPO_ROOT / str(entry["source_path"])
        if not vault_path.exists():
            failures.append(f"Missing vaulted file: {entry['vault_path']}")
            continue
        if vault_path.stat().st_size != entry["file_size_bytes"]:
            failures.append(f"Size mismatch for {entry['vault_path']}")
        if sha256(vault_path) != entry["sha256"]:
            failures.append(f"SHA mismatch for {entry['vault_path']}")
        if sha256(source_path) != entry["sha256"]:
            failures.append(f"Source SHA mismatch for {entry['source_path']}")

    duplicate = held_duplicates[0] if held_duplicates else None
    workbook = next((entry for entry in promoted if entry["role"] == "extracted_workbook"), None)
    if duplicate and workbook and duplicate["sha256"] != workbook["sha256"]:
        failures.append("Held workbook duplicate does not match canonical workbook SHA-256.")

    if manifest["source_class"] != "permit_overlay_reference":
        failures.append("Manifest source_class must remain permit_overlay_reference.")
    if manifest["guardrail"] != "DO_NOT_USE_AS_HARVEST_RESULTS_OR_DRAW_ODDS":
        failures.append("Manifest guardrail changed unexpectedly.")
    if manifest["values_extracted_by_this_step"] is not False:
        failures.append("Vault step must not extract values.")

    return failures


def main() -> int:
    for source in [SOURCE_PDF, SOURCE_EXTRACTED_WORKBOOK, HELD_DUPLICATE_WORKBOOK]:
        if not source.exists():
            raise FileNotFoundError(source)

    VAULT_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_PDF, VAULT_PDF)
    shutil.copy2(SOURCE_EXTRACTED_WORKBOOK, VAULT_EXTRACTED_WORKBOOK)

    records = [
        file_record(
            role="source_pdf",
            status="VAULTED_CANONICAL_COPY",
            source_path=SOURCE_PDF,
            vault_path=VAULT_PDF,
            note="Canonical 2022-2024 conservation permits PDF from raw intake.",
        ),
        file_record(
            role="extracted_workbook",
            status="VAULTED_CANONICAL_COPY",
            source_path=SOURCE_EXTRACTED_WORKBOOK,
            vault_path=VAULT_EXTRACTED_WORKBOOK,
            note="Canonical extracted workbook paired with the conservation permits PDF.",
        ),
        file_record(
            role="extracted_workbook_duplicate",
            status="HELD_DUPLICATE_EXACT_SHA256",
            source_path=HELD_DUPLICATE_WORKBOOK,
            vault_path=None,
            note="Exact SHA-256 duplicate of the vaulted extracted workbook; not copied twice.",
        ),
    ]

    manifest: dict[str, object] = {
        "classification": "CONSERVATION_PERMITS_2022_2024_SOURCE_VAULT_PACKAGE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_class": "permit_overlay_reference",
        "source_authority": "Utah DWR",
        "covered_permit_years": [2022, 2023, 2024],
        "storage_context_year": 2023,
        "promotion_status": "VAULTED_REFERENCE_SOURCE",
        "guardrail": "DO_NOT_USE_AS_HARVEST_RESULTS_OR_DRAW_ODDS",
        "values_extracted_by_this_step": False,
        "website_outputs_modified": False,
        "files": records,
    }

    failures = validate_manifest(manifest)
    manifest["validation"] = {
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "vaulted_file_count": 2,
        "held_duplicate_count": 1,
    }

    VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    VAULT_MANIFEST_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_csv(VAULT_MANIFEST_CSV, records)
    VAULT_README.write_text(
        "\n".join(
            [
                "# 2022-2024 Conservation Permits Source Vault",
                "",
                "This package preserves the 2022-2024 Utah conservation permit source files.",
                "",
                "- Source class: `permit_overlay_reference`",
                "- Source authority: `Utah DWR`",
                "- Covered permit years: `2022`, `2023`, `2024`",
                "- Guardrail: `DO_NOT_USE_AS_HARVEST_RESULTS_OR_DRAW_ODDS`",
                "- This vault step does not extract values or modify website-facing outputs.",
                "",
                "Vaulted canonical files are listed in `source_manifest.json` and `source_manifest.csv`.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps(manifest["validation"], indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
