from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from engine.utah import truth_source_promotion


REPO = Path(__file__).resolve().parents[2]
PROCESSED = REPO / "processed_data"
TRUTH_ROOT = REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2026" / "csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path, hunt_code: str) -> list[dict[str, str]]:
    return [row for row in _read_csv(path) if str(row.get("hunt_code") or "").upper() == hunt_code.upper()]


def _row(path: Path, hunt_code: str, residency: str, *, points: str | None = None, year: str | None = None) -> dict[str, str]:
    for row in _rows(path, hunt_code):
        if str(row.get("residency") or "") != residency:
            continue
        if points is not None and str(row.get("points") or "") != points:
            continue
        if year is not None and str(row.get("year") or "") != year:
            continue
        return row
    raise AssertionError(f"Missing row for {hunt_code} {residency} points={points!r} year={year!r} in {path.name}")


def test_doe_pronghorn_truth_source_promoted_to_runtime_reference() -> None:
    path = PROCESSED / "hunt_unit_reference_linked.csv"
    expected = {
        ("PD1000", "Resident"): ("36", "36", "4", "40"),
        ("PD1012", "Resident"): ("18", "18", "2", "20"),
        ("PD1017", "Resident"): ("31", "31", "4", "35"),
        ("PD1039", "Resident"): ("36", "36", "4", "40"),
        ("PD1044", "Resident"): ("4", "4", "1", "5"),
        ("PD1057", "Resident"): ("27", "27", "3", "30"),
        ("PD1059", "Resident"): ("31", "31", "4", "35"),
    }
    for (hunt_code, residency), values in expected.items():
        row = _row(path, hunt_code, residency)
        assert row["public_permits_2026"] == values[0]
        assert row["permits_2026_res"] == values[1]
        assert row["permits_2026_nr"] == values[2]
        assert row["permits_2026_total"] == values[3]


def test_doe_pronghorn_pd1039_added_to_runtime_reference() -> None:
    path = PROCESSED / "hunt_unit_reference_linked.csv"
    rows = _rows(path, "PD1039")
    assert len(rows) == 2
    assert {row["residency"] for row in rows} == {"Resident", "Nonresident"}
    assert all(row["truth_source_status"] == "MATCHED" for row in rows)


def test_antlerless_deer_truth_source_promoted_to_runtime_reference() -> None:
    path = PROCESSED / "hunt_unit_reference_linked.csv"
    expected = {
        "DA1009": "20",
        "DA1018": "15",
        "DA1033": "10",
        "DA1051": "10",
    }
    for hunt_code, total in expected.items():
        resident = _row(path, hunt_code, "Resident")
        nonresident = _row(path, hunt_code, "Nonresident")
        assert resident["public_permits_2026"] == total
        assert nonresident["public_permits_2026"] == total
        assert resident["permits_2026_total"] == total
        assert nonresident["permits_2026_total"] == total


def test_antlerless_deer_da1051_added_to_runtime_reference() -> None:
    path = PROCESSED / "hunt_unit_reference_linked.csv"
    rows = _rows(path, "DA1051")
    assert len(rows) == 2
    assert all(row["reason_codes"] == "TRUTH_SOURCE_ADDED_MISSING_RUNTIME_ROW" for row in rows)


def test_standard_antlerless_elk_truth_source_promoted_to_runtime_reference() -> None:
    path = PROCESSED / "hunt_unit_reference_linked.csv"
    resident = _row(path, "EA1267", "Resident")
    assert resident["public_permits_2026"] == "180"
    assert resident["permits_2026_res"] == "180"
    assert resident["permits_2026_nr"] == "20"
    assert resident["permits_2026_total"] == "200"

    ogden = _row(path, "EA1269", "Resident")
    assert ogden["permits_2026_total"] == "300"
    assert ogden["permits_2026_res"] == "270"
    assert ogden["permits_2026_nr"] == "30"

    kamas_archery = _row(path, "EA2033", "Resident")
    assert kamas_archery["permits_2026_total"] == "200"
    assert kamas_archery["public_permits_2026"] == "180"

    nebo = _row(path, "EA1021", "Resident")
    assert nebo["permits_2026_total"] == "280"

    nebo_late = _row(path, "EA1208", "Resident")
    assert nebo_late["permits_2026_total"] == "325"

    for hunt_code in [
        "EA1007",
        "EA1287",
        "EA1288",
        "EA1289",
        "EA1290",
        "EA1291",
        "EA1292",
        "EA1293",
        "EA1294",
        "EA1295",
        "EA1296",
        "EA1297",
        "EA1298",
        "EA1299",
        "EA1300",
    ]:
        assert len(_rows(path, hunt_code)) == 2


