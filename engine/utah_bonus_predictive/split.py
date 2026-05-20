"""Permit split logic for Utah bonus-style draws."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UtahBonusPermitSplit:
    publicPermits: int
    maxPointPermits: int
    randomPermits: int
    randomOnly: bool


def split_utah_bonus_permits(public_permits_raw: int) -> UtahBonusPermitSplit:
    public_permits = max(0, int(public_permits_raw or 0))
    if public_permits == 0:
        return UtahBonusPermitSplit(public_permits, 0, 0, False)
    if public_permits == 1:
        return UtahBonusPermitSplit(public_permits, 0, 1, True)
    max_point = (public_permits + 1) // 2
    random = public_permits - max_point
    return UtahBonusPermitSplit(public_permits, max_point, random, False)

