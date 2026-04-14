import pytest


@pytest.mark.xfail(reason="StageManager contract not implemented yet")
def test_stage_manager_initializes_with_stage_1_as_current_stage():
    from app.backend.core.stage_manager import StageManager

    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    assert session.current_stage == "stage_1"
    assert session.approved_stages == []


@pytest.mark.xfail(reason="Stage approval flow not implemented yet")
def test_stage_manager_advances_only_after_approval():
    from app.backend.core.stage_manager import StageManager

    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(Exception):
        manager.advance_stage(session)

    manager.approve_stage(session, "stage_1")
    manager.advance_stage(session)

    assert session.current_stage == "stage_2"


@pytest.mark.xfail(reason="Rollback rules not implemented yet")
def test_stage_manager_allows_only_configured_rollback_targets():
    from app.backend.core.stage_manager import StageManager

    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")
    manager.approve_stage(session, "stage_1")
    manager.advance_stage(session)
    manager.approve_stage(session, "stage_2")
    manager.advance_stage(session)

    # now stage_3, rollback to stage_2 should be allowed
    manager.rollback_to(session, "stage_2")
    assert session.current_stage == "stage_2"


@pytest.mark.xfail(reason="Invalid rollback handling not implemented yet")
def test_stage_manager_rejects_invalid_rollback_target():
    from app.backend.core.stage_manager import StageManager

    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(Exception):
        manager.rollback_to(session, "stage_4")
