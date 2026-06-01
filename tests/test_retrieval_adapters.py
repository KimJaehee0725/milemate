import json
import subprocess

import pytest

from app.backend.core.config_loader import load_app_config
from app.backend.integrations.codex_client import (
    CodexClient,
    CodexStageDraft,
    ModelCallFailedError,
    ModelNotConfiguredError,
    ModelOutputInvalidError,
)
from app.backend.integrations.retrieval_adapter import RetrievalAdapter
from app.backend.schemas.common import Citation, ErrorCode
from app.backend.schemas.retrieval import RetrievalResult
from app.backend.schemas.stage import PrdPacket
from app.backend.services.prd_packet_factory import build_demo_prd_packet


def prd_payload(stage_id="stage_1"):
    return build_demo_prd_packet(
        stage_id=stage_id,
        scenario="dispatch_recommendation",
        summary="테스트용 PRD",
    ).model_dump(mode="json")


def test_source_categories_exist_in_config():
    cfg = load_app_config()
    for key in ["papers", "technical_docs", "laws", "patents", "datasets", "industry_cases"]:
        assert key in cfg.sources.categories


def test_law_source_references_legalize_repository():
    cfg = load_app_config()
    laws = cfg.sources.categories["laws"]
    assert any("legalize-kr" in repo for repo in laws.repositories)


def test_retrieval_adapter_returns_citation_ready_results():
    adapter = RetrievalAdapter()
    results = adapter.search("dynamic dispatch last-mile", source_type="technical_docs")

    assert isinstance(results, list)
    assert results
    first = results[0]
    for key in load_app_config().sources.citation_schema.required_fields:
        assert key in first
    assert first["metadata"]["provider"] == "static"


def test_legal_adapter_can_search_korean_law_sources():
    from app.backend.integrations.legal_adapter import LegalAdapter

    adapter = LegalAdapter()
    results = adapter.search("개인정보 위치정보 배송 알림")

    assert isinstance(results, list)
    assert results is not None
    assert results[0]["source_type"] == "laws"
    assert "not legal advice" in results[0]["metadata"]["disclaimer"]


def test_retrieval_adapter_accepts_fake_provider_without_network():
    class FakeProvider:
        def search(self, query, source_type="technical_docs", scenario=None, top_k=5):
            return [
                RetrievalResult(
                    source_type=source_type,
                    title="fake provider result",
                    locator=f"fake://{scenario or 'general'}",
                    relevance_note=query,
                    metadata={"provider": "fake"},
                )
            ]

    adapter = RetrievalAdapter(providers=[FakeProvider()])
    results = adapter.search(
        "dispatch evidence",
        source_type="industry_cases",
        scenario="dispatch_recommendation",
    )

    assert results[0]["title"] == "fake provider result"
    assert results[0]["metadata"]["provider"] == "fake"


def test_codex_client_builds_cli_command_without_calling_network():
    client = CodexClient(
        runtime_config={
            "model_id": "gpt-5.5",
            "provider": "openai",
            "api_style": "responses",
            "engine": "codex_cli",
            "cli_binary": "codex",
            "timeout": 5,
        }
    )

    command = client.build_cli_command(
        output_path="/tmp/out.json",
        schema_path="/tmp/schema.json",
    )

    assert command[:5] == ["codex", "--search", "exec", "-m", "gpt-5.5"]
    assert "--ephemeral" in command
    assert "--json" in command
    assert "--search" in command
    assert command[command.index("--output-schema") + 1] == "/tmp/schema.json"
    assert command[command.index("--output-last-message") + 1] == "/tmp/out.json"


