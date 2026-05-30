"""Apply deer buck draw-class normalization rules to a CSV file.

Rules:
1. Sportsman rows -> hunt_type=L.E., hunt_class=sportsmens, permits total=1
2. Conservation rows -> hunt_type=conservation
3. Expo rows -> hunt_class=expo and (if not conservation) hunt_type=L.E.
4. Private-land rows -> hunt_type=L.E., hunt_class=private only

Precedence:
sportsman > conservation > expo > private
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def row_text(row: dict[str, str]) -> str:
    return " | ".join(
        [
            upper(row.get("hunt_name")),
            upper(row.get("hunt_code")),
            upper(row.get("hunt_type")),
            upper(row.get("hunt_class")),
            upper(row.get("season")),
        ]
    )


def detect_flags(row: dict[str, str]) -> tuple[bool, bool, bool, bool]:
    text = row_text(row)
    code = upper(row.get("hunt_code"))
    is_sportsman = (
        "SPORTSMAN" in text
        or "SPORTSMEN" in text
        or "SPORTSMENS" in text
        or "STATEWIDE PERMIT" in text
    )
    is_conservation = "CONSERVATION" in text
    is_expo = "EXPO" in text
    is_private = (
        "PRIVATE LAND" in text
        or "PRIVATE LANDS" in text
        or code.startswith("LD")
        or code.startswith("LO")
    )
    return is_sportsman, is_conservation, is_expo, is_private


def apply_rules(row: dict[str, str]) -> tuple[str, dict[str, str], dict[str, str]]:
    before = {
        "hunt_type": clean(row.get("hunt_type")),
        "hunt_class": clean(row.get("hunt_class")),
        "permits_total": clean(row.get("2026 permits total")),
    }
    is_sportsman, is_conservation, is_expo, is_private = detect_flags(row)

    rule = ""
    if is_sportsman:
        rule = "sportsman"
        row["hunt_type"] = "L.E."
        row["hunt_class"] = "sportsmens"
        row["2026 permits total"] = "1"
    elif is_conservation:
        rule = "conservation"
        row["hunt_type"] = "conservation"
        if is_expo:
            row["hunt_class"] = "expo"
    elif is_expo:
        rule = "expo"
        row["hunt_type"] = "L.E."
        row["hunt_class"] = "expo"
    elif is_private:
        rule = "private"
        row["hunt_type"] = "L.E."
        row["hunt_class"] = "private only"

    after = {
        "hunt_type": clean(row.get("hunt_type")),
        "hunt_class": clean(row.get("hunt_class")),
        "permits_total": clean(row.get("2026 permits total")),
    }
    return rule, before, after


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to target CSV file (for example: 2026 deer buck db.csv).",
    )
    parser.add_argument("--write", action="store_true", help="Write changes to file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    changes = []
    rule_counts: Counter[str] = Counter()
    for index, row in enumerate(rows, start=2):
        rule, before, after = apply_rules(row)
        if rule:
            rule_counts[rule] += 1
        if before != after:
            changes.append(
                {
                    "line": index,
                    "hunt_code": clean(row.get("hunt_code")).upper(),
                    "rule": rule,
                    "before": before,
                    "after": after,
                }
            )

    backup_path = ""
    if args.write and changes:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = str(csv_path.with_name(f"{csv_path.stem}.backup_drawclass_rules_{stamp}{csv_path.suffix}"))
        shutil.copy2(csv_path, backup_path)
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    report = {
        "file": str(csv_path),
        "mode": "write" if args.write else "dry_run",
        "rows_checked": len(rows),
        "rows_changed": len(changes),
        "rules_triggered": dict(rule_counts),
        "backup_file": backup_path,
        "sample_changes": changes[:40],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
