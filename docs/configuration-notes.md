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
