# Prompts

Prompts are managed as plain text files by agent and stage.

Convention:
- prompts/agents/{agent_name}/system.txt
- prompts/agents/{agent_name}/{agent_name}_stage1.txt
- prompts/agents/{agent_name}/{agent_name}_stage2.txt
- prompts/agents/{agent_name}/{agent_name}_stage3.txt
- prompts/agents/{agent_name}/{agent_name}_stage4.txt

This makes prompt ownership explicit and avoids mixing common prompts and scenario overlays in the same folder.
