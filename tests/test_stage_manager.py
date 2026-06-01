import pytest

from app.backend.core.session_store import SQLiteSessionStore
from app.backend.core.stage_manager import StageManager, StageTransitionError
from app.backend.schemas.stage import StageOutputBundle, StageResponse


def make_response(session, stage_id=None, summary="stage done"):
    selected_stage = stage_id or session.current_stage
    return StageResponse(
        session_id=session.session_id,
        stage_id=selected_stage,
        status="completed",
        output=StageOutputBundle(summary=summary),
    )


def run_current_stage(manager, session, summary="stage done"):
    return manager.store_stage_response(session, make_response(session, summary=summary))


def approve_and_advance(manager, session):
    session = run_current_stage(manager, session)
    session = manager.approve_stage(session, session.current_stage)
    return manager.advance_stage(session)


def test_stage_manager_initializes_with_stage_1_as_current_stage():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    assert session.current_stage == "stage_1"
    assert session.approved_stages == []


def test_stage_manager_advances_only_after_approval():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(StageTransitionError):
        manager.advance_stage(session)

    session = run_current_stage(manager, session)
    manager.approve_stage(session, "stage_1")
    session = manager.advance_stage(session)

    assert session.current_stage == "stage_2"


def test_stage_manager_allows_only_configured_rollback_targets():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")
    session = approve_and_advance(manager, session)
    session = approve_and_advance(manager, session)

    # now stage_3, rollback to stage_2 should be allowed
    session = manager.rollback_to(session, "stage_2")
    assert session.current_stage == "stage_2"


def test_stage_manager_rejects_invalid_rollback_target():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(StageTransitionError):
        manager.rollback_to(session, "stage_4")


def test_stage_manager_keeps_multiple_sessions_isolated():
    manager = StageManager()
    first = manager.create_session(scenario="dispatch_recommendation")
    second = manager.create_session(scenario="dispatch_recommendation")

    first = run_current_stage(manager, first)
    manager.approve_stage(first, "stage_1")
    first = manager.advance_stage(first)

    assert first.current_stage == "stage_2"
    assert first.approved_stages == ["stage_1"]
    assert second.current_stage == "stage_1"
    assert second.approved_stages == []


def test_stage_manager_rejects_approval_for_non_current_stage():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(StageTransitionError):
        manager.approve_stage(session, "stage_2")

    assert session.current_stage == "stage_1"
    assert session.approved_stages == []


def test_stage_manager_rejects_approval_before_current_stage_runs():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(StageTransitionError, match="must be run before approval"):
        manager.approve_stage(session, "stage_1")


def test_stage_manager_rejects_non_current_stage_output():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(StageTransitionError, match="cannot store output"):
        manager.store_stage_response(session, make_response(session, stage_id="stage_2"))


def test_stage_manager_rollback_prunes_target_and_later_state():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    session = approve_and_advance(manager, session)
    session = approve_and_advance(manager, session)
    session = run_current_stage(manager, session, summary="verification")

    session = manager.rollback_to(session, "stage_2", reason="data risk")

    assert session.current_stage == "stage_2"
    assert session.approved_stages == ["stage_1"]
    assert set(session.stage_outputs) == {"stage_1"}
    assert session.metadata["last_rollback_reason"] == "data risk"
    assert session.rollback_events[-1].target_stage == "stage_2"
    assert session.rollback_events[-1].invalidated_stages == ["stage_2", "stage_3"]


def test_stage_manager_advance_from_final_stage_is_noop_after_approval():
    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")

    for stage_id in ["stage_1", "stage_2", "stage_3"]:
        session = run_current_stage(manager, session)
        manager.approve_stage(session, stage_id)
        session = manager.advance_stage(session)

    assert session.current_stage == "stage_4"

    session = run_current_stage(manager, session)
    manager.approve_stage(session, "stage_4")
    session = manager.advance_stage(session)

    assert session.current_stage == "stage_4"
    assert session.approved_stages == ["stage_1", "stage_2", "stage_3", "stage_4"]


def test_sqlite_session_store_persists_across_manager_reload(tmp_path):
    db_path = tmp_path / "sessions.sqlite"
    first_manager = StageManager(store=SQLiteSessionStore(db_path))
    session = first_manager.create_session(scenario="dispatch_recommendation")
    session = run_current_stage(first_manager, session, summary="persisted output")

    reloaded_manager = StageManager(store=SQLiteSessionStore(db_path))
    reloaded = reloaded_manager.get_session(session.session_id)

    assert reloaded.stage_outputs["stage_1"]["summary"] == "persisted output"
    assert reloaded.current_stage == "stage_1"
