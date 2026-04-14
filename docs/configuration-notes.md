# Configuration Notes

YAML is the single source of truth for stage definitions, scenarios, source categories, prompt paths, and MCP mappings.

Principles:
- avoid duplicated constants across modules
- load scenario/stage/source metadata from config
- keep prompt paths and source mappings declarative
- use backend config loader as the shared entrypoint
