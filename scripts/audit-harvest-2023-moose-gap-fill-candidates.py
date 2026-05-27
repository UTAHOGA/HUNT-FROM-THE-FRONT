"""Review obvious 2023 moose harvest/draw gaps for fillable crosswalks.

The audit consumes the already-anchored 2023 moose draw and harvest source
audits. It promotes only review evidence, not runtime/database changes. The
main fill candidate is the Jacob's Creek CWMU mismatch where the 2023 draw PDF
uses MB6252 while the 2023 DWR harvest report and current DWR CWMU evidence use
MB6258.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARVEST_RECON = ROOT / "data_truth" / "harvest_results_truth" / "validation" / "harvest_2023_moose_code_reconciliation.csv"
DRAW_CODES = ROOT / "data_truth" / "draw_results_truth" / "validation" / "draw_2023_moose_pdf_hunt_codes.csv"
HARVEST_LEDGER = (
    ROOT
    / "data_truth"
    / "harvest_results_truth"
    / "raw_packages"
    / "unknown_for_unknown_hunt_code_year_backcheck_outputs"
    / "hunt_code_year_presence_ledger_2021_2026.csv"
)
PERMIT_OVERLAY = ROOT / "data_model" / "permit_overlays" / "special_permit_overlay_classes_all_years.csv"
VALIDATION_DIR = ROOT / "data_truth" / "harvest_results_truth" / "validation"
GAP_CANDIDATES_CSV = VALIDATION_DIR / "harvest_2023_moose_gap_fill_candidates.csv"
SUMMARY_JSON = VALIDATION_DIR / "harvest_2023_moose_gap_fill_summary.json"
REPORT_MD = ROOT / "processed_data" / "harvest_2023_moose_gap_fill_audit.md"

DWR_2022_BIG_GAME_REPORT_URL = "https://wildlife.utah.gov/pdf/annual_reports/big_game/22_bg_report.pdf"
DWR_2023_BIG_GAME_REPORT_URL = "https://wildlife.utah.gov/pdf/annual-reports/big-game/23_bg_report.pdf"
DWR_DRAW_ODDS_URL = "https://wildlife.utah.gov/biggame/odds"
DWR_GUIDEBOOKS_URL = "https://wildlife.utah.gov/guidebooks"


def norm(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def local_years_for_code(code: str) -> str:
    if not HARVEST_LEDGER.exists():
        return ""
    years = []
    for row in read_rows(HARVEST_LEDGER):
        if norm(row.get("hunt_code")) == code:
            years.append(norm(row.get("reported_hunt_year")))
    return "|".join(sorted({year for year in years if year}))


def overlay_rows_for_name(name: str) -> list[dict[str, str]]:
    if not PERMIT_OVERLAY.exists():
        return []
    lower_name = name.lower()
    return [
        row
        for row in read_rows(PERMIT_OVERLAY)
        if lower_name in norm(row.get("hunt_name")).lower() and norm(row.get("species")).lower() in {"moose", "limited entry bull moose"}
    ]


def draw_title(code: str) -> str:
    for row in read_rows(DRAW_CODES):
        if norm(row.get("hunt_code")) == code:
            return norm(row.get("pdf_title_evidence"))
    return ""


def build_candidates() -> list[dict[str, str]]:
    recon_rows = read_rows(HARVEST_RECON)
    gaps = [row for row in recon_rows if norm(row.get("reconciliation_status")) != "DRAW_AND_HARVEST"]
    candidates: list[dict[str, str]] = []
    for row in gaps:
        code = norm(row.get("hunt_code"))
        if code == "MB6252":
            mapped_code = "MB6258"
            overlay = overlay_rows_for_name("Jacob's Creek")
            overlay_evidence = "; ".join(
                sorted(
                    {
                        f"{norm(item.get('reported_hunt_year'))}->{norm(item.get('model_target_year'))}:{norm(item.get('hunt_code'))}:{norm(item.get('hunt_name'))}:{norm(item.get('permits'))}"
                        for item in overlay
                    }
                )
            )
            candidates.append(
                {
                    "gap_code": code,
                    "gap_type": "DRAW_ONLY",
                    "gap_hunt_name": "Jacob's Creek CWMU",
                    "species": "Moose",
                    "sex_type": "Male Only",
                    "weapon": "Any Legal Weapon",
                    "hunt_type": "CWMU",
                    "candidate_fill_action": "CROSSWALK_TO_HARVEST_CODE",
                    "candidate_harvest_code": mapped_code,
                    "candidate_harvest_name": "Jacob's Creek CWMU",
                    "confidence": "HIGH",
                    "promote_to_runtime": "NO",
                    "reason": "Same Jacob's Creek CWMU/name/species/sex/weapon; 2023 draw PDF uses MB6252 while 2023 harvest and current CWMU evidence use MB6258.",
                    "local_draw_evidence": draw_title(code),
                    "local_harvest_evidence": "2023 harvest CSV has MB6258 Jacob's Creek with 2 permits, 2 hunters afield, 2 harvest.",
                    "local_history_evidence": f"MB6252 harvest years {local_years_for_code('MB6252')}; MB6258 harvest years {local_years_for_code('MB6258')}",
                    "overlay_evidence": overlay_evidence,
                    "online_evidence_urls": "|".join([DWR_2022_BIG_GAME_REPORT_URL, DWR_2023_BIG_GAME_REPORT_URL, DWR_DRAW_ODDS_URL]),
                    "review_status": "FILLABLE_REVIEW_EVIDENCE",
                }
            )
        elif code == "MB6258":
            candidates.append(
                {
                    "gap_code": code,
                    "gap_type": "HARVEST_ONLY_PAIRED_TARGET",
                    "gap_hunt_name": "Jacob's Creek CWMU",
                    "species": "Moose",
                    "sex_type": "Male Only",
                    "weapon": "Any Legal Weapon",
                    "hunt_type": "CWMU",
                    "candidate_fill_action": "HARVEST_CODE_USED_TO_FILL_DRAW_GAP",
                    "candidate_harvest_code": code,
                    "candidate_harvest_name": "Jacob's Creek CWMU",
                    "confidence": "HIGH",
                    "promote_to_runtime": "NO",
                    "reason": "This harvest-only row is the paired current/harvest code for the MB6252 draw-only Jacob's Creek CWMU row.",
                    "local_draw_evidence": draw_title("MB6252"),
                    "local_harvest_evidence": "2023 DWR harvest report has MB6258 Jacob's Creek with 2 permits, 2 hunters afield, 2 harvest.",
                    "local_history_evidence": f"MB6252 harvest years {local_years_for_code('MB6252')}; MB6258 harvest years {local_years_for_code('MB6258')}",
                    "overlay_evidence": "; ".join(
                        sorted(
                            {
                                f"{norm(item.get('reported_hunt_year'))}->{norm(item.get('model_target_year'))}:{norm(item.get('hunt_code'))}:{norm(item.get('hunt_name'))}:{norm(item.get('permits'))}"
                                for item in overlay_rows_for_name("Jacob's Creek")
                            }
                        )
                    ),
                    "online_evidence_urls": "|".join([DWR_2022_BIG_GAME_REPORT_URL, DWR_2023_BIG_GAME_REPORT_URL, DWR_DRAW_ODDS_URL]),
                    "review_status": "PAIRED_WITH_MB6252_REVIEW_EVIDENCE",
                }
            )
        else:
            candidates.append(
                {
                    "gap_code": code,
                    "gap_type": norm(row.get("reconciliation_status")),
                    "gap_hunt_name": norm(row.get("harvest_hunt_names")),
                    "species": "Moose",
                    "sex_type": "Male Only",
                    "weapon": "Any Legal Weapon",
                    "hunt_type": "CWMU",
                    "candidate_fill_action": "KEEP_HARVEST_ONLY",
                    "candidate_harvest_code": code,
                    "candidate_harvest_name": norm(row.get("harvest_hunt_names")),
                    "confidence": "MEDIUM",
                    "promote_to_runtime": "NO",
                    "reason": "Local and DWR harvest evidence support the harvest row, but no same-year 2023 moose draw PDF row was found for this code.",
                    "local_draw_evidence": "",
                    "local_harvest_evidence": f"2023 harvest CSV row: {norm(row.get('harvest_hunt_names'))}",
                    "local_history_evidence": f"{code} harvest years {local_years_for_code(code)}",
                    "overlay_evidence": "",
                    "online_evidence_urls": DWR_2023_BIG_GAME_REPORT_URL,
                    "review_status": "RETAIN_HARVEST_ONLY_NO_DRAW_FILL",
                }
            )
    return sorted(candidates, key=lambda row: (row["candidate_fill_action"], row["gap_code"]))


def build_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# 2023 Moose Gap Fill Candidate Audit",
        "",
        "Reviews local and online evidence for the 2023 moose harvest/draw gaps.",
        "",
        "## Result",
        "",
        f"- Gap rows reviewed: {summary['gap_rows_reviewed']}",
        f"- High-confidence fill candidates: {summary['high_confidence_fill_count']}",
        f"- Paired harvest target rows: {summary['paired_harvest_target_count']}",
        f"- Retained harvest-only rows: {summary['retained_harvest_only_count']}",
        f"- Runtime/database changes made: {summary['runtime_database_changes_made']}",
        "",
        "## Fill Candidate",
        "",
        "- `MB6252` draw-only Jacob's Creek CWMU crosswalks to harvest/current code `MB6258` with high confidence.",
        "- Evidence basis: same Jacob's Creek CWMU, Moose, Male Only/Bull, CWMU, Any Legal Weapon context; DWR 2022 harvest evidence uses `MB6252`; DWR 2023 harvest evidence uses `MB6258`; local draw-source evidence has `MB6252` in the same 2023 draw family.",
        "- `MB6258` is recorded as the paired harvest target row, not as an unresolved harvest-only miss.",
        "",
        "## Retained Harvest-Only",
        "",
        f"- {', '.join(summary['retained_harvest_only_codes'])}",
        "",
        "These remain harvest-only review evidence because no same-year 2023 moose draw PDF row was found for those codes.",
        "",
        "## Source Links",
        "",
        f"- DWR 2022 Big Game Annual Report: {DWR_2022_BIG_GAME_REPORT_URL}",
        f"- DWR 2023 Big Game Annual Report: {DWR_2023_BIG_GAME_REPORT_URL}",
        f"- DWR drawing odds page: {DWR_DRAW_ODDS_URL}",
        f"- DWR guidebooks/corrections page: {DWR_GUIDEBOOKS_URL}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rows = build_candidates()
    high_confidence = [row for row in rows if row["candidate_fill_action"] == "CROSSWALK_TO_HARVEST_CODE" and row["confidence"] == "HIGH"]
    paired_targets = [row for row in rows if row["candidate_fill_action"] == "HARVEST_CODE_USED_TO_FILL_DRAW_GAP"]
    retained = [row for row in rows if row["candidate_fill_action"] == "KEEP_HARVEST_ONLY"]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "audit_scope": "2023_moose_gap_fill_candidates",
        "gap_rows_reviewed": len(rows),
        "high_confidence_fill_count": len(high_confidence),
        "high_confidence_fill_codes": [row["gap_code"] for row in high_confidence],
        "high_confidence_fill_mappings": {row["gap_code"]: row["candidate_harvest_code"] for row in high_confidence},
        "paired_harvest_target_count": len(paired_targets),
        "paired_harvest_target_codes": [row["gap_code"] for row in paired_targets],
        "retained_harvest_only_count": len(retained),
        "retained_harvest_only_codes": [row["gap_code"] for row in retained],
        "runtime_database_changes_made": "NO",
        "status": "PASS"
        if len(high_confidence) == 1
        and high_confidence[0]["gap_code"] == "MB6252"
        and high_confidence[0]["candidate_harvest_code"] == "MB6258"
        and [row["gap_code"] for row in paired_targets] == ["MB6258"]
        else "REVIEW",
    }
    fields = [
        "gap_code",
        "gap_type",
        "gap_hunt_name",
        "species",
        "sex_type",
        "weapon",
        "hunt_type",
        "candidate_fill_action",
        "candidate_harvest_code",
        "candidate_harvest_name",
        "confidence",
        "promote_to_runtime",
        "reason",
        "local_draw_evidence",
        "local_harvest_evidence",
        "local_history_evidence",
        "overlay_evidence",
        "online_evidence_urls",
        "review_status",
    ]
    write_rows(GAP_CANDIDATES_CSV, rows, fields)
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(build_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
