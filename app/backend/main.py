"""FastAPI entrypoint for the milemate mock MVP."""

from __future__ import annotations

from fastapi import FastAPI

from app.backend.api.routes_report import router as report_router
from app.backend.api.routes_runtime import router as runtime_router
from app.backend.api.routes_session import router as session_router
from app.backend.api.routes_stage import router as stage_router
from app.backend.core.config_loader import RootConfig, load_app_config
from app.backend.core.orchestrator import Orchestrator
from app.backend.core.stage_manager import StageManager


def create_app(
    stage_manager: StageManager | None = None,
    orchestrator: Orchestrator | None = None,
    config: RootConfig | None = None,
) -> FastAPI:
    app_config = config or load_app_config()
    manager = stage_manager or StageManager(config=app_config)
    runtime = orchestrator or Orchestrator(stage_manager=manager)

    app = FastAPI(title="milemate Mock MVP", version="0.1.0")
    app.state.config = app_config
    app.state.stage_manager = manager
    app.state.orchestrator = runtime

    app.include_router(session_router)
    app.include_router(stage_router)
    app.include_router(report_router)
    app.include_router(runtime_router)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "app": app_config.app.name}

    return app


def get_app_config() -> RootConfig:
    return load_app_config()


app = create_app()
