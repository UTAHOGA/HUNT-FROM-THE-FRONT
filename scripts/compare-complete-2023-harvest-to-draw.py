"""Compare complete 2023 harvest-result coverage to 2023 draw-result coverage."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARVEST_DIR = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2024" / "csv" / "Harvest Results"
STANDALONE_HARVEST_FILES = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2024" / "csv" / "2024_antlerless_hr.csv"
]
DRAW_FILES = [
    ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2024" / "csv" / "draw_results_2023_for_2024_long.csv",
    ROOT
    / "pipeline"
    / "RAW"
    / "hunt_unit_database"
    / "2024"
    / "csv"
    / "draw_results_2023_for_2024_UPLOADED_COMBINED_long.csv",
]
DATABASE = ROOT / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"


def read_csv_dict(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def read_active_database() -> dict[str, dict[str, str]]:
    rows, _ = read_csv_dict(DATABASE)
    return {row["hunt_code"].strip(): row for row in rows if row.get("hunt_code", "").strip()}


def normalize_antlerless_hr(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.reader(handle))

    header_index = None
    for index, row in enumerate(raw_rows):
        if len(row) >= 9 and row[0].strip() == "Species" and row[1].strip() == "Hunt #":
            header_index = index
            break
    if header_index is None:
        return [], []

    headers = [
        "reported_hunt_year",
        "model_target_year",
        "species",
        "hunt_code",
        "hunt_name",
        "weapon",
        "permits",
        "harvest_hunters",
        "harvest",
        "harvest_success_percent",
        "harvest_average_days",
        "source_file",
        "parse_status",
        "do_not_use_for_permit_quota",
        "do_not_use_for_p_draw_directly",
    ]
    rows: list[dict[str, str]] = []
    for raw in raw_rows[header_index + 1 :]:
        if len(raw) < 9:
            continue
        hunt_code = raw[1].strip()
        if not hunt_code:
            continue
        rows.append(
            {
                "reported_hunt_year": "2023",
                "model_target_year": "2024",
                "species": raw[0].strip(),
                "hunt_code": hunt_code,
                "hunt_name": raw[2].strip(),
                "weapon": raw[3].strip(),
                "permits": raw[4].strip(),
                "harvest_hunters": raw[5].strip(),
                "harvest": raw[6].strip(),
                "harvest_success_percent": raw[7].strip(),
                "harvest_average_days": raw[8].strip(),
                "source_file": str(path.relative_to(ROOT)),
                "parse_status": "POSITIONAL_HEADER_NORMALIZED",
                "do_not_use_for_permit_quota": "True",
                "do_not_use_for_p_draw_directly": "True",
            }
        )
    return rows, headers


def split_codes(value: str) -> list[str]:
    codes: list[str] = []
    for token in str(value or "").replace(";", "|").split("|"):
        token = token.strip()
        if token:
            codes.append(token)
    return codes


def actual_codes(row: dict[str, str]) -> set[str]:
    out: set[str] = set()
    for key in ["hunt_code", "selected_hunt_code", "HuntNumber", "hunt_number", "huntCode", "code"]:
        if key in row:
            out.update(split_codes(row.get(key, "")))
    return out


def numeric(value: str) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return 0.0


def harvest_files() -> list[Path]:
    files: list[Path] = []
    if HARVEST_DIR.exists():
        files.extend(sorted(HARVEST_DIR.glob("*.csv")))
    for path in STANDALONE_HARVEST_FILES:
        if path.exists() and path not in files:
            files.append(path)
    return files


def file_family(path: Path) -> str:
    name = path.name.lower()
    if "turkey" in name:
        return "turkey"
    if "black_bear" in name:
        return "black_bear"
    if "cougar" in name:
        return "cougar"
    if "antlerless" in name or path.name.lower() == "2024_antlerless_hr.csv":
        return "antlerless"
    if "general_deer" in name:
        return "general_deer"
    if "bighorn" in name or "sheep" in name:
        return "bighorn_sheep"
    if "bison" in name:
        return "bison"
    if "moose" in name:
        return "moose"
    if "goat" in name:
        return "mountain_goat"
    if "pronghorn" in name:
        return "pronghorn"
    if "elk" in name:
        return "elk"
    if "deer" in name:
        return "deer"
    if "summary" in name:
        return "summary"
    return "other"


def load_harvest_index() -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    index: dict[str, dict[str, object]] = {}
    file_rows: list[dict[str, object]] = []
    for path in harvest_files():
        if path.name.lower() == "2024_antlerless_hr.csv":
            rows, headers = normalize_antlerless_hr(path)
        else:
            rows, headers = read_csv_dict(path)
        codes_in_file: set[str] = set()
        for row in rows:
            codes = actual_codes(row)
            if not codes:
                continue
            for code in codes:
                codes_in_file.add(code)
                item = index.setdefault(
                    code,
                    {
                        "hunt_code": code,
                        "harvest_files": set(),
                        "harvest_families": set(),
                        "harvest_species": set(),
                        "harvest_hunt_names": set(),
                        "harvest_rows": 0,
                        "harvest_permits_sum": 0.0,
                        "harvest_hunters_sum": 0.0,
                        "harvest_sum": 0.0,
                        "harvest_success_values": [],
                        "harvest_average_days_values": [],
                        "harvest_satisfaction_values": [],
                    },
                )
                item["harvest_files"].add(str(path.relative_to(ROOT)))  # type: ignore[index]
                item["harvest_families"].add(file_family(path))  # type: ignore[index]
                if row.get("species"):
                    item["harvest_species"].add(row["species"].strip())  # type: ignore[index]
                if row.get("hunt_name"):
                    item["harvest_hunt_names"].add(row["hunt_name"].strip())  # type: ignore[index]
                item["harvest_rows"] = int(item["harvest_rows"]) + 1
                item["harvest_permits_sum"] = float(item["harvest_permits_sum"]) + numeric(
                    row.get("permits") or row.get("permits_or_permits_sold") or row.get("total_permits") or ""
                )
                item["harvest_hunters_sum"] = float(item["harvest_hunters_sum"]) + numeric(
                    row.get("harvest_hunters")
                    or row.get("hunters_afield")
                    or row.get("hunters_afield_or_total_hunters")
                    or row.get("total_hunters")
                    or ""
                )
                item["harvest_sum"] = float(item["harvest_sum"]) + numeric(
                    row.get("harvest") or row.get("total_harvest") or ""
                )
                for field, target in [
                    ("harvest_success_percent", "harvest_success_values"),
                    ("percent_success", "harvest_success_values"),
                    ("harvest_average_days", "harvest_average_days_values"),
                    ("average_days", "harvest_average_days_values"),
                    ("mean_days_afield", "harvest_average_days_values"),
                    ("harvest_satisfaction", "harvest_satisfaction_values"),
                    ("hunter_satisfaction", "harvest_satisfaction_values"),
                ]:
                    if row.get(field, "").strip():
                        item[target].append(numeric(row[field]))  # type: ignore[index]
        file_rows.append(
            {
                "file": str(path.relative_to(ROOT)),
                "family": file_family(path),
                "rows": len(rows),
                "headers": len(headers),
                "unique_hunt_codes": len(codes_in_file),
                "sample_hunt_codes": "|".join(sorted(codes_in_file)[:20]),
            }
        )
    return index, file_rows


def load_draw_index() -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    index: dict[str, dict[str, object]] = {}
    file_rows: list[dict[str, object]] = []
    for path in DRAW_FILES:
        rows, headers = read_csv_dict(path)
        codes_in_file: set[str] = set()
        for row in rows:
            code = row.get("hunt_code", "").strip()
            if not code:
                continue
            codes_in_file.add(code)
            item = index.setdefault(
                code,
                {
                    "hunt_code": code,
                    "draw_files": set(),
                    "draw_species": set(),
                    "draw_hunt_names": set(),
                    "draw_rows": 0,
                    "draw_permits_res": 0.0,
                    "draw_permits_nr": 0.0,
                    "draw_applicants_res": 0.0,
                    "draw_applicants_nr": 0.0,
                },
            )
            item["draw_files"].add(str(path.relative_to(ROOT)))  # type: ignore[index]
            if row.get("species"):
                item["draw_species"].add(row["species"].strip())  # type: ignore[index]
            if row.get("hunt_name"):
                item["draw_hunt_names"].add(row["hunt_name"].strip())  # type: ignore[index]
            item["draw_rows"] = int(item["draw_rows"]) + 1
            permits = numeric(row.get("total_permits", ""))
            applicants = numeric(row.get("eligible_applicants", ""))
            residency = row.get("residency", "").strip().lower()
            if residency == "resident":
                item["draw_permits_res"] = float(item["draw_permits_res"]) + permits
                item["draw_applicants_res"] = float(item["draw_applicants_res"]) + applicants
            elif residency == "nonresident":
                item["draw_permits_nr"] = float(item["draw_permits_nr"]) + permits
                item["draw_applicants_nr"] = float(item["draw_applicants_nr"]) + applicants
        file_rows.append(
            {
                "file": str(path.relative_to(ROOT)),
                "rows": len(rows),
                "headers": len(headers),
                "unique_hunt_codes": len(codes_in_file),
                "sample_hunt_codes": "|".join(sorted(codes_in_file)[:20]),
            }
        )
    return index, file_rows


def mean(values: list[float]) -> str:
    if not values:
        return ""
    return f"{sum(values) / len(values):.3f}".rstrip("0").rstrip(".")


def join_set(value: object) -> str:
    if isinstance(value, set):
        return "|".join(sorted(v for v in value if v))
    return str(value or "")


def main() -> int:
    active = read_active_database()
    harvest, harvest_file_rows = load_harvest_index()
    draw, draw_file_rows = load_draw_index()

    all_codes = sorted(set(harvest) | set(draw))
    comparison_rows: list[dict[str, object]] = []
    for code in all_codes:
        h = harvest.get(code)
        d = draw.get(code)
        db = active.get(code, {})
        bucket = "both" if h and d else "harvest_only" if h else "draw_only"
        row = {
            "hunt_code": code,
            "comparison_bucket": bucket,
            "in_active_database_2026": "YES" if code in active else "NO",
            "database_species": db.get("species", ""),
            "database_hunt_name": db.get("hunt_name", ""),
            "database_hunt_type": db.get("hunt_type", ""),
            "harvest_families": join_set(h.get("harvest_families") if h else set()),
            "harvest_species": join_set(h.get("harvest_species") if h else set()),
            "harvest_hunt_names": join_set(h.get("harvest_hunt_names") if h else set()),
            "harvest_rows": h.get("harvest_rows", 0) if h else 0,
            "harvest_files": join_set(h.get("harvest_files") if h else set()),
            "harvest_permits_sum": h.get("harvest_permits_sum", "") if h else "",
            "harvest_hunters_sum": h.get("harvest_hunters_sum", "") if h else "",
            "harvest_sum": h.get("harvest_sum", "") if h else "",
            "harvest_success_percent_mean": mean(h.get("harvest_success_values", []) if h else []),
            "harvest_average_days_mean": mean(h.get("harvest_average_days_values", []) if h else []),
            "harvest_satisfaction_mean": mean(h.get("harvest_satisfaction_values", []) if h else []),
            "draw_species": join_set(d.get("draw_species") if d else set()),
            "draw_hunt_names": join_set(d.get("draw_hunt_names") if d else set()),
            "draw_rows": d.get("draw_rows", 0) if d else 0,
            "draw_files": join_set(d.get("draw_files") if d else set()),
            "draw_permits_2023_res": d.get("draw_permits_res", "") if d else "",
            "draw_permits_2023_nr": d.get("draw_permits_nr", "") if d else "",
            "draw_permits_2023_total": (
                float(d.get("draw_permits_res", 0)) + float(d.get("draw_permits_nr", 0)) if d else ""
            ),
            "draw_applicants_2023_res": d.get("draw_applicants_res", "") if d else "",
            "draw_applicants_2023_nr": d.get("draw_applicants_nr", "") if d else "",
        }
        comparison_rows.append(row)

    out_dir = ROOT / "processed_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "complete_2023_harvest_vs_draw_comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    harvest_codes = set(harvest)
    draw_codes = set(draw)
    active_codes = set(active)
    bucket_counts = Counter(row["comparison_bucket"] for row in comparison_rows)
    family_counts: dict[str, int] = {}
    for code, item in harvest.items():
        for family in item.get("harvest_families", set()):
            family_counts[str(family)] = family_counts.get(str(family), 0) + 1
    summary = {
        "harvest_files_checked": len(harvest_file_rows),
        "draw_files_checked": len(draw_file_rows),
        "active_database_hunt_codes": len(active_codes),
        "complete_harvest_hunt_codes": len(harvest_codes),
        "draw_odds_hunt_codes": len(draw_codes),
        "both_harvest_and_draw": len(harvest_codes & draw_codes),
        "harvest_only": len(harvest_codes - draw_codes),
        "draw_only": len(draw_codes - harvest_codes),
        "harvest_codes_in_active_database": len(harvest_codes & active_codes),
        "draw_codes_in_active_database": len(draw_codes & active_codes),
        "both_codes_in_active_database": len((harvest_codes & draw_codes) & active_codes),
        "harvest_only_in_active_database": len((harvest_codes - draw_codes) & active_codes),
        "draw_only_in_active_database": len((draw_codes - harvest_codes) & active_codes),
        "bucket_counts": dict(bucket_counts),
        "harvest_family_hunt_code_counts": dict(sorted(family_counts.items())),
        "harvest_only_codes": sorted(harvest_codes - draw_codes),
        "draw_only_codes": sorted(draw_codes - harvest_codes),
        "outputs": {
            "csv": str(csv_path.relative_to(ROOT)),
            "json": "processed_data/complete_2023_harvest_vs_draw_comparison.json",
            "md": "processed_data/complete_2023_harvest_vs_draw_comparison.md",
        },
        "source_notes": [
            "Harvest fields are quality/demand features and must not be used as permit quotas or direct p_draw.",
            "Draw-result fields are point-level odds/history and are the source for permits_2023_draw_res/nr/total.",
            "The malformed 2024_antlerless_hr.csv file is parsed by locating column B as Hunt #.",
        ],
    }
    json_path = out_dir / "complete_2023_harvest_vs_draw_comparison.json"
    json_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "harvest_files": harvest_file_rows,
                "draw_files": draw_file_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    md_lines = [
        "# Complete 2023 Harvest vs Draw Comparison",
        "",
        "## Summary",
    ]
    for key, value in summary.items():
        if key in {"harvest_only_codes", "draw_only_codes"}:
            md_lines.append(f"- {key}: {len(value)} codes")
        elif isinstance(value, dict):
            md_lines.append(f"- {key}: {value}")
        elif isinstance(value, list):
            md_lines.append(f"- {key}: {'; '.join(value)}")
        else:
            md_lines.append(f"- {key}: {value}")
    md_lines += [
        "",
        "## Interpretation",
        "- `both` rows can support both draw-history features and harvest-quality features.",
        "- `harvest_only` rows can support quality/demand features but should not receive draw odds from harvest data.",
        "- `draw_only` rows can support point-ladder/draw-history features but have no harvest-quality row in this harvest database.",
    ]
    (out_dir / "complete_2023_harvest_vs_draw_comparison.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
