from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
HUNT_MASTER = ROOT / "processed_data/hunt_master_enriched.csv"
POINT_LADDER = ROOT / "processed_data/point_ladder_view.csv"
DRAW_REALITY = ROOT / "processed_data/draw_reality_engine.csv"
PREDICTIVE = ROOT / "processed_data/draw_reality_engine_predictive_v2.csv"

OUT_CSV = ROOT / "processed_data/2026_hunt_code_family_gap_scan.csv"
OUT_JSON = ROOT / "processed_data/2026_hunt_code_family_gap_scan_summary.json"
OUT_MD = ROOT / "processed_data/2026_hunt_code_family_gap_scan.md"

SURFACES = {
    "database": DATABASE,
    "hunt_master": HUNT_MASTER,
    "point_ladder": POINT_LADDER,
    "draw_reality": DRAW_REALITY,
    "predictive_v2": PREDICTIVE,
}

PREFIX_LABELS = {
    "BI": "Bison",
    "BR": "Bear",
    "CG": "Cougar",
    "DA": "Antlerless Deer",
    "DB": "Buck Deer",
    "DS": "Desert Bighorn Sheep",
    "EA": "Antlerless Elk",
    "EB": "Bull Elk",
    "EL": "Limited-Entry Elk Reference",
    "EX": "Expo",
    "GO": "Mountain Goat",
    "LD": "Limited Deer Reference",
    "LO": "Limited-Entry Deer Reference",
    "LP": "Limited Pronghorn Reference",
    "MA": "Antlerless Moose",
    "MB": "Bull Moose",
    "PB": "Pronghorn Buck",
    "PD": "Doe Pronghorn",
    "RE": "Rocky Mountain Bighorn Ewe",
    "RS": "Rocky Mountain Bighorn Ram",
    "TK": "Turkey",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def code_prefix(hunt_code: str) -> str:
    match = re.match(r"^[A-Z]+", hunt_code or "")
    return match.group(0) if match else "UNKNOWN"


def code_rows_by_surface() -> dict[str, dict[str, list[dict[str, str]]]]:
    by_surface: dict[str, dict[str, list[dict[str, str]]]] = {}
    for surface, path in SURFACES.items():
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in read_rows(path):
            hunt_code = (row.get("hunt_code") or "").strip()
            if not hunt_code:
                continue
            grouped.setdefault(hunt_code, []).append(row)
        by_surface[surface] = grouped
    return by_surface


def dominant_value(rows: list[dict[str, str]], field: str) -> str:
    values = [row.get(field, "").strip() for row in rows if row.get(field, "").strip()]
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]


def summarize_prefix(prefix: str, by_surface: dict[str, dict[str, list[dict[str, str]]]]) -> dict[str, str]:
    database_codes = {code for code in by_surface["database"] if code_prefix(code) == prefix}
    hunt_master_codes = {code for code in by_surface["hunt_master"] if code_prefix(code) == prefix}
    point_ladder_codes = {code for code in by_surface["point_ladder"] if code_prefix(code) == prefix}
    draw_reality_codes = {code for code in by_surface["draw_reality"] if code_prefix(code) == prefix}
    predictive_codes = {code for code in by_surface["predictive_v2"] if code_prefix(code) == prefix}

    missing_hunt_master = sorted(database_codes - hunt_master_codes)
    missing_point_ladder = sorted(database_codes - point_ladder_codes)
    missing_draw_reality = sorted(database_codes - draw_reality_codes)
    missing_predictive = sorted(database_codes - predictive_codes)
    extra_hunt_master = sorted(hunt_master_codes - database_codes)
    extra_point_ladder = sorted(point_ladder_codes - database_codes)
    extra_draw_reality = sorted(draw_reality_codes - database_codes)
    extra_predictive = sorted(predictive_codes - database_codes)
    missing_required = sorted(set(missing_hunt_master) | set(missing_point_ladder) | set(missing_draw_reality))

    database_rows = [row for code in database_codes for row in by_surface["database"][code]]
    species = dominant_value(database_rows, "species") or PREFIX_LABELS.get(prefix, "")
    hunt_type = dominant_value(database_rows, "hunt_type")

    if missing_required:
        status = "BLOCKED_REQUIRED_REFERENCE_SURFACE"
    elif missing_predictive:
        status = "PREDICTIVE_GAP"
    else:
        status = "RESOLVED"

    return {
        "code_prefix": prefix,
        "label": PREFIX_LABELS.get(prefix, ""),
        "dominant_species": species,
        "dominant_hunt_type": hunt_type,
        "database_code_count": str(len(database_codes)),
        "hunt_master_code_count": str(len(hunt_master_codes)),
        "point_ladder_code_count": str(len(point_ladder_codes)),
        "draw_reality_code_count": str(len(draw_reality_codes)),
        "predictive_v2_code_count": str(len(predictive_codes)),
        "missing_hunt_master_count": str(len(missing_hunt_master)),
        "missing_point_ladder_count": str(len(missing_point_ladder)),
        "missing_draw_reality_count": str(len(missing_draw_reality)),
        "missing_predictive_v2_count": str(len(missing_predictive)),
        "extra_hunt_master_not_database_count": str(len(extra_hunt_master)),
        "extra_point_ladder_not_database_count": str(len(extra_point_ladder)),
        "extra_draw_reality_not_database_count": str(len(extra_draw_reality)),
        "extra_predictive_v2_not_database_count": str(len(extra_predictive)),
        "missing_hunt_master_codes": ";".join(missing_hunt_master),
        "missing_point_ladder_codes": ";".join(missing_point_ladder),
        "missing_draw_reality_codes": ";".join(missing_draw_reality),
        "missing_predictive_v2_codes": ";".join(missing_predictive),
        "extra_hunt_master_not_database_codes": ";".join(extra_hunt_master),
        "extra_point_ladder_not_database_codes": ";".join(extra_point_ladder),
        "extra_draw_reality_not_database_codes": ";".join(extra_draw_reality),
        "extra_predictive_v2_not_database_codes": ";".join(extra_predictive),
        "status": status,
    }


