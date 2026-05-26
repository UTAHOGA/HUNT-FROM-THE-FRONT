from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "processed_data/2026_big_game_application_guidebook_season_corrections.json"

RS6700_CORRECTION = {
    "hunt_code": "RS6700",
    "source": "2026 Big Game Application Guidebook page 67",
    "old_values": {"Nov 11, 2026 - Nov 18, 2026", "Nov 11 2026 - Nov 18 2026"},
    "new_value": "Nov 09 2026 - Nov 16 2026",
    "new_value_commas": "Nov 09, 2026 - Nov 16, 2026",
}

CSV_FILES = [
    "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv",
    "data/hunt-master-canonical-2026-database-candidate.csv",
    "data/hunt-master-canonical-2026-foundation.csv",
    "data/hunt-master-canonical-2026-source-of-truth.csv",
    "processed_data/hunt-master-canonical-2026-source-of-truth.csv",
    "data/utah/official_downloads_2026/hunt_master_canonical_2026.csv",
    "data/utah/foundation_bundle_2026/utah_hunt_codes_canonical_2026.csv",
]

JSON_FILES = [
    "data/bighorn_sheep_hunt_table_official.json",
    "data/hunt-master-canonical-2026-database-candidate.json",
    "data/hunt-master-canonical-2026-foundation.json",
    "data/hunt-master-canonical-2026-source-of-truth.json",
    "processed_data/hunt-master-canonical-2026-source-of-truth.json",
    "canonical/hunt-planner-2026.json",
    "generated/pages/hunt-planner.json",
]


def is_rs6700(row: dict[str, Any]) -> bool:
    return any(str(row.get(key, "")).strip() == RS6700_CORRECTION["hunt_code"] for key in ("hunt_code", "HUNT_NUMBER", "HuntCode", "code"))


def update_season_value(value: Any, prefer_commas: bool = False) -> tuple[Any, bool]:
    if not isinstance(value, str):
        return value, False
    if value not in RS6700_CORRECTION["old_values"]:
        return value, False
    return (RS6700_CORRECTION["new_value_commas"] if prefer_commas else RS6700_CORRECTION["new_value"]), True


def patch_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "exists": False, "changed_cells": 0}

    raw = path.read_text(encoding="utf-8-sig")
    had_bom = path.read_bytes().startswith(b"\xef\xbb\xbf")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()

    changed_cells = 0
    touched_rows = 0
    next_lines = []
    reader = csv.DictReader(lines)
    for index, parsed in enumerate(reader, start=1):
        line = lines[index]
        if is_rs6700(parsed):
            next_line = line
            for old in RS6700_CORRECTION["old_values"]:
                replacement = RS6700_CORRECTION["new_value_commas"] if "," in old else RS6700_CORRECTION["new_value"]
                if old in next_line:
                    next_line = next_line.replace(old, replacement)
                    changed_cells += 1
            if next_line != line:
                touched_rows += 1
            line = next_line
        next_lines.append(line)

    if changed_cells:
        output = lines[:1] + next_lines
        text = newline.join(output) + (newline if raw.endswith(("\n", "\r\n")) else "")
        if had_bom:
            path.write_text("\ufeff" + text, encoding="utf-8")
        else:
            path.write_text(text, encoding="utf-8")

    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "exists": True,
        "changed_cells": changed_cells,
        "touched_rows": touched_rows,
    }


def patch_object(value: Any) -> tuple[Any, int]:
    if isinstance(value, list):
        total = 0
        next_items = []
        for item in value:
            patched, changed = patch_object(item)
            total += changed
            next_items.append(patched)
        return next_items, total

    if isinstance(value, dict):
        total = 0
        next_obj = {}
        row_is_rs6700 = is_rs6700(value)
        for key, item in value.items():
            if row_is_rs6700 and key in {"season", "SEASON", "season_dates", "Season"}:
                prefer_commas = "," in item if isinstance(item, str) else False
                patched, changed = update_season_value(item, prefer_commas=prefer_commas)
                next_obj[key] = patched
                total += int(changed)
            else:
                patched, changed = patch_object(item)
                next_obj[key] = patched
                total += changed
        return next_obj, total

    return value, 0


def patch_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "exists": False, "changed_cells": 0}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    patched, changed_cells = patch_object(data)
    if changed_cells:
        path.write_text(json.dumps(patched, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "exists": True,
        "changed_cells": changed_cells,
    }


def main() -> None:
    results = {
        "correction": {
            "hunt_code": RS6700_CORRECTION["hunt_code"],
            "source": RS6700_CORRECTION["source"],
            "old_values": sorted(RS6700_CORRECTION["old_values"]),
            "new_value": RS6700_CORRECTION["new_value"],
        },
        "csv": [patch_csv(ROOT / rel) for rel in CSV_FILES],
        "json": [patch_json(ROOT / rel) for rel in JSON_FILES],
    }
    results["total_changed_cells"] = sum(item.get("changed_cells", 0) for group in ("csv", "json") for item in results[group])
    REPORT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
