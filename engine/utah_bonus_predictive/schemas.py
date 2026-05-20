"""Typed shapes for Utah bonus predictive engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrawResultRow:
    year: int
    draw_id: str
    species: str
    hunt_code: str
    hunt_name: str
    hunt_type: str
    residency: str
    bonus_points: int
    total_eligible_applicants: int
    bonus_permits: int
    regular_permits: int
    total_permits: int
    success_ratio_text: str
    source_pdf: str
    source_page: str