def test_codex_client_uses_injected_command_runner_without_network():
    class FakeRunner:
        def __init__(self):
            self.calls = []

        def __call__(self, command, **kwargs):
            self.calls.append((command, kwargs))
            output_path = command[command.index("--output-last-message") + 1]
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("codex generated note")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    fake_runner = FakeRunner()
    client = CodexClient(
        runtime_config={"model_id": "gpt-5.5", "cli_binary": "codex", "timeout": 5},
        command_runner=fake_runner,
    )

    result = client.generate_text(instructions="Do work", input_text="hello")

    assert result == "codex generated note"
    command, kwargs = fake_runner.calls[0]
    assert command[:5] == ["codex", "--search", "exec", "-m", "gpt-5.5"]
    assert "Do work" in kwargs["input"]
    assert "hello" in kwargs["input"]


def test_codex_client_calls_codex_exec_with_stage_schema():
    class FakeRunner:
        def __init__(self):
            self.command = None
            self.prompt = None
            self.schema = None

        def __call__(self, command, **kwargs):
            self.command = command
            self.prompt = kwargs["input"]
            schema_path = command[command.index("--output-schema") + 1]
            output_path = command[command.index("--output-last-message") + 1]
            with open(schema_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "summary": "Codex generated a stage plan.",
                        "prd_packet": prd_payload("stage_1"),
                        "planner_sections": [
                            {
                                "key": "problem_summary",
                                "text": "Dispatchers need a clearer risk queue.",
                                "items": [],
                            }
                        ],
                        "engineer_sections": [
                            {"key": "core_data", "text": "", "items": ["orders", "couriers"]}
                        ],
                        "decision_points": [
                            {
                                "item": "Keep dispatcher approval in the loop.",
                                "status": "proposed",
                                "rationale": "Limits operational risk.",
                            }
                        ],
                        "required_user_input": ["Confirm the pilot zone."],
                        "risks": [
                            {
                                "category": "data",
                                "severity": "medium",
                                "description": "Location freshness may be uneven.",
                                "mitigation": "Show confidence in the UI.",
                            }
                        ],
                        "external_citations": [
                            {
                                "source_type": "industry_cases",
                                "title": "External source",
                                "locator": "https://example.com/source",
                                "relevance_note": "web source used by Codex",
                            }
                        ],
                    },
                    f,
                )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    fake_runner = FakeRunner()
    citation = Citation(
        source_type="technical_docs",
        title="reference",
        locator="doc://1",
        relevance_note="relevant",
    )
    client = CodexClient(
        runtime_config={
            "model_id": "gpt-5.5",
            "reasoning_effort": "medium",
            "cli_binary": "codex",
            "timeout": 5,
        },
        command_runner=fake_runner,
    )

    output = client.generate_stage_output(
        stage_id="stage_1",
        scenario="dispatch_recommendation",
        user_input="peak dispatch",
        context={},
        citations=[citation],
        approved_state={},
        proposal_state={},
        evidence_state={"data_sources": ["orders"]},
        collected_risks=[],
        rollback_targets=["stage_1"],
        scenario_metadata={"user_input": "peak dispatch"},
    )

    assert fake_runner.command[:5] == ["codex", "--search", "exec", "-m", "gpt-5.5"]
    assert fake_runner.schema["title"] == CodexStageDraft.__name__
    assert "prd_packet" in fake_runner.schema["properties"]
    assert fake_runner.schema["$defs"]["Citation"]["properties"]["metadata"][
        "additionalProperties"
    ] is False
    assert '"stage_id": "stage_1"' in fake_runner.prompt
    assert "Write every user-facing value in Korean" in fake_runner.prompt
    assert "Use live web_search actively" in fake_runner.prompt
    assert "metadata to an empty object" in fake_runner.prompt
    assert '"minimum_external_sources": 2' in fake_runner.prompt
    assert "Do not translate schema keys" in fake_runner.prompt
    assert output.planner_view["problem_summary"] == "Dispatchers need a clearer risk queue."
    assert output.engineer_view["core_data"] == ["orders", "couriers"]
    assert output.prd_packet.screens
    assert output.prd_quality.status == "ready"
    assert [item.locator for item in output.citations] == [
        "doc://1",
        "https://example.com/source",
    ]
    assert output.rollback_targets == ["stage_1"]