def test_private_lands_antlerless_elk_not_duplicated_by_residency() -> None:
    audit = _read_json(PROCESSED / "private_lands_antlerless_elk_truth_source_audit.json")
    assert audit["structural_duplicated_by_residency_errors"] == 0
    for path in [
        PROCESSED / "hunt_unit_reference_linked.csv",
        PROCESSED / "hunt_master_enriched.csv",
        PROCESSED / "point_ladder_view.csv",
        PROCESSED / "draw_reality_engine.csv",
    ]:
        rows = _rows(path, "EA2012")
        assert rows
        assert all((row.get("public_permits_2026") or "") == "" for row in rows)


def test_private_lands_antlerless_elk_marked_availability_only() -> None:
    for path in [
        PROCESSED / "hunt_unit_reference_linked.csv",
        PROCESSED / "hunt_master_enriched.csv",
        PROCESSED / "point_ladder_view.csv",
        PROCESSED / "draw_reality_engine.csv",
    ]:
        rows = _rows(path, "EA2012")
        assert rows
        for row in rows:
            assert row["draw_model_class"] == "AVAILABILITY_ONLY"
            assert row["probability_model"] == "NONE"
            assert row["hunt_category"] == "PRIVATE_LANDS_ONLY_ANTLERLESS_ELK"
            assert "AVAILABILITY_ONLY_NO_DRAW_PROBABILITY" in row["reason_codes"]

    reference = PROCESSED / "hunt_unit_reference_linked.csv"
    expected_totals = {
        "EA2012": "500",
        "EA2015": "75",
        "EA2016": "325",
        "EA2027": "250",
        "EA2046": "50",
    }
    for hunt_code, total in expected_totals.items():
        assert _row(reference, hunt_code, "Resident")["permits_2026_total"] == total


def test_antlerless_elk_control_units_overlay_preserved() -> None:
    audit = _read_json(PROCESSED / "antlerless_elk_control_unit_audit.json")
    assert audit["control_unit_count"] == 9
    assert audit["matched_control_unit_count"] == 8
    assert audit["unmatched_control_units"] == ["Henry Mtns"]


def test_antlerless_elk_control_unit_henry_mtns_unmatched_but_not_fabricated() -> None:
    audit = _read_json(PROCESSED / "antlerless_elk_control_unit_audit.json")
    henry = next(item for item in audit["control_unit_matches"] if item["control_unit"] == "Henry Mtns")
    assert henry["matched_any_truth_rows"] is False
    for path in [
        PROCESSED / "hunt_unit_reference_linked.csv",
        PROCESSED / "hunt_master_enriched.csv",
        PROCESSED / "point_ladder_view.csv",
        PROCESSED / "draw_reality_engine.csv",
    ]:
        assert _rows(path, "EA1032") == []


def test_box_elder_grouse_creek_control_unit_maps_to_ea1287() -> None:
    audit = _read_json(PROCESSED / "antlerless_elk_control_unit_audit.json")
    match = next(item for item in audit["control_unit_matches"] if item["control_unit"] == "Box Elder, Grouse Creek")
    assert match["new_this_year"] == "YES"
    assert match["matched_hunt_codes"] == ["EA1287"]

    row = _row(PROCESSED / "hunt_unit_reference_linked.csv", "EA1287", "Resident")
    assert row["new_this_year"] == "YES"


def test_antlerless_moose_truth_source_locked_zero_mismatches() -> None:
    audit = _read_json(PROCESSED / "antlerless_moose_truth_source_audit.json")
    assert audit["repo_mismatch_row_count"] == 0
    assert audit["all_2026_repo_matches_truth"] is True


def test_ewe_rocky_sheep_truth_source_locked_zero_mismatches() -> None:
    audit = _read_json(PROCESSED / "ewe_rocky_sheep_truth_source_audit.json")
    assert audit["repo_mismatch_row_count"] == 0
    assert audit["all_2026_repo_matches_truth"] is True


def test_locked_clean_families_left_unchanged() -> None:
    hamss = _read_json(PROCESSED / "le_bull_elk_hamss_september_archery_truth_source_audit.json")
    pronghorn = _read_json(PROCESSED / "le_buck_pronghorn_truth_source_audit.json")
    moose = _read_json(PROCESSED / "antlerless_moose_truth_source_audit.json")
    ewe = _read_json(PROCESSED / "ewe_rocky_sheep_truth_source_audit.json")

    assert hamss["all_2026_repo_matches_truth"] is True
    assert pronghorn["repo_mismatch_row_count"] == 0
    assert moose["repo_mismatch_row_count"] == 0
    assert ewe["repo_mismatch_row_count"] == 0


def test_truth_source_audits_zero_mismatches_after_promotion() -> None:
    summary = _read_json(PROCESSED / "truth_source_promotion_summary.json")
    for family in [
        "doe_pronghorn",
        "antlerless_deer",
        "standard_antlerless_elk",
        "private_lands_antlerless_elk",
        "antlerless_moose",
        "ewe_rocky_sheep",
    ]:
        assert summary["families"][family]["mismatch_rows_after_promotion"] == 0


