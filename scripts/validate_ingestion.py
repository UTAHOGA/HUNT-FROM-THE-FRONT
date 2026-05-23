#!/usr/bin/env python3
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / "engine_payload_manifest.json").read_text())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

errors = []
for entry in manifest["files"]:
    rel = entry["path"]
    p = ROOT / rel
    if not p.exists():
        errors.append(f"missing: {rel}")
        continue
    actual = sha256_file(p)
    if actual != entry["sha256"]:
        errors.append(f"sha256 mismatch: {rel}")
    if rel.endswith(".csv") and "row_count" in entry:
        with p.open('r', encoding='utf-8-sig', newline='') as f:
            count = max(sum(1 for _ in csv.reader(f)) - 1, 0)
        if count != entry["row_count"]:
            errors.append(f"row count mismatch: {rel}: expected {entry['row_count']}, got {count}")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(f"- {e}")
    raise SystemExit(1)
print("VALIDATION PASSED")
print(f"Checked {len(manifest['files'])} files.")
