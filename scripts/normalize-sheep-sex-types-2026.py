"""Normalize 2026 sheep sex labels to DWR website wording."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
AUDIT_OUT = ROOT / "data_truth/crosswalk_truth/validation/sheep_sex_type_normalization_2026.csv"
SUMMARY_OUT = ROOT / "data_truth/crosswalk_truth/validation/sheep_sex_type_normalization_2026_summary.json"
REPORT_OUT = ROOT / "processed_data/sheep_sex_type_normalization_2026.md"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("\ufeff", "")


def main() -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with DATABASE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = [{key: clean(value) for key, value in row.items()} for row in reader]

    audit_rows = []
    changed_rows = 0
    for row in rows:
        species = row.get("species", "")
        old = row.get("sex_type", "")
        new = old
        reason = ""
        if species == "Desert Bighorn Sheep" and old != "Male Only":
            new = "Male Only"
            reason = "DWR website exposes desert bighorn sheep permit tables as Male Only."
        elif species == "Rocky Mountain Bighorn Sheep" and row.get("hunt_code") != "RE1000" and old != "Ram":
            new = "Ram"
            reason = "DWR website has one ewe hunt; remaining Rocky Mountain bighorn sheep rows are ram/male-only."
        elif row.get("hunt_code") == "RE1000" and old != "Ewe":
            new = "Ewe"
            reason = "RE1000 is the single DWR ewe bighorn sheep hunt."

        if new != old:
            changed_rows += 1
            row["sex_type"] = new
        if species in {"Desert Bighorn Sheep", "Rocky Mountain Bighorn Sheep"}:
            audit_rows.append(
                {
                    "snapshot_utc": timestamp,
                    "hunt_code": row.get("hunt_code", ""),
                    "hunt_name": row.get("hunt_name", ""),
                    "species": species,
                    "old_sex_type": old,
                    "new_sex_type": row.get("sex_type", ""),
                    "changed": str(new != old).lower(),
                    "reason": reason,
                }
            )

    with DATABASE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    audit_fields = [
        "snapshot_utc",
        "hunt_code",
        "hunt_name",
        "species",
        "old_sex_type",
        "new_sex_type",
        "changed",
        "reason",
    ]
    with AUDIT_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(audit_rows)

    counts = Counter((row["species"], row["sex_type"]) for row in rows if row["species"] in {"Desert Bighorn Sheep", "Rocky Mountain Bighorn Sheep"})
    summary = {
        "artifact": "sheep_sex_type_normalization_2026",
        "snapshot_utc": timestamp,
        "database_path": DATABASE.relative_to(ROOT).as_posix(),
        "audit_row_count": len(audit_rows),
        "changed_rows": changed_rows,
        "sex_type_counts": {f"{species}|{sex_type}": count for (species, sex_type), count in sorted(counts.items())},
        "guardrail": "Only RE1000 remains Ewe; desert bighorn sheep rows use Male Only and Rocky Mountain bighorn ram rows use Ram.",
        "outputs": {
            "audit_csv": AUDIT_OUT.relative_to(ROOT).as_posix(),
            "summary_json": SUMMARY_OUT.relative_to(ROOT).as_posix(),
            "report_md": REPORT_OUT.relative_to(ROOT).as_posix(),
        },
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Sheep Sex Type Normalization 2026",
        "",
        f"- Snapshot UTC: `{timestamp}`",
        f"- Changed rows: `{changed_rows}`",
        "",
        "## Sex Type Counts",
        "",
    ]
    for label, count in sorted(summary["sex_type_counts"].items()):
        lines.append(f"- `{label}`: `{count}`")
    REPORT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
