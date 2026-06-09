"""Codex CLI boundary for structured stage generation."""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.backend.core.config_loader import get_model_runtime_config
from app.backend.schemas.common import Citation, DecisionItem, ErrorCode, RiskItem
from app.backend.schemas.stage import PrdPacket, PrdQualityReport, StageOutputBundle
from app.backend.services.prd_packet_verifier import PrdPacketVerifier

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class CodexClientError(RuntimeError):
    """Base error for model generation failures with API-facing error codes."""

    def __init__(self, message: str, error_code: ErrorCode) -> None:
        super().__init__(message)
        self.error_code = error_code


class ModelNotConfiguredError(CodexClientError):
    def __init__(self, message: str = "Codex CLI is not configured") -> None:
        super().__init__(message, ErrorCode.MODEL_NOT_CONFIGURED)


class ModelCallFailedError(CodexClientError):
    def __init__(self, message: str = "Codex CLI model call failed") -> None:
        super().__init__(message, ErrorCode.MODEL_CALL_FAILED)


class ModelOutputInvalidError(CodexClientError):
    def __init__(self, message: str = "Codex CLI output did not match the stage schema") -> None:
        super().__init__(message, ErrorCode.MODEL_OUTPUT_INVALID)


class CodexViewSection(BaseModel):
    """A strict structured-output section converted into the existing view dicts."""

    model_config = ConfigDict(extra="forbid")

    key: str
    text: str
    items: List[str]


