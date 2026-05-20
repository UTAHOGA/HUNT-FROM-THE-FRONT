from __future__ import annotations

import csv
import re
from pathlib import Path

from pypdf import PdfReader


REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "data_truth" / "draw_results_truth" / "normalized" / "draw_results_long.csv"

PDFS = [
    REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2022" / "pdf" / "draw_odds" / "21_bg-odds.pdf",
    REPO / "pipeline" / "RAW" / "hunt_unit_database" / "2025" / "pdf" / "draw_odds" / "24_bg-odds.pdf",
]

HUNT_RE = re.compile(r"Hunt:\s*([A-Z]{2}\d{4})\s+(.+?)\s+Page\s+\d+", re.IGNORECASE)
YEAR_RE = re.compile(r"(20\d{2})\s+Draw", re.IGNORECASE)

ROW_RE = re.compile(
    r"(\d{1,2})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(N\s*/\s*A|N/A|1\s*in\s*[\d\.,]+)\s+"
    r"(\d{1,2})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(N\s*/\s*A|N/A|1\s*in\s*[\d\.,]+)",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    s = text.replace("\u00a0", " ")
    s = s.replace("|", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("N / A", "N/A").replace("N /A", "N/A").replace("N/ A", "N/A")
    return s


def _to_int(token: str) -> int:
    return int(re.sub(r"[^\d]", "", token) or "0")


def _hunt_type_from_name(name: str) -> str:
    n = name.lower()
    if "premium le" in n or "premium limited" in n:
        return "Premium Limited-entry"
    if "once-in-a-lifetime" in n or "once in a lifetime" in n or "oial" in n:
        return "Once-in-a-lifetime"
    return "Limited Entry"


def extract_rows(pdf_path: Path) -> list[dict[str, str]]:
    if not pdf_path.exists():
        return []
    out: list[dict[str, str]] = []
    reader = PdfReader(str(pdf_path))
    for i, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = _clean(raw)
        if "Hunt:" not in text:
            continue
        hunt_match = HUNT_RE.search(text)
        if not hunt_match:
            continue
        year_match = YEAR_RE.search(text)
        if not year_match:
            continue
        year = year_match.group(1)
        hunt_code = hunt_match.group(1).upper().strip()
        hunt_name = hunt_match.group(2).strip()
        hunt_type = _hunt_type_from_name(hunt_name)
        for m in ROW_RE.finditer(text):
            p_res = _to_int(m.group(1))
            res_app = _to_int(m.group(2))
            res_bonus = _to_int(m.group(3))
            res_regular = _to_int(m.group(4))
            res_total = _to_int(m.group(5))
            res_ratio = m.group(6).replace(" ", "")

            p_non = _to_int(m.group(7))
            non_app = _to_int(m.group(8))
            non_bonus = _to_int(m.group(9))
            non_regular = _to_int(m.group(10))
            non_total = _to_int(m.group(11))
            non_ratio = m.group(12).replace(" ", "")

            out.append(
                {
                    "hunt_code": hunt_code,
                    "boundary_id": "",
                    "hunt_name": hunt_name,
                    "species": "",
                    "sex_type": "",
                    "hunt_type": hunt_type,
                    "weapon": "",
                    "hunt_class": hunt_type,
                    "season": "",
                    "year": year,
                    "draw_pool": "standard",
                    "residency": "Resident",
                    "points": str(p_res),
                    "eligible_applicants": str(res_app),
                    "bonus_permits": str(res_bonus),
                    "preference_permits": "",
                    "regular_permits": str(res_regular),
                    "total_permits": str(res_total),
                    "total_drawn": str(res_total),
                    "success_ratio": res_ratio,
                    "p_draw_percent": "",
                    "draw_type": "Draw 5",
                    "draw_method": "BONUS",
                    "status": "",
                    "source_file": pdf_path.name,
                    "source_pdf_page": str(i),
                    "page_number": str(i),
                    "raw_hunt_name": hunt_name,
                    "reference_match_status": "",
                    "metadata_status": "",
                    "missing_required_metadata": "",
                    "hunt_name_source": "pdf",
                    "boundary_id_source": "",
                    "species_source": "",
                    "sex_type_source": "",
                    "hunt_type_source": "pdf",
                    "weapon_source": "",
                    "hunt_class_source": "pdf",
                    "season_source": "",
                    "database_2026_match": "",
                    "hunt_master_enriched_match": "",
                    "required_metadata_complete": "",
                    "database_truth_match": "",
                }
            )
            out.append(
                {
                    "hunt_code": hunt_code,
                    "boundary_id": "",
                    "hunt_name": hunt_name,
                    "species": "",
                    "sex_type": "",
                    "hunt_type": hunt_type,
                    "weapon": "",
                    "hunt_class": hunt_type,
                    "season": "",
                    "year": year,
                    "draw_pool": "standard",
                    "residency": "Nonresident",
                    "points": str(p_non),
                    "eligible_applicants": str(non_app),
                    "bonus_permits": str(non_bonus),
                    "preference_permits": "",
                    "regular_permits": str(non_regular),
                    "total_permits": str(non_total),
                    "total_drawn": str(non_total),
                    "success_ratio": non_ratio,
                    "p_draw_percent": "",
                    "draw_type": "Draw 5",
                    "draw_method": "BONUS",
                    "status": "",
                    "source_file": pdf_path.name,
                    "source_pdf_page": str(i),
                    "page_number": str(i),
                    "raw_hunt_name": hunt_name,
                    "reference_match_status": "",
                    "metadata_status": "",
                    "missing_required_metadata": "",
                    "hunt_name_source": "pdf",
                    "boundary_id_source": "",
                    "species_source": "",
                    "sex_type_source": "",
                    "hunt_type_source": "pdf",
                    "weapon_source": "",
                    "hunt_class_source": "pdf",
                    "season_source": "",
                    "database_2026_match": "",
                    "hunt_master_enriched_match": "",
                    "required_metadata_complete": "",
                    "database_truth_match": "",
                }
            )
    return out


def main() -> None:
    with TARGET.open("r", encoding="utf-8-sig", newline="") as f:
        existing = list(csv.DictReader(f))
        fieldnames = list(existing[0].keys())
    by_key = {
        (
            (r.get("hunt_code") or "").upper().strip(),
            (r.get("year") or "").strip(),
            (r.get("draw_pool") or "standard").strip().lower(),
            (r.get("residency") or "").strip(),
            str(r.get("points") or "").strip(),
        ): r
        for r in existing
    }
    added = 0
    for pdf in PDFS:
        for row in extract_rows(pdf):
            k = (
                row["hunt_code"].upper().strip(),
                row["year"].strip(),
                row["draw_pool"].strip().lower(),
                row["residency"].strip(),
                str(row["points"]).strip(),
            )
            if k in by_key:
                continue
            by_key[k] = row
            added += 1
    rows = list(by_key.values())
    rows.sort(key=lambda r: ((r.get("hunt_code") or ""), (r.get("year") or ""), (r.get("draw_pool") or ""), (r.get("residency") or ""), int((r.get("points") or "0"))))
    with TARGET.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"added_rows={added}")
    print(f"total_rows={len(rows)}")


if __name__ == "__main__":
    main()
