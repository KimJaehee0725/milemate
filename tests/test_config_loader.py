from app.backend.core.config_loader import (
    get_model_runtime_config,
    get_prompt_path,
    get_scenario_definition,
    get_stage_definition,
    load_app_config,
)


def test_config_loader_loads_root_config():
    cfg = load_app_config()
    assert cfg.app.name == "last-mile-planning-agent"
    assert cfg.model.model_id == "gpt-5.2-codex"
    assert cfg.serving.engine == "codex_sdk"
    assert cfg.storage.stage_state == "memory"


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
    assert runtime["engine"] == "codex_sdk"
    assert runtime["provider"] == "openai"
    assert runtime["api_style"] == "responses"
    assert runtime["model_id"] == "gpt-5.2-codex"
