import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


REPO = Path(__file__).resolve().parents[1]
MASTER_PATH = REPO / "processed_data" / "harvest_master.csv"
FEATURES_PATH = REPO / "processed_data" / "harvest_quality_features_all_years_by_hunt_code.csv"


def normalize_code(value: str) -> str:
    return "".join(ch for ch in str(value or "").upper().strip() if ch.isalnum())


def to_int(value):
    try:
        text = str(value or "").strip()
        if not text:
            return None
        return int(float(text))
    except Exception:
        return None


def has_value(value) -> bool:
    return str(value or "").strip() != ""


def score_row(row: dict, fields: List[str]) -> int:
    return sum(1 for field in fields if has_value(row.get(field)))


def read_csv(path: Path) -> Tuple[List[str], List[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return reader.fieldnames or [], rows


def write_csv(path: Path, fieldnames: List[str], rows: List[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def pick_best_feature(rows: List[dict]) -> dict:
    if not rows:
        return {}
    return max(
        rows,
        key=lambda row: (
            score_row(row, ["percent_success", "average_days", "hunter_satisfaction", "permits", "hunters_afield", "harvest_total"]),
            to_int(row.get("reported_hunt_year")) or 0,
        ),
    )


def pick_best_master(rows: List[dict]) -> dict:
    if not rows:
        return {}
    return max(
        rows,
        key=lambda row: (
            score_row(row, ["percent_success", "avg_days", "satisfaction", "permits_total", "hunters", "harvest"]),
            to_int(row.get("year")) or 0,
        ),
    )


def build_feature_index(feature_rows: List[dict]) -> Dict[Tuple[str, int], List[dict]]:
    idx: Dict[Tuple[str, int], List[dict]] = {}
    for row in feature_rows:
        code = normalize_code(row.get("hunt_code"))
        year = to_int(row.get("reported_hunt_year"))
        if not code or year is None:
            continue
        idx.setdefault((code, year), []).append(row)
    return idx


def build_master_index(master_rows: List[dict]) -> Dict[Tuple[str, int], List[dict]]:
    idx: Dict[Tuple[str, int], List[dict]] = {}
    for row in master_rows:
        code = normalize_code(row.get("hunt_code"))
        year = to_int(row.get("year"))
        if not code or year is None:
            continue
        idx.setdefault((code, year), []).append(row)
    return idx


def sync_master_from_features(master_rows: List[dict], feature_idx: Dict[Tuple[str, int], List[dict]]) -> dict:
    updates = {
        "percent_success": 0,
        "avg_days": 0,
        "satisfaction": 0,
        "rows_touched": 0,
    }
    touched_ids = set()

    for i, row in enumerate(master_rows):
        code = normalize_code(row.get("hunt_code"))
        year = to_int(row.get("year"))
        if not code or year is None:
            continue

        feature = pick_best_feature(feature_idx.get((code, year), []))
        if not feature:
            continue

        row_touched = False
        if not has_value(row.get("percent_success")) and has_value(feature.get("percent_success")):
            row["percent_success"] = feature.get("percent_success", "")
            updates["percent_success"] += 1
            row_touched = True
        if not has_value(row.get("avg_days")) and has_value(feature.get("average_days")):
            row["avg_days"] = feature.get("average_days", "")
            updates["avg_days"] += 1
            row_touched = True
        if not has_value(row.get("satisfaction")) and has_value(feature.get("hunter_satisfaction")):
            row["satisfaction"] = feature.get("hunter_satisfaction", "")
            updates["satisfaction"] += 1
            row_touched = True

        if row_touched:
            touched_ids.add(i)

    updates["rows_touched"] = len(touched_ids)
    return updates


def sync_features_from_master(feature_rows: List[dict], master_idx: Dict[Tuple[str, int], List[dict]]) -> dict:
    updates = {
        "percent_success": 0,
        "average_days": 0,
        "hunter_satisfaction": 0,
        "permits": 0,
        "hunters_afield": 0,
        "harvest_total": 0,
        "rows_touched": 0,
    }
    touched_ids = set()

    for i, row in enumerate(feature_rows):
        code = normalize_code(row.get("hunt_code"))
        year = to_int(row.get("reported_hunt_year"))
        if not code or year is None:
            continue

        master = pick_best_master(master_idx.get((code, year), []))
        if not master:
            continue

        row_touched = False
        if not has_value(row.get("percent_success")) and has_value(master.get("percent_success")):
            row["percent_success"] = master.get("percent_success", "")
            updates["percent_success"] += 1
            row_touched = True
        if not has_value(row.get("average_days")) and has_value(master.get("avg_days")):
            row["average_days"] = master.get("avg_days", "")
            updates["average_days"] += 1
            row_touched = True
        if not has_value(row.get("hunter_satisfaction")) and has_value(master.get("satisfaction")):
            row["hunter_satisfaction"] = master.get("satisfaction", "")
            updates["hunter_satisfaction"] += 1
            row_touched = True
        if not has_value(row.get("permits")) and has_value(master.get("permits_total")):
            row["permits"] = master.get("permits_total", "")
            updates["permits"] += 1
            row_touched = True
        if not has_value(row.get("hunters_afield")) and has_value(master.get("hunters")):
            row["hunters_afield"] = master.get("hunters", "")
            updates["hunters_afield"] += 1
            row_touched = True
        if not has_value(row.get("harvest_total")) and has_value(master.get("harvest")):
            row["harvest_total"] = master.get("harvest", "")
            updates["harvest_total"] += 1
            row_touched = True

        if row_touched:
            touched_ids.add(i)

    updates["rows_touched"] = len(touched_ids)
    return updates


def count_missing(rows: List[dict], columns: List[str]) -> dict:
    out = {"rows": len(rows)}
    for column in columns:
        missing = sum(1 for row in rows if not has_value(row.get(column)))
        out[column] = {"filled": len(rows) - missing, "missing": missing}
    return out


def main() -> None:
    master_fields, master_rows = read_csv(MASTER_PATH)
    feature_fields, feature_rows = read_csv(FEATURES_PATH)

    before = {
        "master": count_missing(master_rows, ["percent_success", "avg_days", "satisfaction"]),
        "features": count_missing(feature_rows, ["percent_success", "average_days", "hunter_satisfaction", "permits", "hunters_afield", "harvest_total", "average_age"]),
    }

    feature_idx = build_feature_index(feature_rows)
    master_idx = build_master_index(master_rows)

    master_updates = sync_master_from_features(master_rows, feature_idx)
    feature_updates = sync_features_from_master(feature_rows, master_idx)

    write_csv(MASTER_PATH, master_fields, master_rows)
    write_csv(FEATURES_PATH, feature_fields, feature_rows)

    after = {
        "master": count_missing(master_rows, ["percent_success", "avg_days", "satisfaction"]),
        "features": count_missing(feature_rows, ["percent_success", "average_days", "hunter_satisfaction", "permits", "hunters_afield", "harvest_total", "average_age"]),
    }

    print(json.dumps(
        {
            "ok": True,
            "files": {
                "master": str(MASTER_PATH.relative_to(REPO)).replace("\\", "/"),
                "features": str(FEATURES_PATH.relative_to(REPO)).replace("\\", "/"),
            },
            "before": before,
            "master_updates_from_features": master_updates,
            "feature_updates_from_master": feature_updates,
            "after": after,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