def test_codex_stage_input_passes_missing_data_context_to_parse_payload():
    class FakeRunner:
        def __init__(self):
            self.prompt = None

        def __call__(self, command, **kwargs):
            self.prompt = kwargs["input"]
            output_path = command[command.index("--output-last-message") + 1]
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "summary": "Verification needs missing data resolved.",
                        "prd_packet": prd_payload("stage_3"),
                        "planner_sections": [
                            {
                                "key": "rollback_recommendation",
                                "text": "Return to problem definition to identify data owners.",
                                "items": [],
                            }
                        ],
                        "engineer_sections": [
                            {
                                "key": "required_data",
                                "text": "",
                                "items": ["order events", "courier locations"],
                            }
                        ],
                        "decision_points": [],
                        "required_user_input": ["Confirm missing data owner."],
                        "risks": [],
                    },
                    f,
                )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    fake_runner = FakeRunner()
    client = CodexClient(
        runtime_config={"model_id": "gpt-5.5", "cli_binary": "codex", "timeout": 5},
        command_runner=fake_runner,
    )

    client.generate_stage_output(
        stage_id="stage_3",
        scenario="dispatch_recommendation",
        user_input="",
        context={"data_sources": []},
        citations=[],
        approved_state={"mvp_scope": ["risk queue"]},
        proposal_state={"mvp_scope": ["risk queue"]},
        evidence_state={"data_sources": []},
        collected_risks=[],
        rollback_targets=["stage_1", "stage_2"],
        scenario_metadata={},
    )

    assert '"stage_id": "stage_3"' in fake_runner.prompt
    assert '"data_sources": []' in fake_runner.prompt
    assert '"allowed_rollback_targets": ["stage_1", "stage_2"]' in (
        fake_runner.prompt
    )


def test_codex_client_coerces_stage_4_report_list_sections():
    def stage_4_runner(command, **kwargs):
        output_path = command[command.index("--output-last-message") + 1]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": "Final report ready.",
                    "prd_packet": prd_payload("stage_4"),
                    "planner_sections": [
                        {
                            "key": "problem_redefinition",
                            "text": "Peak dispatch bottlenecks need triage.",
                            "items": [],
                        },
                        {
                            "key": "expected_value",
                            "text": "Reduce manual triage during peak windows.",
                            "items": [],
                        },
                    ],
                    "engineer_sections": [
                        {
                            "key": "required_data",
                            "text": "orders and courier locations",
                            "items": [],
                        }
                    ],
                    "decision_points": [],
                    "required_user_input": [],
                    "risks": [],
                },
                f,
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    client = CodexClient(
        runtime_config={"model_id": "gpt-5.5", "cli_binary": "codex", "timeout": 5},
        command_runner=stage_4_runner,
    )

    output = client.generate_stage_output(
        stage_id="stage_4",
        scenario="dispatch_recommendation",
        user_input="",
        context={},
        citations=[],
        approved_state={},
        proposal_state={},
        evidence_state={},
        collected_risks=[],
        rollback_targets=["stage_2", "stage_3"],
        scenario_metadata={},
    )

    assert output.planner_view["problem_redefinition"] == (
        "Peak dispatch bottlenecks need triage."
    )
    assert output.planner_view["expected_value"] == [
        "Reduce manual triage during peak windows."
    ]
    assert output.engineer_view["required_data"] == ["orders and courier locations"]


