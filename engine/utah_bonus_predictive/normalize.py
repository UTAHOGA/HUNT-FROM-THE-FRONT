"""Normalization helpers for draw rows."""

from __future__ import annotations


def normalize_residency(value: str) -> str:
    text = (value or "").strip().lower()
    if text in {"resident", "res"}:
        return "Resident"
    if text in {"nonresident", "non-resident", "nr"}:
        return "Nonresident"
    return value


def normalize_draw_pool(value: str) -> str:
    return (value or "standard").strip().lower() or "standard"

