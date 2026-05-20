"""Ingest Utah draw results from CSV extracts."""

from __future__ import annotations

import csv
from pathlib import Path

from .schemas import DrawResultRow


def load_draw_results_csv(path: str | Path) -> list[DrawResultRow]:
    rows: list[DrawResultRow] = []
    with Path(path).open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                DrawResultRow(
                    year=int(row.get("year") or 0),
                    draw_id=str(row.get("draw_id") or ""),
                    species=str(row.get("species") or ""),
                    hunt_code=str(row.get("hunt_code") or "").upper(),
                    hunt_name=str(row.get("hunt_name") or ""),
                    hunt_type=str(row.get("hunt_type") or ""),
                    residency=str(row.get("residency") or ""),
                    bonus_points=int(row.get("bonus_points") or 0),
                    total_eligible_applicants=int(row.get("total_eligible_applicants") or 0),
                    bonus_permits=int(row.get("bonus_permits") or 0),
                    regular_permits=int(row.get("regular_permits") or 0),
                    total_permits=int(row.get("total_permits") or 0),
                    success_ratio_text=str(row.get("success_ratio_text") or ""),
                    source_pdf=str(row.get("source_pdf") or ""),
                    source_page=str(row.get("source_page") or ""),
                )
            )
    return rows

