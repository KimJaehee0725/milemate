# Configuration Notes

YAML is the single source of truth for stage definitions, scenarios, source categories, prompt paths, and MCP mappings.

Principles:
- avoid duplicated constants across modules
- load scenario/stage/source metadata from config
- keep prompt paths and source mappings declarative
- use backend config loader as the shared entrypoint
- manage prompts as files, not inline strings
- organize prompts by agent and stage so ownership is explicit

Prompt convention:
- prompts/agents/{agent_name}/system.txt
- prompts/agents/{agent_name}/{agent_name}_stage1.txt
- prompts/agents/{agent_name}/{agent_name}_stage2.txt
- prompts/agents/{agent_name}/{agent_name}_stage3.txt
- prompts/agents/{agent_name}/{agent_name}_stage4.txt

Runtime config convention:
- app.yaml contains app/model/serving/huggingface/storage/features
- stages.yaml contains stage definitions and rollback targets
- scenarios.yaml contains scenario metadata
- sources.yaml contains retrieval/citation metadata
- prompts.yaml contains prompt file paths by agent and stage
- mcp-hub.yaml contains MCP server definitions and source mappings

Model serving convention:
- local inference is assumed to be vLLM first
- model metadata is tracked under `model:`
- serving endpoint metadata is tracked under `serving:`
- Hugging Face local/cache/token metadata is tracked under `huggingface:`
- config_loader should expose a single `get_model_runtime_config()` helper for backend use
