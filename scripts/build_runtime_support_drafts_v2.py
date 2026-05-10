import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
INPUT_DATABASE = REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv" / "DATABASE.csv"
INPUT_DRAW_V2 = REPO / "data_model" / "runtime_drafts" / "draw_reality_engine_v2.csv"
INPUT_POINT_LADDER = REPO / "processed_data" / "point_ladder_view.csv"
INPUT_ENRICHED = REPO / "processed_data" / "hunt_master_enriched.csv"
INPUT_REF_LINKED = REPO / "processed_data" / "hunt_unit_reference_linked.csv"

OUT_DIR = REPO / "data_model" / "runtime_drafts"
OUT_PERMITS = OUT_DIR / "permits_2026_online.csv"
OUT_POINT_LADDER = OUT_DIR / "point_ladder_view_v2.csv"
OUT_ENRICHED = OUT_DIR / "hunt_master_enriched_v2.csv"
OUT_CROSSWALK = OUT_DIR / "hunt_boundary_crosswalk_v2.csv"
OUT_REPORT = OUT_DIR / "runtime_feed_sync_report.json"
OUT_SUMMARY = OUT_DIR / "runtime_feed_sync_summary.csv"

IDENTITY_FIELDS = [
    "hunt_code",
    "boundary_id",
    "hunt_name",
    "species",
    "sex_type",
    "hunt_type",
    "weapon",
    "hunt_class",
    "season",
    "permits_2026_res",
    "permits_2026_nr",
    "permits_2026_total",
]

PROMOTION_BLOCKERS = [
    "DRAFT_ONLY_NOT_PUBLISHED",
    "PROCESSED_DATA_NOT_UPDATED",
    "WEBSITE_LOADER_MUST_SUPPORT_DRAW_POOL",
    "DO_NOT_MERGE_HISTORICAL_DATABASE_YEARS_INTO_2026",
]


def clean(v):
    return "" if v is None else str(v).strip()


def nint(v):
    t = clean(v)
    if not t:
        return ""
    try:
        return str(int(float(t)))
    except Exception:
        return ""


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def get_hunt_class_map(draw_v2_rows):
    by_code = defaultdict(Counter)
    for row in draw_v2_rows:
        code = clean(row.get("hunt_code")).upper()
        hc = clean(row.get("hunt_class"))
        if code and hc:
            by_code[code][hc] += 1
    out = {}
    for code, ctr in by_code.items():
        out[code] = ctr.most_common(1)[0][0]
    return out


def build_database_truth(draw_v2_rows):
    db_rows = read_csv(INPUT_DATABASE)
    hunt_class_map = get_hunt_class_map(draw_v2_rows)

    truth = {}
    invalid_rows = 0
    for row in db_rows:
        code = clean(row.get("hunt_code")).upper()
        if not code:
            invalid_rows += 1
            continue
        truth[code] = {
            "hunt_code": code,
            "boundary_id": nint(row.get("boundary_id")),
            "hunt_name": clean(row.get("hunt_name")),
            "species": clean(row.get("species")),
            "sex_type": clean(row.get("sex_type")),
            "hunt_type": clean(row.get("hunt_type")),
            "weapon": clean(row.get("weapon")),
            "hunt_class": hunt_class_map.get(code, "Public"),
            "season": clean(row.get("season")),
            "permits_2026_res": nint(row.get("permits_2026_res")),
            "permits_2026_nr": nint(row.get("permits_2026_nr")),
            "permits_2026_total": nint(row.get("permits_2026_total")),
            "notes": clean(row.get("NOTES")),
        }
    return truth, invalid_rows


def permit_status(truth_row):
    res = nint(truth_row.get("permits_2026_res"))
    nr = nint(truth_row.get("permits_2026_nr"))
    total = nint(truth_row.get("permits_2026_total"))
    if not res and not nr and not total:
        return "NO_QUOTA_PUBLISHED"
    if total and not res and not nr:
        return "TOTAL_ONLY_SPLIT_MISSING"
    if not total and (res or nr):
        return "CALCULATED_TOTAL_FROM_SPLIT"
    if total and (res or nr):
        calc = (int(res or "0") + int(nr or "0"))
        if calc != int(total):
            return "PERMIT_MATH_CONFLICT"
        return "OK"
    return "NO_QUOTA_PUBLISHED"


