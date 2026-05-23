"""Normalize canonical draw_family labels to user-facing families.

The predictive engine keeps draw mechanics in algorithm_status/draw_system_type.
This field is a catalog/display family, so values should describe the hunt
offering rather than internal modeling buckets like BONUS or NONE.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "processed_data" / "draw_family_label_normalization_report.json"

CSV_TARGETS = [
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.csv",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.csv",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.csv",
]

JSON_TARGETS = [
    ROOT / "hunt-master-canonical-2026.json",
    ROOT / "data" / "hunt-master-canonical-2026-database-candidate.json",
    ROOT / "data" / "hunt-master-canonical-2026-foundation.json",
    ROOT / "data" / "hunt-master-canonical-2026-source-of-truth.json",
    ROOT / "processed_data" / "hunt-master-canonical-2026-source-of-truth.json",
    ROOT / "canonical" / "hunt-planner-2026.json",
    ROOT / "generated" / "pages" / "hunt-planner.json",
]


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def has_quota(row: dict[str, Any]) -> bool:
    for field in (
        "permits_2026_res",
        "permits_2026_nr",
        "permits_2026_total",
        "permit_allotment_2026_res",
        "permit_allotment_2026_nr",
        "permit_allotment_2026_total",
    ):
        if clean(row.get(field)):
            return True
    return False


def derive_draw_family(row: dict[str, Any]) -> str:
    current = clean(row.get("draw_family"))
    old = current.upper()
    hunt_type = clean(row.get("hunt_type") or row.get("hunt_class")).lower()
    name = clean(row.get("hunt_name") or row.get("title") or row.get("unitName")).lower()
    species = clean(row.get("species")).lower()
    code = clean(row.get("hunt_code") or row.get("huntCode") or row.get("code")).upper()
    text = " ".join([hunt_type, name, species, code]).lower()

    if "harvest objective" in text:
        return "Availability"
    if "private lands only" in text or "private land only" in text:
        return "Allocation"
    if "cwmu" in text:
        return "CWMU"
    if "tribal" in text:
        return "Allocation"
    if "conservation" in text or "expo" in text:
        return "Allocation"
    if "statewide permit" in text or hunt_type == "statewide":
        return "Sportsman"
    if "otc" in text or "over-the-counter" in text or "over the counter" in text:
        return "O.T.C."

    # Bonus/random point systems, including OIAL and premium/limited-entry rows,
    # are user-facing limited-entry draw families.
    if old in {"BONUS", "TURKEY_DRAW"}:
        return "Limited Entry"
    if "once-in-a-lifetime" in text or "once in a lifetime" in text:
        return "Limited Entry"
    if "premium limited entry" in text or "limited entry" in text:
        return "Limited Entry"
    if "management buck" in text or "cactus buck" in text:
        return "Limited Entry"
    if "restricted pursuit" in text and has_quota(row):
        return "Limited Entry"
    if "spot and stalk" in text and has_quota(row):
        return "Limited Entry"

    # Preference-point/public draw families.
    if old == "ANTLERLESS":
        return "General"
    if "general season" in text and has_quota(row):
        return "General"
    if "fall management" in text and has_quota(row):
        return "General"

    # True no-quota statewide/availability rows are not modeled draw families.
    if "extended archery" in text:
        return "O.T.C."
    if not has_quota(row) and any(token in text for token in ("pursuit", "statewide", "general season")):
        return "O.T.C."

    if old in {"HARVEST_OBJECTIVE"}:
        return "Availability"
    if old in {"UNKNOWN", ""}:
        return "Other"
    return current


def normalize_record(record: dict[str, Any]) -> bool:
    if "draw_family" not in record:
        return False
    before = clean(record.get("draw_family"))
    after = derive_draw_family(record)
    if before == after:
        return False
    record["draw_family"] = after
    return True


def load_json_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("hunt_catalog", "hunts", "records"):
            rows = data.get(key)
            if isinstance(rows, list):
                return rows
    return []


def normalize_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if "draw_family" not in fields:
        return {"file": path.relative_to(ROOT).as_posix(), "kind": "csv", "rows": len(rows), "changed": 0}
    before = Counter(clean(row.get("draw_family")) for row in rows)
    changed = sum(1 for row in rows if normalize_record(row))
    after = Counter(clean(row.get("draw_family")) for row in rows)
    if changed:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "kind": "csv",
        "rows": len(rows),
        "changed": changed,
        "before": dict(sorted(before.items())),
        "after": dict(sorted(after.items())),
    }


def normalize_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = load_json_records(data)
    before = Counter(clean(row.get("draw_family")) for row in rows if isinstance(row, dict))
    changed = sum(1 for row in rows if isinstance(row, dict) and normalize_record(row))
    after = Counter(clean(row.get("draw_family")) for row in rows if isinstance(row, dict))
    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "kind": "json",
        "rows": len(rows),
        "changed": changed,
        "before": dict(sorted(before.items())),
        "after": dict(sorted(after.items())),
    }


def main() -> int:
    reports: list[dict[str, Any]] = []
    for path in CSV_TARGETS:
        if path.exists():
            reports.append(normalize_csv(path))
    for path in JSON_TARGETS:
        if path.exists():
            reports.append(normalize_json(path))
    summary = {
        "changed_files": sum(1 for item in reports if item.get("changed")),
        "changed_rows": sum(int(item.get("changed", 0)) for item in reports),
        "files": reports,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
