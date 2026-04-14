"""FastAPI entrypoint placeholder."""

from app.backend.core.config_loader import load_app_config


def get_app_config():
    return load_app_config()
