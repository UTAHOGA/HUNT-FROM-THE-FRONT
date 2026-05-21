from pathlib import Path


def test_docs_current_state_reflects_completed_and_pending_phases() -> None:
    text = Path(r"C:\Users\tyler\Desktop\GitHub\HUNTS\docs\utah_draw_system_scope.md").read_text(encoding="utf-8")

    for phrase in (
        "Phase 1: OIL / LE / PLE bonus engine",
        "Phase 2: target-scope classifier and guardrails",
        "Phase 3: general-season buck deer preference engine",
        "Phase 4: antlerless deer / antlerless elk / doe pronghorn preference engine",
        "Phase 5: Dedicated Hunter deer preference engine",
        "Phase 6: CWMU public + antlerless moose + ewe bighorn bonus families",
        "Phase 7: limited-entry turkey bonus strategy",
        "Phase 8: public bear bonus strategy + Sportsman permit classifier",
        "Phase 9: private-lands-only antlerless elk allocation / availability strategy",
        "Phase 10: mountain lion / cougar rule-status + availability strategy",
        "Phase 11: Sportsman permit odds strategy",
        "Phase 12: bear subtype-aware quota draw + availability strategy",
        "Phase 13: mountain lion / cougar rule-status + availability closeout",
        "Phase 14: private-lands-only antlerless elk allocation / availability closeout",
    ):
        assert phrase in text

    stale_pending_lines = (
        "- `SPORTSMAN_PERMIT`",
        "- `BONUS_CWMU_BIG_GAME`",
        "- `BONUS_ANTLERLESS_MOOSE`",
        "- `BONUS_EWE_BIGHORN`",
        "- `BONUS_TURKEY`",
        "- `BEAR_DRAW`",
        "- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`",
        "- `MOUNTAIN_LION_DRAW`",
        "- `PREFERENCE_GENERAL_SEASON_BUCK_DEER`",
        "- `PREFERENCE_DEDICATED_HUNTER_DEER`",
        "- `PREFERENCE_ANTLERLESS_DEER`",
        "- `PREFERENCE_ANTLERLESS_ELK`",
        "- `PREFERENCE_DOE_PRONGHORN`",
    )
    pending_section = text.split("Still pending:", 1)[1].split("Private-lands-only antlerless elk note:", 1)[0]
    for stale_line in stale_pending_lines:
        assert stale_line not in pending_section

    assert "Currently modeled as `MODELED_ALLOCATION`:" in text
    assert "- `PRIVATE_LANDS_ONLY_ANTLERLESS_ELK`" in text.split("Currently modeled as `MODELED_ALLOCATION`:", 1)[1]
    assert "Currently modeled as `MODELED_AVAILABILITY`:" in text
    assert "- `MOUNTAIN_LION_DRAW`" in text.split("Currently modeled as `MODELED_AVAILABILITY`:", 1)[1]
    assert "Currently modeled as `MODELED_SPORTSMAN_DRAW`:" in text
    assert "- `SPORTSMAN_PERMIT`" in text.split("Currently modeled as `MODELED_SPORTSMAN_DRAW`:", 1)[1]