def main() -> int:
    by_surface = code_rows_by_surface()
    prefixes = sorted({code_prefix(code) for surface in by_surface.values() for code in surface})
    rows = [summarize_prefix(prefix, by_surface) for prefix in prefixes]
    rows.sort(key=lambda row: (-int(row["missing_predictive_v2_count"]), row["code_prefix"]))

    fieldnames = [
        "code_prefix",
        "label",
        "dominant_species",
        "dominant_hunt_type",
        "database_code_count",
        "hunt_master_code_count",
        "point_ladder_code_count",
        "draw_reality_code_count",
        "predictive_v2_code_count",
        "missing_hunt_master_count",
        "missing_point_ladder_count",
        "missing_draw_reality_count",
        "missing_predictive_v2_count",
        "extra_hunt_master_not_database_count",
        "extra_point_ladder_not_database_count",
        "extra_draw_reality_not_database_count",
        "extra_predictive_v2_not_database_count",
        "missing_hunt_master_codes",
        "missing_point_ladder_codes",
        "missing_draw_reality_codes",
        "missing_predictive_v2_codes",
        "extra_hunt_master_not_database_codes",
        "extra_point_ladder_not_database_codes",
        "extra_draw_reality_not_database_codes",
        "extra_predictive_v2_not_database_codes",
        "status",
    ]
    write_rows(OUT_CSV, fieldnames, rows)

    unresolved_predictive = [row for row in rows if int(row["missing_predictive_v2_count"])]
    required_surface_blockers = [
        row
        for row in rows
        if int(row["missing_hunt_master_count"]) or int(row["missing_point_ladder_count"]) or int(row["missing_draw_reality_count"])
    ]
    resolved = [row for row in rows if row["status"] == "RESOLVED"]

    summary = {
        "classification": "CURRENT_2026_HUNT_CODE_FAMILY_GAP_SCAN",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "database_code_count": len(by_surface["database"]),
        "hunt_master_code_count": len(by_surface["hunt_master"]),
        "point_ladder_code_count": len(by_surface["point_ladder"]),
        "draw_reality_code_count": len(by_surface["draw_reality"]),
        "predictive_v2_code_count": len(by_surface["predictive_v2"]),
        "family_count": len(rows),
        "resolved_family_count": len(resolved),
        "predictive_gap_family_count": len(unresolved_predictive),
        "required_surface_blocker_family_count": len(required_surface_blockers),
        "total_missing_predictive_v2_current_database_codes": sum(int(row["missing_predictive_v2_count"]) for row in rows),
        "total_required_surface_missing_current_database_codes": sum(
            int(row["missing_hunt_master_count"]) + int(row["missing_point_ladder_count"]) + int(row["missing_draw_reality_count"])
            for row in rows
        ),
        "resolved_families": [row["code_prefix"] for row in resolved],
        "predictive_gap_families_ranked": [
            {
                "code_prefix": row["code_prefix"],
                "label": row["label"],
                "dominant_species": row["dominant_species"],
                "missing_predictive_v2_count": int(row["missing_predictive_v2_count"]),
                "database_code_count": int(row["database_code_count"]),
                "missing_predictive_v2_codes": row["missing_predictive_v2_codes"].split(";") if row["missing_predictive_v2_codes"] else [],
            }
            for row in unresolved_predictive
        ],
        "required_surface_blocker_families": [
            {
                "code_prefix": row["code_prefix"],
                "label": row["label"],
                "missing_hunt_master_count": int(row["missing_hunt_master_count"]),
                "missing_point_ladder_count": int(row["missing_point_ladder_count"]),
                "missing_draw_reality_count": int(row["missing_draw_reality_count"]),
            }
            for row in required_surface_blockers
        ],
        "guardrail": "Gap scan is read-only except for audit outputs; it does not promote rows or change prediction math.",
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    top_gap_lines = [
        f"- `{item['code_prefix']}` {item['label'] or item['dominant_species']}: `{item['missing_predictive_v2_count']}` missing predictive v2 codes"
        for item in summary["predictive_gap_families_ranked"][:10]
    ]
    OUT_MD.write_text(
        "\n".join(
            [
                "# 2026 Hunt-Code Family Gap Scan",
                "",
                f"- Current DATABASE code count: `{summary['database_code_count']}`",
                f"- Predictive v2 code count: `{summary['predictive_v2_code_count']}`",
                f"- Families scanned: `{summary['family_count']}`",
                f"- Fully resolved families: `{summary['resolved_family_count']}`",
                f"- Families with predictive v2 gaps: `{summary['predictive_gap_family_count']}`",
                f"- Required-surface blocker families: `{summary['required_surface_blocker_family_count']}`",
                f"- Current DATABASE codes missing predictive v2: `{summary['total_missing_predictive_v2_current_database_codes']}`",
                "",
                "## Largest Predictive Gaps",
                "",
                *(top_gap_lines or ["- None"]),
                "",
                "This scan only identifies gaps. It does not promote reference rows or alter draw-odds math.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return 1 if required_surface_blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