def test_codex_client_repairs_prd_quality_once():
    class FakeRunner:
        def __init__(self):
            self.prompts = []

        def __call__(self, command, **kwargs):
            self.prompts.append(kwargs["input"])
            output_path = command[command.index("--output-last-message") + 1]
            packet = (
                PrdPacket().model_dump(mode="json")
                if len(self.prompts) == 1
                else prd_payload("stage_1")
            )
            external_citations = (
                []
                if len(self.prompts) == 1
                else [
                    {
                        "source_type": "industry_cases",
                        "title": "External source",
                        "locator": "https://example.com/repair-source",
                        "relevance_note": "repair source",
                    }
                ]
            )
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "summary": "Repairable stage output.",
                        "prd_packet": packet,
                        "planner_sections": [],
                        "engineer_sections": [],
                        "decision_points": [],
                        "required_user_input": [],
                        "risks": [],
                        "external_citations": external_citations,
                    },
                    f,
                )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    fake_runner = FakeRunner()
    client = CodexClient(
        runtime_config={"model_id": "gpt-5.5", "cli_binary": "codex", "timeout": 5},
        command_runner=fake_runner,
    )

    output = client.generate_stage_output(
        stage_id="stage_1",
        scenario="dispatch_recommendation",
        user_input="",
        context={},
        citations=[],
        approved_state={},
        proposal_state={},
        evidence_state={},
        collected_risks=[],
        rollback_targets=[],
        scenario_metadata={},
    )

    assert len(fake_runner.prompts) == 2
    assert "PRD quality repair request" in fake_runner.prompts[1]
    assert output.prd_quality.status == "ready"
    assert output.prd_quality.repair_attempted is True
    assert output.prd_packet.screens


def test_codex_client_missing_cli_binary_raises_explicit_error():
    def missing_runner(command, **kwargs):
        raise FileNotFoundError("codex")

    client = CodexClient(
        runtime_config={"model_id": "gpt-5.5", "cli_binary": "missing-codex", "timeout": 5},
        command_runner=missing_runner,
    )

    with pytest.raises(ModelNotConfiguredError) as exc_info:
        client.generate_stage_output(
            stage_id="stage_1",
            scenario="dispatch_recommendation",
            user_input="",
            context={},
            citations=[],
            approved_state={},
            proposal_state={},
            evidence_state={},
            collected_risks=[],
            rollback_targets=[],
            scenario_metadata={},
        )

    assert exc_info.value.error_code == ErrorCode.MODEL_NOT_CONFIGURED


def test_codex_client_nonzero_command_raises_model_call_failed():
    def failing_runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout='{"type":"error","message":"model unavailable"}',
            stderr="",
        )

    client = CodexClient(
        runtime_config={"model_id": "gpt-5.5", "cli_binary": "codex", "timeout": 5},
        command_runner=failing_runner,
    )

    with pytest.raises(ModelCallFailedError) as exc_info:
        client.generate_stage_output(
            stage_id="stage_1",
            scenario="dispatch_recommendation",
            user_input="",
            context={},
            citations=[],
            approved_state={},
            proposal_state={},
            evidence_state={},
            collected_risks=[],
            rollback_targets=[],
            scenario_metadata={},
        )

    assert exc_info.value.error_code == ErrorCode.MODEL_CALL_FAILED


def test_codex_client_invalid_parsed_output_raises_model_output_invalid():
    def invalid_runner(command, **kwargs):
        output_path = command[command.index("--output-last-message") + 1]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": "",
                    "planner_sections": [],
                    "engineer_sections": [],
                    "decision_points": [],
                    "required_user_input": [],
                    "risks": [],
                },
                f,
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    client = CodexClient(
        runtime_config={"model_id": "gpt-5.5", "cli_binary": "codex", "timeout": 5},
        command_runner=invalid_runner,
    )

    with pytest.raises(ModelOutputInvalidError) as exc_info:
        client.generate_stage_output(
            stage_id="stage_1",
            scenario="dispatch_recommendation",
            user_input="",
            context={},
            citations=[],
            approved_state={},
            proposal_state={},
            evidence_state={},
            collected_risks=[],
            rollback_targets=[],
            scenario_metadata={},
        )

    assert exc_info.value.error_code == ErrorCode.MODEL_OUTPUT_INVALID
