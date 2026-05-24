from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDEBOOK_AUDIT = ROOT / "scripts/audit-big-game-application-guidebook-2026.py"
GUIDEBOOK_TABLES = ROOT / "data_truth/regulations_truth/normalized/2026_big_game_application_guidebook_hunt_tables.csv"
DATABASE = ROOT / "pipeline/RAW/hunt_unit_database/2026/csv/DATABASE.csv"
PROCESSED = ROOT / "processed_data"

OUTPUT_CSV = PROCESSED / "2026_big_game_hunt_code_reconciliation.csv"
OUTPUT_JSON = PROCESSED / "2026_big_game_hunt_code_reconciliation_summary.json"
OUTPUT_MD = PROCESSED / "2026_big_game_hunt_code_reconciliation.md"

REQUIRED_SURFACES = {
    "DATABASE": DATABASE,
    "hunt_master_enriched": PROCESSED / "hunt_master_enriched.csv",
    "hunt_unit_reference_linked": PROCESSED / "hunt_unit_reference_linked.csv",
    "point_ladder_view": PROCESSED / "point_ladder_view.csv",
    "draw_reality_engine": PROCESSED / "draw_reality_engine.csv",
}

OPTIONAL_SURFACES = {
    "draw_reality_engine_predictive_v2": PROCESSED / "draw_reality_engine_predictive_v2.csv",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def code_from_row(row: dict[str, str]) -> str:
    return clean(row.get("hunt_code") or row.get("HuntCode") or row.get("code")).upper()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def code_set(path: Path) -> set[str]:
    return {code for code in (code_from_row(row) for row in read_csv_rows(path)) if code}


def build_reconciliation_rows() -> tuple[list[dict[str, str]], dict[str, set[str]], dict[str, set[str]]]:
    subprocess.run([sys.executable, str(GUIDEBOOK_AUDIT.relative_to(ROOT))], cwd=ROOT, check=True)

    guidebook_rows = read_csv_rows(GUIDEBOOK_TABLES)
    required_codes = {name: code_set(path) for name, path in REQUIRED_SURFACES.items()}
    optional_codes = {name: code_set(path) for name, path in OPTIONAL_SURFACES.items()}

    rows: list[dict[str, str]] = []
    for row in sorted(guidebook_rows, key=lambda item: item["hunt_code"]):
        code = row["hunt_code"]
        missing_required = [name for name, codes in required_codes.items() if code not in codes]
        missing_optional = [name for name, codes in optional_codes.items() if code not in codes]
        rows.append(
            {
                "hunt_code": code,
                "guidebook_page": row["guidebook_page"],
                "guidebook_section": row["guidebook_section"],
                "species_inferred": row["species_inferred"],
                "guidebook_hunt_name": row["guidebook_hunt_name"],
                "required_surface_status": "PASS" if not missing_required else "BLOCKER",
                "missing_required_surfaces": ";".join(missing_required),
                "optional_predictive_status": "PASS" if not missing_optional else "INFO_MISSING_PREDICTIVE_ROW",
                "missing_optional_surfaces": ";".join(missing_optional),
                **{f"in_{name}": str(code in codes).lower() for name, codes in required_codes.items()},
                **{f"in_{name}": str(code in codes).lower() for name, codes in optional_codes.items()},
            }
        )
    return rows, required_codes, optional_codes


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(summary: dict[str, object], rows: list[dict[str, str]]) -> None:
    blockers = [row for row in rows if row["required_surface_status"] != "PASS"]
    optional_missing = [row for row in rows if row["optional_predictive_status"] != "PASS"]
    lines = [
        "# 2026 Big Game Hunt Code Reconciliation",
        "",
        "This checks hunt-code presence from the corrected 2026 Big Game Application Guidebook against the core source/database/runtime reference surfaces.",
        "",
        "## Result",
        "",
        f"- Guidebook hunt codes checked: `{summary['guidebook_hunt_codes']}`",
        f"- Required-surface blocker count: `{summary['required_surface_blocker_count']}`",
        f"- Codes present in every required surface: `{summary['codes_present_in_all_required_surfaces']}`",
        f"- Optional predictive rows missing: `{summary['optional_predictive_missing_count']}`",
        f"- Extra DATABASE codes not in guidebook: `{summary['extra_database_codes_not_in_guidebook']}`",
        "",
        "Required surfaces: `DATABASE.csv`, `hunt_master_enriched.csv`, `hunt_unit_reference_linked.csv`, `point_ladder_view.csv`, `draw_reality_engine.csv`.",
        "",
        "Optional predictive surface: `draw_reality_engine_predictive_v2.csv`. Missing optional rows are coverage notes, not source-code reconciliation blockers.",
        "",
    ]
    if blockers:
        lines.extend(["## Required Blockers", "", "| hunt_code | missing required surfaces |", "|---|---|"])
        for row in blockers:
            lines.append(f"| {row['hunt_code']} | {row['missing_required_surfaces']} |")
        lines.append("")
    else:
        lines.extend(["## Required Blockers", "", "None. All guidebook hunt codes are present in every required surface.", ""])

    if optional_missing:
        lines.extend(["## Optional Predictive Coverage Notes", "", "| hunt_code | guidebook hunt name | missing optional surfaces |", "|---|---|---|"])
        for row in optional_missing[:75]:
            lines.append(
                f"| {row['hunt_code']} | {row['guidebook_hunt_name']} | {row['missing_optional_surfaces']} |"
            )
        lines.append("")

    lines.append("Full row-level output: `processed_data/2026_big_game_hunt_code_reconciliation.csv`")
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows, required_codes, optional_codes = build_reconciliation_rows()
    guidebook_codes = {row["hunt_code"] for row in rows}
    status_counts = Counter(row["required_surface_status"] for row in rows)
    optional_counts = Counter(row["optional_predictive_status"] for row in rows)
    required_missing_by_surface = {
        name: sum(1 for row in rows if row[f"in_{name}"] != "true") for name in REQUIRED_SURFACES
    }
    optional_missing_by_surface = {
        name: sum(1 for row in rows if row[f"in_{name}"] != "true") for name in OPTIONAL_SURFACES
    }

    summary: dict[str, object] = {
        "guidebook_hunt_codes": len(guidebook_codes),
        "codes_present_in_all_required_surfaces": status_counts.get("PASS", 0),
        "required_surface_blocker_count": status_counts.get("BLOCKER", 0),
        "required_surface_status_counts": dict(status_counts),
        "required_missing_by_surface": required_missing_by_surface,
        "optional_predictive_missing_count": optional_counts.get("INFO_MISSING_PREDICTIVE_ROW", 0),
        "optional_status_counts": dict(optional_counts),
        "optional_missing_by_surface": optional_missing_by_surface,
        "required_surface_code_counts": {name: len(codes) for name, codes in required_codes.items()},
        "optional_surface_code_counts": {name: len(codes) for name, codes in optional_codes.items()},
        "extra_database_codes_not_in_guidebook": len(required_codes["DATABASE"] - guidebook_codes),
        "extra_database_code_note": "Expected: DATABASE includes antlerless, other current-year rows, and broader active references not printed in the big-game application hunt tables.",
        "classification": "BIG_GAME_HUNT_CODE_RECONCILIATION",
        "modeling_guardrail": "DO_NOT_CHANGE_PREDICTION_MATH_OR_PERMIT_VALUES",
    }

    write_csv(OUTPUT_CSV, rows)
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