class CodexStageDraft(BaseModel):
    """Structured output returned by Codex before app-owned fields are injected."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    prd_packet: PrdPacket
    planner_sections: List[CodexViewSection]
    engineer_sections: List[CodexViewSection]
    decision_points: List[DecisionItem]
    required_user_input: List[str]
    risks: List[RiskItem]
    external_citations: List[Citation] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("summary must not be blank")
        return value


class CodexClient:
    """Injectable client for Codex model calls via `codex exec`."""

    def __init__(
        self,
        runtime_config: Optional[Dict[str, Any]] = None,
        command_runner: Optional[CommandRunner] = None,
        cwd: Optional[Path | str] = None,
    ) -> None:
        self.runtime_config = runtime_config or get_model_runtime_config()
        self.command_runner = command_runner or subprocess.run
        self.cwd = Path(cwd) if cwd is not None else None
        self.prd_verifier = PrdPacketVerifier()

    def build_cli_command(
        self,
        output_path: str,
        schema_path: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[str]:
        command = [
            str(self.runtime_config.get("cli_binary", "codex")),
            "--search",
            "exec",
            "-m",
            model or str(self.runtime_config["model_id"]),
            "--ephemeral",
            "--json",
            "--sandbox",
            "read-only",
        ]
        reasoning_effort = str(self.runtime_config.get("reasoning_effort") or "").strip()
        if reasoning_effort:
            command.extend(["-c", f"model_reasoning_effort={json.dumps(reasoning_effort)}"])
        if schema_path is not None:
            command.extend(["--output-schema", schema_path])
        command.extend(["--output-last-message", output_path])
        return command

    def build_stage_cli_request(
        self,
        stage_id: str,
        scenario: str,
        user_input: str,
        context: Dict[str, Any],
        citations: List[Citation],
        approved_state: Dict[str, Any],
        proposal_state: Dict[str, Any],
        evidence_state: Dict[str, Any],
        collected_risks: List[RiskItem],
        rollback_targets: List[str],
        scenario_metadata: Dict[str, Any],
        output_path: str,
        schema_path: str,
    ) -> Dict[str, Any]:
        return {
            "command": self.build_cli_command(
                output_path=output_path,
                schema_path=schema_path,
            ),
            "prompt": self._stage_prompt(
                stage_id=stage_id,
                scenario=scenario,
                user_input=user_input,
                context=context,
                citations=citations,
                approved_state=approved_state,
                proposal_state=proposal_state,
                evidence_state=evidence_state,
                collected_risks=collected_risks,
                rollback_targets=rollback_targets,
                scenario_metadata=scenario_metadata,
            ),
        }

    def generate_text(
        self,
        instructions: str,
        input_text: str,
        model: Optional[str] = None,
        **_: Any,
    ) -> str:
        prompt = "\n\n".join([instructions.strip(), input_text.strip()]).strip()
        with tempfile.TemporaryDirectory(prefix="milemate-codex-") as tmp_dir:
            output_path = str(Path(tmp_dir) / "output.txt")
            command = self.build_cli_command(output_path=output_path, model=model)
            self._run_command(command=command, prompt=prompt)
            return self._read_output_text(Path(output_path))

    def generate_stage_output(
        self,
        stage_id: str,
        scenario: str,
        user_input: str,
        context: Dict[str, Any],
        citations: List[Citation],
        approved_state: Dict[str, Any],
        proposal_state: Dict[str, Any],
        evidence_state: Dict[str, Any],
        collected_risks: List[RiskItem],
        rollback_targets: List[str],
        scenario_metadata: Dict[str, Any],
    ) -> StageOutputBundle:
        with tempfile.TemporaryDirectory(prefix="milemate-codex-") as tmp_dir:
            tmp_path = Path(tmp_dir)
            schema_path = tmp_path / "stage_schema.json"
            output_path = tmp_path / "stage_output.json"
            self._write_stage_schema(schema_path)
            request = self.build_stage_cli_request(
                stage_id=stage_id,
                scenario=scenario,
                user_input=user_input,
                context=context,
                citations=citations,
                approved_state=approved_state,
                proposal_state=proposal_state,
                evidence_state=evidence_state,
                collected_risks=collected_risks,
                rollback_targets=rollback_targets,
                scenario_metadata=scenario_metadata,
                output_path=str(output_path),
                schema_path=str(schema_path),
            )

            self._run_command(command=request["command"], prompt=request["prompt"])
            draft = self._parse_stage_draft(output_path)
            output = self._draft_to_stage_output(
                draft=draft,
                stage_id=stage_id,
                app_citations=citations,
                rollback_targets=rollback_targets,
                repair_attempted=False,
            )
            if output.prd_quality.status == "ready":
                return output

            repair_output_path = tmp_path / "stage_output_repair.json"
            repair_command = self.build_cli_command(
                output_path=str(repair_output_path),
                schema_path=str(schema_path),
            )
            self._run_command(
                command=repair_command,
                prompt=self._repair_stage_prompt(
                    original_prompt=request["prompt"],
                    draft=draft,
                    quality=output.prd_quality,
                ),
            )
            repaired_draft = self._parse_stage_draft(repair_output_path)
            return self._draft_to_stage_output(
                draft=repaired_draft,
                stage_id=stage_id,
                app_citations=citations,
                rollback_targets=rollback_targets,
                repair_attempted=True,
            )

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

    def _run_command(self, command: Sequence[str], prompt: str) -> None:
        try:
            result = self.command_runner(
                list(command),
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.runtime_config.get("timeout"),
                cwd=str(self.cwd) if self.cwd else None,
            )
        except FileNotFoundError as exc:
            raise ModelNotConfiguredError("codex CLI binary was not found") from exc
        except subprocess.TimeoutExpired as exc:
            raise ModelCallFailedError("codex CLI call timed out") from exc
        except OSError as exc:
            raise ModelCallFailedError(str(exc)) from exc

        if result.returncode != 0:
            message = self._command_error_message(result)
            if self._looks_like_auth_or_config_error(message):
                raise ModelNotConfiguredError(message)
            raise ModelCallFailedError(message)

    @staticmethod
    def _command_error_message(result: subprocess.CompletedProcess[str]) -> str:
        combined = "\n".join(
            item.strip()
            for item in [result.stderr or "", result.stdout or ""]
            if item and item.strip()
        )
        return combined or f"codex CLI exited with status {result.returncode}"

    @staticmethod
    def _looks_like_auth_or_config_error(message: str) -> bool:
        lowered = message.lower()
        return any(
            marker in lowered
            for marker in [
                "auth is not configured",
                "not logged in",
                "login",
                "authentication",
                "unauthorized",
                "codex cli binary was not found",
            ]
        )

    @staticmethod
    def _write_stage_schema(path: Path) -> None:
        from openai.lib._pydantic import to_strict_json_schema

        schema = to_strict_json_schema(CodexStageDraft)
        CodexClient._close_schema_objects(schema)
        path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _close_schema_objects(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and node.get("additionalProperties") is not False:
                node["additionalProperties"] = False
                node.setdefault("properties", {})
            for value in node.values():
                CodexClient._close_schema_objects(value)
        elif isinstance(node, list):
            for item in node:
                CodexClient._close_schema_objects(item)

    @staticmethod
    def _read_output_text(path: Path) -> str:
        if not path.exists():
            raise ModelOutputInvalidError("codex CLI did not write an output file")
        return path.read_text(encoding="utf-8").strip()

    @classmethod
    def _parse_stage_draft(cls, path: Path) -> CodexStageDraft:
        text = cls._read_output_text(path)
        try:
            payload = json.loads(text)
            return CodexStageDraft.model_validate(payload)
        except json.JSONDecodeError as exc:
            raise ModelOutputInvalidError(str(exc)) from exc
        except ValidationError as exc:
            raise ModelOutputInvalidError(str(exc)) from exc

    @staticmethod
    def _sections_to_view(
        sections: List[CodexViewSection],
        stage_id: str = "",
        view_name: str = "",
    ) -> Dict[str, Any]:
        view: Dict[str, Any] = {}
        list_keys = CodexClient._list_section_keys(stage_id=stage_id, view_name=view_name)
        for section in sections:
            if section.key in list_keys:
                view[section.key] = section.items if section.items else [section.text]
            else:
                view[section.key] = section.items if section.items else section.text
        return view

    @staticmethod
    def _merge_citations(*citation_groups: List[Citation]) -> List[Citation]:
        merged: List[Citation] = []
        seen: set[str] = set()
        for group in citation_groups:
            for item in group:
                locator = item.locator.strip()
                key = locator or f"{item.source_type}:{item.title}"
                if key in seen:
                    continue
                merged.append(item)
                seen.add(key)
        return merged

    def _draft_to_stage_output(
        self,
        *,
        draft: CodexStageDraft,
        stage_id: str,
        app_citations: List[Citation],
        rollback_targets: List[str],
        repair_attempted: bool,
    ) -> StageOutputBundle:
        citations = self._merge_citations(
            app_citations,
            draft.external_citations,
            draft.prd_packet.evidence_links,
        )
        prd_packet = draft.prd_packet.model_copy(update={"evidence_links": citations})
        prd_quality = self.prd_verifier.evaluate(
            prd_packet,
            citations,
            repair_attempted=repair_attempted,
            require_external_url=True,
        )
        return StageOutputBundle(
            summary=draft.summary,
            planner_view=self._sections_to_view(
                draft.planner_sections,
                stage_id=stage_id,
                view_name="planner",
            ),
            engineer_view=self._sections_to_view(
                draft.engineer_sections,
                stage_id=stage_id,
                view_name="engineer",
            ),
            prd_packet=prd_packet,
            prd_quality=prd_quality,
            decision_points=draft.decision_points,
            required_user_input=draft.required_user_input,
            citations=citations,
            risks=draft.risks,
            rollback_targets=rollback_targets,
        )

    @staticmethod
    def _repair_stage_prompt(
        *,
        original_prompt: str,
        draft: CodexStageDraft,
        quality: PrdQualityReport,
    ) -> str:
        repair_payload = {
            "repair_goal": (
                "The previous JSON was valid but not ready for a planner/developer "
                "meeting. Return a complete replacement JSON matching the same schema."
            ),
            "quality_findings": quality.model_dump(mode="json"),
            "previous_output": draft.model_dump(mode="json"),
            "repair_rules": [
                "Keep all user-facing values in Korean.",
                "Keep real citation URLs only; do not invent citation locators.",
                (
                    "Fill PRD fields with concrete screen, policy, KPI, data, "
                    "event log, and handoff detail."
                ),
                (
                    "Preserve the human approval workflow and proposed decision "
                    "status unless prior approval is explicit."
                ),
            ],
        }
        return "\n\n".join(
            [
                original_prompt,
                "PRD quality repair request:",
                json.dumps(repair_payload, ensure_ascii=False, sort_keys=True),
            ]
        )

    @staticmethod
    def _list_section_keys(stage_id: str, view_name: str) -> set[str]:
        if stage_id != "stage_4":
            return set()
        if view_name == "planner":
            return {"target_users", "prioritized_kpis", "mvp_scope", "expected_value"}
        if view_name == "engineer":
            return {
                "required_data",
                "required_tech_blocks",
                "constraints",
                "implementation_order",
                "verification_plan",
            }
        return set()

    @staticmethod
    def _stage_prompt(
        stage_id: str,
        scenario: str,
        user_input: str,
        context: Dict[str, Any],
        citations: List[Citation],
        approved_state: Dict[str, Any],
        proposal_state: Dict[str, Any],
        evidence_state: Dict[str, Any],
        collected_risks: List[RiskItem],
        rollback_targets: List[str],
        scenario_metadata: Dict[str, Any],
    ) -> str:
        return "\n\n".join(
            [
                CodexClient._stage_instructions(stage_id),
                "Input JSON:",
                CodexClient._stage_input_text(
                    stage_id=stage_id,
                    scenario=scenario,
                    user_input=user_input,
                    context=context,
                    citations=citations,
                    approved_state=approved_state,
                    proposal_state=proposal_state,
                    evidence_state=evidence_state,
                    collected_risks=collected_risks,
                    rollback_targets=rollback_targets,
                    scenario_metadata=scenario_metadata,
                ),
            ]
        )

    @staticmethod
    def _stage_instructions(stage_id: str) -> str:
        stage_specific = ""
        if stage_id == "stage_3":
            stage_specific = (
                "For stage_3, use the evidence context to write a rollback recommendation "
                "inside planner_sections and engineer_sections when needed. Do not output "
                "rollback_targets; the application injects allowed rollback targets."
            )
        elif stage_id == "stage_4":
            stage_specific = (
                "For stage_4, planner_sections must include problem_redefinition, "
                "target_users, prioritized_kpis, mvp_scope, and expected_value. "
                "engineer_sections must include required_data, required_tech_blocks, "
                "constraints, implementation_order, and verification_plan."
            )

        return "\n".join(
            [
                "You are milemate's Codex stage generation agent.",
                "Return only JSON that matches the provided output schema.",
                (
                    "Write every user-facing value in Korean. This includes summaries, "
                    "section text, list items, decisions, required user input, risks, "
                    "and mitigations."
                ),
                (
                    "Do not translate schema keys, stage ids, citation locators, or "
                    "rollback target ids."
                ),
                (
                    "Use live web_search actively for external evidence. Prefer recent "
                    "operator, logistics, product, legal, or market references that help "
                    "a service planning decision."
                ),
                (
                    "Put every web source you actually used in external_citations. "
                    "Each external citation locator must be a real URL from the search "
                    "result or page you inspected. Do not invent titles, URLs, or locators."
                ),
                "For every citation object, set metadata to an empty object: {}.",
                (
                    "Provided input citations are app-owned baseline references. You may "
                    "use them in reasoning, but do not duplicate them in external_citations."
                ),
                (
                    "Do not output rollback_targets; the application injects allowed "
                    "rollback targets."
                ),
                (
                    "Preserve the human approval workflow; decisions should remain "
                    "proposed unless prior approved state justifies otherwise."
                ),
                (
                    "The prd_packet is the primary deliverable. Write it as a full "
                    "Korean service PRD that a non-engineer planner can bring to a "
                    "developer meeting."
                ),
                (
                    "Translate service planning intent about demand, supply, cost, "
                    "operations, marketing promises, and customer trust into concrete "
                    "screens, policies, KPIs, data requirements, event logs, and "
                    "developer handoff notes."
                ),
                (
                    "Every screen must include user actions and acceptance criteria. "
                    "Every metric must include baseline, target, measurement method, "
                    "and owner. Every data requirement must include source, freshness, "
                    "purpose, and quality rule."
                ),
                "Planner and engineer sections must be presentation-ready and concise.",
                (
                    "For every section, set key plus either text for scalar content "
                    "or items for list content. Use an empty string or empty list for "
                    "the unused field."
                ),
                "Decision statuses must be proposed, approved, deferred, or rejected.",
                (
                    "Risk categories must be data, technical, operational, "
                    "regulatory, scope, or other."
                ),
                "Do not run shell commands or inspect files; use only the input JSON.",
                "Use the native web_search tool for external research; do not use shell commands.",
                stage_specific,
            ]
        ).strip()

    @staticmethod
    def _stage_input_text(
        stage_id: str,
        scenario: str,
        user_input: str,
        context: Dict[str, Any],
        citations: List[Citation],
        approved_state: Dict[str, Any],
        proposal_state: Dict[str, Any],
        evidence_state: Dict[str, Any],
        collected_risks: List[RiskItem],
        rollback_targets: List[str],
        scenario_metadata: Dict[str, Any],
    ) -> str:
        payload = {
            "current_date": date.today().isoformat(),
            "stage_id": stage_id,
            "scenario": scenario,
            "scenario_metadata": scenario_metadata,
            "user_input": user_input,
            "context": context,
            "approved_prior_stage_state": approved_state,
            "proposal_state": proposal_state,
            "evidence_context": evidence_state,
            "citations": [item.model_dump(mode="json") for item in citations],
            "allowed_rollback_targets": rollback_targets,
            "collected_risks": [item.model_dump(mode="json") for item in collected_risks],
            "external_research_expectation": {
                "use_web_search": True,
                "minimum_external_sources": 2,
                "include_links_in_external_citations": True,
                "preferred_sources": [
                    "official company or product documentation",
                    "government or legal guidance",
                    "credible logistics or operations case studies",
                    "recent market or industry reports",
                ],
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
