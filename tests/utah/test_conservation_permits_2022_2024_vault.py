import csv
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VAULT_ROOT = (
    REPO_ROOT
    / "data_truth"
    / "permit_overlay_truth"
    / "raw_sources"
    / "2022_2024_conservation_permits"
)
MANIFEST_JSON = VAULT_ROOT / "source_manifest.json"
MANIFEST_CSV = VAULT_ROOT / "source_manifest.csv"
README = VAULT_ROOT / "README.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest():
    return json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))


def test_conservation_permits_vault_outputs_exist():
    assert MANIFEST_JSON.exists()
    assert MANIFEST_CSV.exists()
    assert README.exists()


def test_conservation_permits_manifest_guardrails():
    manifest = load_manifest()

    assert manifest["classification"] == "CONSERVATION_PERMITS_2022_2024_SOURCE_VAULT_PACKAGE"
    assert manifest["source_class"] == "permit_overlay_reference"
    assert manifest["covered_permit_years"] == [2022, 2023, 2024]
    assert manifest["guardrail"] == "DO_NOT_USE_AS_HARVEST_RESULTS_OR_DRAW_ODDS"
    assert manifest["values_extracted_by_this_step"] is False
    assert manifest["website_outputs_modified"] is False
    assert manifest["validation"]["status"] == "PASS"


def test_conservation_permits_vault_file_hashes_match_manifest():
    manifest = load_manifest()
    files = manifest["files"]
    vaulted = [entry for entry in files if entry["status"] == "VAULTED_CANONICAL_COPY"]
    held = [entry for entry in files if entry["status"] == "HELD_DUPLICATE_EXACT_SHA256"]

    assert len(vaulted) == 2
    assert len(held) == 1

    for entry in vaulted:
        source_path = REPO_ROOT / entry["source_path"]
        vault_path = REPO_ROOT / entry["vault_path"]
        assert source_path.exists()
        assert vault_path.exists()
        assert source_path.stat().st_size == entry["file_size_bytes"]
        assert vault_path.stat().st_size == entry["file_size_bytes"]
        assert sha256(source_path) == entry["sha256"]
        assert sha256(vault_path) == entry["sha256"]

    workbook = next(entry for entry in vaulted if entry["role"] == "extracted_workbook")
    assert held[0]["sha256"] == workbook["sha256"]


def test_conservation_permits_manifest_csv_matches_json():
    manifest = load_manifest()

    with MANIFEST_CSV.open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))

    assert len(csv_rows) == len(manifest["files"])
    assert {row["sha256"] for row in csv_rows} == {
        entry["sha256"] for entry in manifest["files"]
    }
