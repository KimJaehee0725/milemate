"""Application configuration loader.

Loads YAML config files, resolves environment placeholders, and returns typed
configuration objects suitable for Microsoft Agent Framework orchestration,
local vLLM serving, and Hugging Face model metadata.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_env_string(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return os.getenv(key, "")

    return ENV_PATTERN.sub(repl, value)


def _resolve_env_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _resolve_env_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_values(v) for v in value]
    if isinstance(value, str):
        return _resolve_env_string(value)
    return value


class BackendSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class FrontendSettings(BaseModel):
    framework: str = "streamlit"


class DefaultSettings(BaseModel):
    default_scenario: str = "dispatch_recommendation"
    citation_limit: int = 5
    allow_rollback: bool = True


class AppSection(BaseModel):
    name: str
    environment: str = "local"
    backend: BackendSettings
    frontend: FrontendSettings
    defaults: DefaultSettings


class ModelSettings(BaseModel):
    provider: str = "huggingface"
    model_id: str
    dtype: str = "auto"
    max_context_tokens: int = 32768
    temperature: float = 0.2
    max_output_tokens: int = 2048
    api_style: str = "openai_compatible"


class ServingSettings(BaseModel):
    engine: str = "vllm"
    base_url: str
    chat_completions_path: str = "/chat/completions"
    models_path: str = "/models"
    api_key_env: str = "VLLM_API_KEY"
    request_timeout_seconds: int = 120

    @property
    def api_key(self) -> Optional[str]:
        return os.getenv(self.api_key_env)

    @property
    def chat_completions_url(self) -> str:
        return self.base_url.rstrip("/") + self.chat_completions_path

    @property
    def models_url(self) -> str:
        return self.base_url.rstrip("/") + self.models_path


class HuggingFaceSettings(BaseModel):
    cache_dir: Optional[str] = None
    token_env: str = "HUGGINGFACE_HUB_TOKEN"
    trust_remote_code: bool = False

    @property
    def token(self) -> Optional[str]:
        return os.getenv(self.token_env)


class StorageSettings(BaseModel):
    stage_state: str = "sqlite"
    stage_state_path: str = "data/app_state.sqlite"
    memory_mode: str = "local"


class FeatureSettings(BaseModel):
    use_mcp: bool = True
    use_verifier: bool = True
    use_long_term_memory: bool = False
    require_stage_approval: bool = True


class StageDefinition(BaseModel):
    id: str
    name: str
    title: str
    required_approval: bool = True
    outputs: List[str] = Field(default_factory=list)
    rollback_targets: List[str] = Field(default_factory=list)


class StagesConfig(BaseModel):
    stages: List[StageDefinition]

    def by_id(self) -> Dict[str, StageDefinition]:
        return {stage.id: stage for stage in self.stages}


class ScenarioDefinition(BaseModel):
    label: str
    primary_users: List[str] = Field(default_factory=list)
    primary_kpis: List[str] = Field(default_factory=list)
    core_data: List[str] = Field(default_factory=list)


class ScenariosConfig(BaseModel):
    scenarios: Dict[str, ScenarioDefinition]


class SourceCategory(BaseModel):
    enabled: bool = True
    priority: int = 1
    retrieval_modes: List[str] = Field(default_factory=list)
    repositories: List[str] = Field(default_factory=list)


class CitationSchema(BaseModel):
    required_fields: List[str] = Field(default_factory=list)


class SourcesConfig(BaseModel):
    categories: Dict[str, SourceCategory]
    citation_schema: CitationSchema


class AgentPromptStageMap(BaseModel):
    stage_1: Optional[str] = None
    stage_2: Optional[str] = None
    stage_3: Optional[str] = None
    stage_4: Optional[str] = None


class AgentPromptConfig(BaseModel):
    system: str
    stages: AgentPromptStageMap


class RenderingConfig(BaseModel):
    planner_sections: List[str] = Field(default_factory=list)
    engineer_sections: List[str] = Field(default_factory=list)


class PromptsConfig(BaseModel):
    agents: Dict[str, AgentPromptConfig]
    rendering: RenderingConfig


class MCPServerConfig(BaseModel):
    enabled: bool = True
    transport: str
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    auth_env: Optional[str] = None

    @property
    def auth_value(self) -> Optional[str]:
        return os.getenv(self.auth_env) if self.auth_env else None


class MCPConfig(BaseModel):
    mcp_servers: Dict[str, MCPServerConfig]
    source_mapping: Dict[str, List[str]]


class RootConfig(BaseModel):
    app: AppSection
    model: ModelSettings
    serving: ServingSettings
    huggingface: HuggingFaceSettings
    storage: StorageSettings
    features: FeatureSettings
    stages: StagesConfig
    scenarios: ScenariosConfig
    sources: SourcesConfig
    prompts: PromptsConfig
    mcp: MCPConfig

    @model_validator(mode="after")
    def validate_defaults(self) -> "RootConfig":
        scenario_name = self.app.defaults.default_scenario
        if scenario_name not in self.scenarios.scenarios:
            raise ValueError(f"default scenario '{scenario_name}' not found in scenarios.yaml")
        return self


def load_yaml(name: str) -> Dict[str, Any]:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _resolve_env_values(data)


@lru_cache(maxsize=1)
def load_app_config() -> RootConfig:
    merged = {
        **load_yaml("app.yaml"),
        "stages": load_yaml("stages.yaml").get("stages", []),
        "scenarios": load_yaml("scenarios.yaml").get("scenarios", {}),
        "sources": load_yaml("sources.yaml").get("sources", {}),
        "prompts": load_yaml("prompts.yaml").get("prompts", {}),
        "mcp": load_yaml("mcp-hub.yaml"),
    }

    normalized = {
        "app": merged["app"],
        "model": merged["model"],
        "serving": merged["serving"],
        "huggingface": merged["huggingface"],
        "storage": merged["storage"],
        "features": merged["features"],
        "stages": {"stages": merged["stages"]},
        "scenarios": {"scenarios": merged["scenarios"]},
        "sources": merged["sources"],
        "prompts": merged["prompts"],
        "mcp": merged["mcp"],
    }
    return RootConfig.model_validate(normalized)


def reload_app_config() -> RootConfig:
    load_app_config.cache_clear()
    return load_app_config()


def get_stage_definition(stage_id: str) -> Optional[StageDefinition]:
    config = load_app_config()
    return config.stages.by_id().get(stage_id)


def get_scenario_definition(scenario_name: str) -> Optional[ScenarioDefinition]:
    config = load_app_config()
    return config.scenarios.scenarios.get(scenario_name)


def get_prompt_path(agent_name: str, stage_id: Optional[str] = None) -> Optional[Path]:
    config = load_app_config()
    agent = config.prompts.agents.get(agent_name)
    if not agent:
        return None
    if stage_id is None:
        return Path(agent.system)

    stage_map = {
        "stage_1": agent.stages.stage_1,
        "stage_2": agent.stages.stage_2,
        "stage_3": agent.stages.stage_3,
        "stage_4": agent.stages.stage_4,
    }
    value = stage_map.get(stage_id)
    return Path(value) if value else None


def get_model_runtime_config() -> Dict[str, Any]:
    config = load_app_config()
    return {
        "provider": config.model.provider,
        "model_id": config.model.model_id,
        "dtype": config.model.dtype,
        "temperature": config.model.temperature,
        "max_output_tokens": config.model.max_output_tokens,
        "api_style": config.model.api_style,
        "engine": config.serving.engine,
        "base_url": config.serving.base_url,
        "chat_completions_url": config.serving.chat_completions_url,
        "api_key": config.serving.api_key,
        "timeout": config.serving.request_timeout_seconds,
        "hf_cache_dir": config.huggingface.cache_dir,
        "hf_token": config.huggingface.token,
        "trust_remote_code": config.huggingface.trust_remote_code,
    }
