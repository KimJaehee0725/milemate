"""OpenAI-compatible vLLM client boundary."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib import request

from app.backend.core.config_loader import get_model_runtime_config


class VLLMClient:
    """Small injectable client for an OpenAI-compatible local vLLM endpoint."""

    def __init__(self, runtime_config: Optional[Dict[str, Any]] = None) -> None:
        self.runtime_config = runtime_config or get_model_runtime_config()

    def build_chat_completion_request(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model or self.runtime_config["model_id"],
            "messages": messages,
            "temperature": (
                self.runtime_config["temperature"] if temperature is None else temperature
            ),
            "max_tokens": (
                self.runtime_config["max_output_tokens"] if max_tokens is None else max_tokens
            ),
        }
        payload.update(extra)
        return payload

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        payload = self.build_chat_completion_request(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        api_key = self.runtime_config.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = request.Request(
            self.runtime_config["chat_completions_url"],
            data=body,
            method="POST",
            headers=headers,
        )
        with request.urlopen(req, timeout=self.runtime_config["timeout"]) as response:
            return json.loads(response.read().decode("utf-8"))