def test_truth_source_rows_preserve_source_metadata() -> None:
    for path, hunt_code, residency in [
        (PROCESSED / "hunt_unit_reference_linked.csv", "PD1039", "Resident"),
        (PROCESSED / "hunt_unit_reference_linked.csv", "DA1051", "Resident"),
        (PROCESSED / "hunt_unit_reference_linked.csv", "EA2012", "Resident"),
    ]:
        row = _row(path, hunt_code, residency)
        assert row["permit_source"] == "2026_RAC_TRUTH_SOURCE"
        assert row["quota_source"] == "2026_RAC_TRUTH_SOURCE"
        assert row["truth_source_status"] == "MATCHED"
        assert row["data_quality_grade"] == "A"
        assert row["truth_source_file"].endswith(".csv")


def test_truth_source_promotion_does_not_change_probability_math(tmp_path: Path) -> None:
    processed_copy = tmp_path / "processed"
    processed_copy.mkdir()
    for name in [
        "hunt_unit_reference_linked.csv",
        "hunt_master_enriched.csv",
        "point_ladder_view.csv",
        "draw_reality_engine.csv",
    ]:
        shutil.copyfile(PROCESSED / name, processed_copy / name)

    before = _row(processed_copy / "draw_reality_engine.csv", "PD1000", "Nonresident", points="0", year="2022").copy()
    exit_code = truth_source_promotion.main(
        [
            "--truth-root",
            str(TRUTH_ROOT),
            "--processed-root",
            str(processed_copy),
            "--families",
            "doe_pronghorn",
            "antlerless_deer",
            "standard_antlerless_elk",
            "private_lands_antlerless_elk",
            "antlerless_elk_control_units",
            "antlerless_moose",
            "ewe_rocky_sheep",
            "--promote",
            "--write-audits",
        ]
    )
    assert exit_code == 0
    after = _row(processed_copy / "draw_reality_engine.csv", "PD1000", "Nonresident", points="0", year="2022")
    assert after["eligible_applicants"] == before["eligible_applicants"]
    assert after["total_drawn"] == before["total_drawn"]
    assert after["p_draw_percent"] == before["p_draw_percent"]


def test_truth_source_dash_values_normalized_to_zero_for_delta_only() -> None:
    audit = _read_json(PROCESSED / "antlerless_deer_truth_source_audit.json")
    beaver_city = next(item for item in audit["group_changes"] if item["permit_group"] == "Beaver City")
    assert beaver_city["permits_2025_total"] == 0
    row = _row(PROCESSED / "hunt_unit_reference_linked.csv", "DA1051", "Resident")
    assert row["permits_2025_total"] == ""


def test_truth_source_promotion_preserves_existing_columns() -> None:
    for name in [
        "hunt_unit_reference_linked.csv",
        "hunt_master_enriched.csv",
        "point_ladder_view.csv",
        "draw_reality_engine.csv",
    ]:
        with (PROCESSED / name).open(encoding="utf-8-sig", newline="") as handle:
            headers = list(csv.DictReader(handle).fieldnames or [])
        assert "hunt_code" in headers
        assert "residency" in headers
        assert "public_permits_2026" in headers
        assert "draw_pool" in headers
        assert "permit_source" in headers
        assert "truth_source_status" in headers
        assert "reason_codes" in headers


def test_truth_source_promotion_cli_writes_summary_report(tmp_path: Path) -> None:
    processed_copy = tmp_path / "processed"
    processed_copy.mkdir()
    for name in [
        "hunt_unit_reference_linked.csv",
        "hunt_master_enriched.csv",
        "point_ladder_view.csv",
        "draw_reality_engine.csv",
    ]:
        shutil.copyfile(PROCESSED / name, processed_copy / name)

    exit_code = truth_source_promotion.main(
        [
            "--truth-root",
            str(TRUTH_ROOT),
            "--processed-root",
            str(processed_copy),
            "--families",
            "antlerless_moose",
            "ewe_rocky_sheep",
            "--promote",
            "--write-audits",
        ]
    )
    assert exit_code == 0
    assert (processed_copy / "truth_source_promotion_summary.json").exists()


def test_truth_source_promotion_cli_exits_nonzero_on_remaining_required_mismatches(monkeypatch) -> None:
    def fake_run_promotion(*args, **kwargs):
        return 1, {"families": {}}

    monkeypatch.setattr(truth_source_promotion, "run_promotion", fake_run_promotion)
    exit_code = truth_source_promotion.main(
        [
            "--truth-root",
            str(TRUTH_ROOT),
            "--processed-root",
            str(PROCESSED),
            "--families",
            "antlerless_moose",
            "--promote",
            "--write-audits",
        ]
    )
    assert exit_code == 1
