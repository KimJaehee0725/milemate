"""YAML config loader placeholder."""

from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def load_yaml(name: str):
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_app_config():
    return {
        "app": load_yaml("app.yaml"),
        "stages": load_yaml("stages.yaml"),
        "scenarios": load_yaml("scenarios.yaml"),
        "sources": load_yaml("sources.yaml"),
        "prompts": load_yaml("prompts.yaml"),
        "mcp": load_yaml("mcp-hub.yaml"),
    }
