"""OpenAI Codex SDK boundary for stage generation."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from app.backend.core.config_loader import get_model_runtime_config


class CodexSDKClient(Protocol):
    """Subset of the OpenAI SDK client used by CodexClient."""

    responses: Any


class CodexClient:
    """Small injectable client for Codex model calls via the OpenAI SDK."""

    def __init__(
        self,
        runtime_config: Optional[Dict[str, Any]] = None,
        sdk_client: Optional[CodexSDKClient] = None,
    ) -> None:
        self.runtime_config = runtime_config or get_model_runtime_config()
        self._sdk_client = sdk_client

    def build_response_request(
        self,
        instructions: str,
        input_text: str,
        model: Optional[str] = None,
        reasoning_effort: str = "medium",
        **extra: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model or self.runtime_config["model_id"],
            "instructions": instructions,
            "input": input_text,
            "reasoning": {"effort": reasoning_effort},
        }
        payload.update(extra)
        return payload

    def generate_text(
        self,
        instructions: str,
        input_text: str,
        model: Optional[str] = None,
        reasoning_effort: str = "medium",
        **extra: Any,
    ) -> str:
        payload = self.build_response_request(
            instructions=instructions,
            input_text=input_text,
            model=model,
            reasoning_effort=reasoning_effort,
            **extra,
        )
        response = self.sdk_client.responses.create(**payload)
        return str(getattr(response, "output_text", ""))

    def generate_stage_text(
        self,
        stage_id: str,
        scenario: str,
        user_input: str,
        context: Dict[str, Any],
    ) -> str:
        instructions = (
            "You are milemate's stage planning agent. Return concise, structured "
            "planning guidance for the requested stage."
        )
        input_text = "\n".join(
            [
                f"stage_id: {stage_id}",
                f"scenario: {scenario}",
                f"user_input: {user_input}",
                f"context: {context}",
            ]
        )
        return self.generate_text(instructions=instructions, input_text=input_text)

    @property
    def sdk_client(self) -> CodexSDKClient:
        if self._sdk_client is None:
            from openai import OpenAI

            self._sdk_client = OpenAI()
        return self._sdk_client
