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
    assert cfg.model.model_id == "google/gemma-4-26B-A4B-it"
    assert cfg.serving.engine == "vllm"


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


def test_model_runtime_config_exposes_vllm_ready_settings():
    runtime = get_model_runtime_config()
    assert runtime["engine"] == "vllm"
    assert runtime["provider"] == "huggingface"
    assert runtime["api_style"] == "openai_compatible"
    assert runtime["chat_completions_url"].endswith("/chat/completions")
