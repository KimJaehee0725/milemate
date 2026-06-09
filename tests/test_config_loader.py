from app.backend.core.config_loader import (
    get_model_runtime_config,
    get_prompt_path,
    get_scenario_definition,
    get_stage_definition,
    load_app_config,
)


def test_config_loader_loads_root_config():
    cfg = load_app_config()
    assert cfg.app.name == "milemate-planning-assistant"
    assert isinstance(cfg.model.model_id, str)  # 빈 문자열 허용 (기본 모델 사용)
    assert cfg.model.reasoning_effort == "medium"
    assert cfg.serving.engine == "codex_cli"
    assert cfg.serving.cli_binary == "codex"
    assert cfg.storage.stage_state == "memory"
    assert cfg.features.use_codex_generation is True
    assert cfg.features.allow_deterministic_fallback is False


def test_stage_definitions_available_from_config():
    stage = get_stage_definition("stage_3")
    assert stage is not None
    assert stage.name == "feasibility_verification"
    assert "stage_2" in stage.rollback_targets


def test_scenario_definitions_available_from_config():
    scenario = get_scenario_definition("dispatch_recommendation")
    assert scenario is not None
    assert scenario.label == "Dynamic Dispatch and Route Recommendation"
    assert "delay_rate" in scenario.primary_kpis


def test_prompt_paths_are_resolved_from_config():
    path = get_prompt_path("planner_agent", "stage_1")
    assert path is not None
    assert str(path).endswith("prompts/agents/planner_agent/planner_agent_stage1.txt")


def test_model_runtime_config_exposes_codex_ready_settings():
    runtime = get_model_runtime_config()
    assert runtime["engine"] == "codex_cli"
    assert runtime["provider"] == "openai"
    assert runtime["api_style"] == "responses"
    assert isinstance(runtime["model_id"], str)  # 빈 문자열 허용 (기본 모델 사용)
    assert runtime["reasoning_effort"] == "medium"
    assert runtime["cli_binary"] == "codex"
