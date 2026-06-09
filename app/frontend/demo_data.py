"""Demo input helpers shared by the Streamlit app and tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

VERIFICATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "Configured evidence": {},
    "Missing data": {"data_sources": []},
    "Poor labels": {"label_quality": "poor"},
}


def load_demo_inputs(root_dir: Path) -> Dict[str, Dict[str, Any]]:
    inputs: Dict[str, Dict[str, Any]] = {}
    for path in sorted((root_dir / "data" / "demo_inputs").glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            item = json.load(f)
        scenario = item.get("scenario")
        if scenario:
            inputs[scenario] = item
    return inputs


def scenario_title(demo_inputs: Dict[str, Dict[str, Any]], scenario_id: str) -> str:
    return str(demo_inputs.get(scenario_id, {}).get("title", ""))


def scenario_display_title(demo_inputs: Dict[str, Dict[str, Any]], scenario_id: str) -> str:
    item = demo_inputs.get(scenario_id, {})
    return str(item.get("display_title") or item.get("title") or scenario_id)


def scenario_initial_input(demo_inputs: Dict[str, Dict[str, Any]], scenario_id: str) -> str:
    item = demo_inputs.get(scenario_id, {})
    brief = item.get("demo_brief") if isinstance(item.get("demo_brief"), dict) else {}
    return str(
        item.get("initial_input")
        or brief.get("summary")
        or item.get("display_title")
        or item.get("title")
        or ""
    )


def scenario_brief(demo_inputs: Dict[str, Dict[str, Any]], scenario_id: str) -> Dict[str, Any]:
    item = demo_inputs.get(scenario_id, {})
    brief = item.get("demo_brief") if isinstance(item.get("demo_brief"), dict) else {}
    return {
        "title": scenario_display_title(demo_inputs, scenario_id),
        "subtitle": str(item.get("subtitle") or brief.get("subtitle") or ""),
        "summary": str(
            brief.get("summary")
            or item.get("initial_input")
            or item.get("title")
            or ""
        ),
        "presentation_goal": str(brief.get("presentation_goal") or ""),
        "decision_focus": list(brief.get("decision_focus") or []),
        "demo_highlights": list(brief.get("demo_highlights") or []),
        "sidebar_note": str(brief.get("sidebar_note") or ""),
    }


def verification_context_for_preset(
    preset: str,
    scenario_input: Dict[str, Any],
) -> Dict[str, Any]:
    context = dict(VERIFICATION_PRESETS.get(preset, {}))
    if "data_sources" not in context and scenario_input.get("data_sources"):
        context["data_sources"] = scenario_input["data_sources"]
    return context