def schema_changes(old_headers, new_headers):
    old_set = set(old_headers)
    new_set = set(new_headers)
    return {
        "added_columns": [c for c in new_headers if c not in old_set],
        "removed_columns": [c for c in old_headers if c not in new_set],
        "reordered_columns": old_headers != new_headers,
    }


def apply_identity_sync(
    source_rows, source_headers, truth, source_name, require_points_dedupe=False
):
    rows = []
    dropped_invalid_code = 0
    dropped_duplicates = 0
    seen = set()

    for src in source_rows:
        code = clean(src.get("hunt_code")).upper()
        if not code or code not in truth:
            dropped_invalid_code += 1
            continue

        key = None
        if require_points_dedupe:
            pts = clean(src.get("points"))
            if pts != "":
                key = (code, clean(src.get("residency")), pts)
        else:
            key = (code, clean(src.get("residency")), clean(src.get("points")))

        if key in seen:
            dropped_duplicates += 1
            continue
        seen.add(key)

        t = truth[code]
        merged = {k: clean(v) for k, v in src.items()}
        # sync identity truth fields
        for f in IDENTITY_FIELDS:
            merged[f] = clean(t.get(f))
        rows.append(merged)

    remaining_headers = [h for h in source_headers if h not in IDENTITY_FIELDS]
    new_headers = IDENTITY_FIELDS + remaining_headers
    for row in rows:
        for h in new_headers:
            if h not in row:
                row[h] = ""

    # post validations
    boundary_missing = sum(1 for r in rows if not clean(r.get("boundary_id")))
    dup_key_count = 0
    key_counter = Counter()
    for r in rows:
        k = (clean(r.get("hunt_code")), clean(r.get("residency")), clean(r.get("points")))
        key_counter[k] += 1
    dup_key_count = sum(1 for _, c in key_counter.items() if c > 1)

    return {
        "rows": rows,
        "headers": new_headers,
        "dropped_invalid_code": dropped_invalid_code,
        "dropped_duplicates": dropped_duplicates,
        "boundary_missing": boundary_missing,
        "dup_hunt_res_points": dup_key_count,
        "schema_changes": schema_changes(source_headers, new_headers),
        "source_name": source_name,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    draw_v2_rows = read_csv(INPUT_DRAW_V2)
    point_rows = read_csv(INPUT_POINT_LADDER)
    enriched_rows = read_csv(INPUT_ENRICHED)
    ref_rows = read_csv(INPUT_REF_LINKED)
    point_headers = list(point_rows[0].keys()) if point_rows else []
    enriched_headers = list(enriched_rows[0].keys()) if enriched_rows else []
    ref_headers = list(ref_rows[0].keys()) if ref_rows else []

    truth, invalid_db_rows = build_database_truth(draw_v2_rows)
    valid_codes = sorted(truth.keys())

    # permits_2026_online.csv
    permit_rows = []
    permit_status_counts = Counter()
    permit_math_conflicts = 0
    for code in valid_codes:
        t = truth[code]
        status = permit_status(t)
        if status == "CALCULATED_TOTAL_FROM_SPLIT":
            calc_total = int(t["permits_2026_res"] or "0") + int(t["permits_2026_nr"] or "0")
            t_total = str(calc_total)
        else:
            t_total = t["permits_2026_total"]
        row = dict(t)
        row["permits_2026_total"] = t_total
        row["permit_status"] = status
        row["permit_validation_notes"] = ""
        permit_rows.append(row)
        permit_status_counts[status] += 1
        if status == "PERMIT_MATH_CONFLICT":
            permit_math_conflicts += 1

    permits_headers = IDENTITY_FIELDS + ["permit_status", "permit_validation_notes", "notes"]
    write_csv(OUT_PERMITS, permits_headers, permit_rows)

    # point_ladder_view_v2
    point_sync = apply_identity_sync(
        point_rows, point_headers, truth, "processed_data/point_ladder_view.csv", require_points_dedupe=False
    )
    write_csv(OUT_POINT_LADDER, point_sync["headers"], point_sync["rows"])

    # hunt_master_enriched_v2
    enriched_sync = apply_identity_sync(
        enriched_rows, enriched_headers, truth, "processed_data/hunt_master_enriched.csv", require_points_dedupe=True
    )
    write_csv(OUT_ENRICHED, enriched_sync["headers"], enriched_sync["rows"])

    # hunt_boundary_crosswalk_v2 (one row per valid DATABASE hunt code)
    crosswalk_rows = []
    ref_by_code = {}
    for r in ref_rows:
        c = clean(r.get("hunt_code")).upper()
        if c and c not in ref_by_code:
            ref_by_code[c] = r

    for code in valid_codes:
        t = truth[code]
        rr = ref_by_code.get(code, {})
        crosswalk_rows.append(
            {
                "hunt_code": t["hunt_code"],
                "boundary_id": t["boundary_id"],
                "hunt_name": t["hunt_name"],
                "species": t["species"],
                "sex_type": t["sex_type"],
                "hunt_type": t["hunt_type"],
                "weapon": t["weapon"],
                "hunt_class": t["hunt_class"],
                "season": t["season"],
                "permits_2026_res": t["permits_2026_res"],
                "permits_2026_nr": t["permits_2026_nr"],
                "permits_2026_total": t["permits_2026_total"],
                "permit_status": permit_status(t),
                "source_file_2026": clean(rr.get("source_file_2026")),
                "link_key": clean(rr.get("link_key")),
            }
        )
    crosswalk_headers = IDENTITY_FIELDS + ["permit_status", "source_file_2026", "link_key"]
    write_csv(OUT_CROSSWALK, crosswalk_headers, crosswalk_rows)

    # validations
    permits_blank_code = sum(1 for r in permit_rows if not clean(r.get("hunt_code")))
    permits_dupe_code = len(permit_rows) - len({clean(r.get("hunt_code")) for r in permit_rows})
    permits_boundary_missing = sum(1 for r in permit_rows if not clean(r.get("boundary_id")))

    crosswalk_dupe_code = len(crosswalk_rows) - len({clean(r.get("hunt_code")) for r in crosswalk_rows})
    crosswalk_boundary_missing = sum(1 for r in crosswalk_rows if not clean(r.get("boundary_id")))

    # duplicate boundary_id allowed; still count
    crosswalk_dup_boundary = len(crosswalk_rows) - len({clean(r.get("boundary_id")) for r in crosswalk_rows})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs_used": [
            str(INPUT_DATABASE.relative_to(REPO)).replace("\\", "/"),
            str(INPUT_DRAW_V2.relative_to(REPO)).replace("\\", "/"),
            str(INPUT_POINT_LADDER.relative_to(REPO)).replace("\\", "/"),
            str(INPUT_ENRICHED.relative_to(REPO)).replace("\\", "/"),
            str(INPUT_REF_LINKED.relative_to(REPO)).replace("\\", "/"),
        ],
        "outputs_created": [
            str(OUT_PERMITS.relative_to(REPO)).replace("\\", "/"),
            str(OUT_POINT_LADDER.relative_to(REPO)).replace("\\", "/"),
            str(OUT_ENRICHED.relative_to(REPO)).replace("\\", "/"),
            str(OUT_CROSSWALK.relative_to(REPO)).replace("\\", "/"),
            str(OUT_REPORT.relative_to(REPO)).replace("\\", "/"),
            str(OUT_SUMMARY.relative_to(REPO)).replace("\\", "/"),
        ],
        "database_truth": {
            "valid_2026_hunt_codes": len(valid_codes),
            "invalid_database_rows_without_hunt_code": invalid_db_rows,
            "boundary_id_missing_in_truth": sum(1 for c in valid_codes if not clean(truth[c].get("boundary_id"))),
        },
        "permits_2026_online_validation": {
            "row_count": len(permit_rows),
            "unique_hunt_code_count": len({clean(r.get("hunt_code")) for r in permit_rows}),
            "blank_hunt_code_count": permits_blank_code,
            "duplicate_hunt_code_count": permits_dupe_code,
            "boundary_id_populated_count": len(permit_rows) - permits_boundary_missing,
            "boundary_id_missing_count": permits_boundary_missing,
            "permit_status_counts": dict(permit_status_counts),
            "permit_math_conflicts": permit_math_conflicts,
        },
        "point_ladder_view_v2_validation": {
            "source_row_count": len(point_rows),
            "row_count": len(point_sync["rows"]),
            "dropped_rows_invalid_hunt_code": point_sync["dropped_invalid_code"],
            "dropped_rows_duplicate_key": point_sync["dropped_duplicates"],
            "all_rows_match_valid_database_hunt_code": point_sync["dropped_invalid_code"] == (len(point_rows) - len(point_sync["rows"]) - point_sync["dropped_duplicates"]),
            "boundary_id_missing_count": point_sync["boundary_missing"],
            "duplicate_hunt_code_residency_points_count": point_sync["dup_hunt_res_points"],
            "schema_changes_vs_current": point_sync["schema_changes"],
        },
        "hunt_master_enriched_v2_validation": {
            "source_row_count": len(enriched_rows),
            "row_count": len(enriched_sync["rows"]),
            "dropped_rows_invalid_hunt_code": enriched_sync["dropped_invalid_code"],
            "dropped_rows_duplicate_key": enriched_sync["dropped_duplicates"],
            "boundary_id_missing_count": enriched_sync["boundary_missing"],
            "duplicate_hunt_code_residency_points_count": enriched_sync["dup_hunt_res_points"],
            "schema_changes_vs_current": enriched_sync["schema_changes"],
            "permit_fields_synced_from_database": True,
        },
        "hunt_boundary_crosswalk_v2_validation": {
            "row_count": len(crosswalk_rows),
            "unique_hunt_code_count": len({clean(r.get("hunt_code")) for r in crosswalk_rows}),
            "duplicate_hunt_code_count": crosswalk_dupe_code,
            "boundary_id_missing_count": crosswalk_boundary_missing,
            "duplicate_boundary_id_count_allowed": crosswalk_dup_boundary,
        },
        "schema_changes_summary": {
            "point_ladder_view_v2": point_sync["schema_changes"],
            "hunt_master_enriched_v2": enriched_sync["schema_changes"],
        },
        "promotion_blockers": PROMOTION_BLOCKERS,
        "recommended_next_step": "Run contract checks against loaders using draft files, then perform controlled promotion from runtime_drafts to processed_data in a separate task.",
    }

    OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary_rows = [
        {
            "output_file": str(OUT_PERMITS.relative_to(REPO)).replace("\\", "/"),
            "row_count": len(permit_rows),
            "unique_hunt_code_count": len({clean(r.get("hunt_code")) for r in permit_rows}),
            "boundary_id_missing_count": permits_boundary_missing,
            "duplicate_key_count": permits_dupe_code,
            "notes": "one row per valid 2026 hunt_code",
        },
        {
            "output_file": str(OUT_POINT_LADDER.relative_to(REPO)).replace("\\", "/"),
            "row_count": len(point_sync["rows"]),
            "unique_hunt_code_count": len({clean(r.get("hunt_code")) for r in point_sync["rows"]}),
            "boundary_id_missing_count": point_sync["boundary_missing"],
            "duplicate_key_count": point_sync["dup_hunt_res_points"],
            "notes": "key=hunt_code+residency+points",
        },
        {
            "output_file": str(OUT_ENRICHED.relative_to(REPO)).replace("\\", "/"),
            "row_count": len(enriched_sync["rows"]),
            "unique_hunt_code_count": len({clean(r.get("hunt_code")) for r in enriched_sync["rows"]}),
            "boundary_id_missing_count": enriched_sync["boundary_missing"],
            "duplicate_key_count": enriched_sync["dup_hunt_res_points"],
            "notes": "key=hunt_code+residency+points (where points exists)",
        },
        {
            "output_file": str(OUT_CROSSWALK.relative_to(REPO)).replace("\\", "/"),
            "row_count": len(crosswalk_rows),
            "unique_hunt_code_count": len({clean(r.get("hunt_code")) for r in crosswalk_rows}),
            "boundary_id_missing_count": crosswalk_boundary_missing,
            "duplicate_key_count": crosswalk_dupe_code,
            "notes": "duplicate boundary_id allowed when shared by multiple hunts",
        },
    ]
    write_csv(
        OUT_SUMMARY,
        ["output_file", "row_count", "unique_hunt_code_count", "boundary_id_missing_count", "duplicate_key_count", "notes"],
        summary_rows,
    )

    print(
        json.dumps(
            {
                "valid_hunt_codes": len(valid_codes),
                "permits_row_count": len(permit_rows),
                "point_ladder_v2_row_count": len(point_sync["rows"]),
                "enriched_v2_row_count": len(enriched_sync["rows"]),
                "crosswalk_v2_row_count": len(crosswalk_rows),
                "permit_math_conflicts": permit_math_conflicts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
