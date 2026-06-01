import pytest

from app.backend.core.agent_graph import AgentGraphInput, MilemateAgentGraphRunner
from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageManager, StageTransitionError
from app.frontend.demo_backend import LocalFakeCodexClient

REQUIRED_STAGE_OUTPUT_KEYS = {
    "summary",
    "planner_view",
    "engineer_view",
    "prd_packet",
    "prd_quality",
    "decision_points",
    "required_user_input",
    "citations",
    "risks",
    "rollback_targets",
}


def make_orchestrator():
    manager = StageManager()
    return manager, Orchestrator(
        stage_manager=manager,
        graph_runner=MilemateAgentGraphRunner(codex_client=LocalFakeCodexClient()),
    )


def test_orchestrator_runs_dispatch_stage_1_to_stage_4_without_fastapi():
    manager, orchestrator = make_orchestrator()
    session = manager.create_session(
        scenario="dispatch_recommendation",
        user_input="peak dispatch bottleneck",
    )

    seen_stage_ids = []
    for expected_stage in ["stage_1", "stage_2", "stage_3", "stage_4"]:
        response = orchestrator.run_current_stage(session.session_id)
        seen_stage_ids.append(response.stage_id)
        assert response.stage_id == expected_stage
        assert response.status == "completed"
        assert response.output.summary

        session = orchestrator.approve_current_stage(session.session_id)

    assert seen_stage_ids == ["stage_1", "stage_2", "stage_3", "stage_4"]
    assert session.current_stage == "stage_4"
    assert session.approved_stages == ["stage_1", "stage_2", "stage_3", "stage_4"]

    report = orchestrator.build_final_report(session.session_id)
    assert report.planner_report.problem_redefinition
    assert report.engineer_report.required_data
    assert report.prd_report.screens
    assert report.prd_quality.status == "ready"
    assert report.decision_log
    assert report.citations


def test_orchestrator_stage_outputs_keep_common_rendering_contract():
    manager, orchestrator = make_orchestrator()
    session = manager.create_session(scenario="dispatch_recommendation")

    for expected_stage in ["stage_1", "stage_2", "stage_3", "stage_4"]:
        response = orchestrator.run_current_stage(session.session_id)
        output = response.output.model_dump()

        assert response.stage_id == expected_stage
        assert REQUIRED_STAGE_OUTPUT_KEYS <= set(output)
        assert isinstance(output["summary"], str)
        assert isinstance(output["planner_view"], dict)
        assert isinstance(output["engineer_view"], dict)
        assert isinstance(output["prd_packet"], dict)
        assert isinstance(output["prd_quality"], dict)
        assert isinstance(output["decision_points"], list)
        assert isinstance(output["required_user_input"], list)
        assert isinstance(output["citations"], list)
        assert isinstance(output["risks"], list)
        assert isinstance(output["rollback_targets"], list)

        session = orchestrator.approve_current_stage(session.session_id)


def test_orchestrator_fake_codex_fixture_is_deterministic_for_same_stage_input():
    first_manager, first_orchestrator = make_orchestrator()
    first_session = first_manager.create_session(
        scenario="dispatch_recommendation",
        user_input="same input",
    )

    second_manager, second_orchestrator = make_orchestrator()
    second_session = second_manager.create_session(
        scenario="dispatch_recommendation",
        user_input="same input",
    )

    first_response = first_orchestrator.run_current_stage(first_session.session_id)
    second_response = second_orchestrator.run_current_stage(second_session.session_id)

    assert first_response.stage_id == second_response.stage_id == "stage_1"
    assert first_response.output.model_dump() == second_response.output.model_dump()


def test_orchestrator_uses_graph_runner_boundary():
    manager, orchestrator = make_orchestrator()

    assert set(manager.stage_ids()) <= set(orchestrator.graph_runner.nodes)


def test_orchestrator_rejects_final_report_before_stage_4_approval():
    manager, orchestrator = make_orchestrator()
    session = manager.create_session(scenario="dispatch_recommendation")

    with pytest.raises(StageTransitionError, match="stage_4 must be run"):
        orchestrator.build_final_report(session.session_id)

    for _ in ["stage_1", "stage_2", "stage_3"]:
        orchestrator.run_current_stage(session.session_id)
        session = orchestrator.approve_current_stage(session.session_id)

    orchestrator.run_current_stage(session.session_id)
    with pytest.raises(StageTransitionError, match="stage_4 must be approved"):
        orchestrator.build_final_report(session.session_id)


def test_orchestrator_accepts_fake_retrieval_and_legal_clients():
    class FakeRetrieval:
        def search(self, query, source_type, scenario=None, top_k=1):
            return [
                {
                    "source_type": source_type,
                    "title": "fake retrieval",
                    "locator": f"fake://{scenario}/{top_k}",
                    "relevance_note": query,
                }
            ]

    class FakeLegal:
        def search(self, query):
            return [
                {
                    "source_type": "laws",
                    "title": "fake law",
                    "locator": "fake://law",
                    "relevance_note": query,
                    "metadata": {"disclaimer": "Reference material only; not legal advice."},
                }
            ]

    manager = StageManager()
    orchestrator = Orchestrator(
        stage_manager=manager,
        retrieval=FakeRetrieval(),
        legal=FakeLegal(),
        graph_runner=MilemateAgentGraphRunner(codex_client=LocalFakeCodexClient()),
    )
    session = manager.create_session(scenario="dispatch_recommendation")

    response = orchestrator.run_current_stage(session.session_id)

    assert response.output.citations[0].title == "fake retrieval"


def test_graph_runner_uses_injected_codex_stage_client():
    class FakeCodex:
        def generate_stage_output(
            self,
            stage_id,
            scenario,
            user_input,
            context,
            citations,
            approved_state,
            proposal_state,
            evidence_state,
            collected_risks,
            rollback_targets,
            scenario_metadata,
        ):
            assert stage_id == "stage_1"
            assert scenario == "dispatch_recommendation"
            assert user_input == "codex stage"
            assert context == {"demo": True}
            from app.backend.schemas.stage import StageOutputBundle

            return StageOutputBundle(
                summary="generated by injected codex",
                planner_view={"problem_summary": "fake"},
                engineer_view={"core_data": ["orders"]},
                decision_points=[],
                required_user_input=[],
                citations=[],
                risks=[],
                rollback_targets=["stage_4"],
            )

    manager = StageManager()
    session = manager.create_session(scenario="dispatch_recommendation")
    runner = MilemateAgentGraphRunner(codex_client=FakeCodex())
    graph_input = AgentGraphInput(
        session=session,
        stage_id="stage_1",
        user_input="codex stage",
        context={"demo": True},
        citations=[],
        approved_state={},
        proposal_state={},
        evidence_state={},
        collected_risks=[],
    )

    output = runner.run(graph_input)

    assert output.summary == "generated by injected codex"
    assert output.rollback_targets == []
    assert output.engineer_view["graph_runtime"] in {
        "microsoft_agent_framework_core",
        "openai_codex_responses",
    }
