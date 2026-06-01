from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib import error, request

import streamlit as st
import yaml

from app.frontend.demo_data import (
    VERIFICATION_PRESETS,
    load_demo_inputs,
    scenario_title,
    verification_context_for_preset,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
API_BASE_URL = os.getenv("MILEMATE_API_BASE", "http://127.0.0.1:8000").rstrip("/")


def api_request(method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{API_BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Backend unavailable at {API_BASE_URL}: {exc.reason}") from exc


@st.cache_data
def load_scenarios() -> Dict[str, Dict[str, Any]]:
    with open(ROOT_DIR / "config" / "scenarios.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["scenarios"]


@st.cache_data
def load_demo_input_map() -> Dict[str, Dict[str, Any]]:
    return load_demo_inputs(ROOT_DIR)


def render_list(items: Iterable[Any]) -> None:
    for item in items:
        st.markdown(f"- {item}")


def render_value(value: Any) -> None:
    if isinstance(value, dict):
        st.json(value, expanded=False)
    elif isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            st.dataframe(value, width="stretch", hide_index=True)
        else:
            render_list(value)
    else:
        st.write(value)


def render_key_values(data: Dict[str, Any]) -> None:
    for key, value in data.items():
        st.markdown(f"**{key.replace('_', ' ').title()}**")
        render_value(value)


def render_stage_output(stage_response: Dict[str, Any]) -> None:
    output = stage_response.get("output", {})
    st.subheader(f"{stage_response.get('stage_id', '').replace('_', ' ').title()} Output")
    st.write(output.get("summary", ""))

    planner_tab, engineer_tab, decisions_tab, evidence_tab = st.tabs(
        ["Planner", "Engineer", "Decisions", "Evidence"]
    )
    with planner_tab:
        render_key_values(output.get("planner_view", {}))
    with engineer_tab:
        render_key_values(output.get("engineer_view", {}))
    with decisions_tab:
        decisions = output.get("decision_points", [])
        if decisions:
            st.dataframe(decisions, width="stretch", hide_index=True)
        required = output.get("required_user_input", [])
        if required:
            st.markdown("**Required Input**")
            render_list(required)
    with evidence_tab:
        risks = output.get("risks", [])
        if risks:
            st.markdown("**Risks**")
            st.dataframe(risks, width="stretch", hide_index=True)
        citations = output.get("citations", [])
        if citations:
            st.markdown("**Citations**")
            st.dataframe(citations, width="stretch", hide_index=True)


def render_session(session: Dict[str, Any]) -> None:
    st.caption(f"Session {session['session_id']}")
    cols = st.columns(3)
    cols[0].metric("Current stage", session["current_stage"])
    cols[1].metric("Approved", len(session.get("approved_stages", [])))
    cols[2].metric("Outputs", len(session.get("stage_outputs", {})))

    history = session.get("stage_history", [])
    if history:
        st.dataframe(history, width="stretch", hide_index=True)
    rollback_events = session.get("rollback_events", [])
    if rollback_events:
        st.markdown("**Rollback History**")
        st.dataframe(rollback_events, width="stretch", hide_index=True)


def render_report(report: Dict[str, Any]) -> None:
    st.subheader("Final Report")
    planner_tab, engineer_tab, log_tab = st.tabs(
        ["Planner Report", "Engineer Report", "Decision Log"]
    )
    with planner_tab:
        render_key_values(report.get("planner_report", {}))
    with engineer_tab:
        render_key_values(report.get("engineer_report", {}))
    with log_tab:
        st.dataframe(report.get("decision_log", []), width="stretch", hide_index=True)


def set_error(message: str) -> None:
    st.session_state["error"] = message


def clear_error() -> None:
    st.session_state["error"] = ""


def sync_input_to_scenario() -> None:
    scenario_id = st.session_state["scenario_id"]
    st.session_state["user_input"] = scenario_title(st.session_state["demo_inputs"], scenario_id)
    st.session_state["session"] = None
    st.session_state["stage_response"] = None
    st.session_state["report"] = None
    clear_error()


def refresh_session(session_id: str) -> None:
    st.session_state["session"] = api_request("GET", f"/sessions/{session_id}")


def current_stage_response(session: Dict[str, Any]) -> Dict[str, Any] | None:
    current_stage = session["current_stage"]
    output = session.get("stage_outputs", {}).get(current_stage)
    if not output:
        return None
    return {
        "session_id": session["session_id"],
        "stage_id": current_stage,
        "status": "completed",
        "output": output,
    }


st.set_page_config(page_title="milemate", layout="wide")
st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 1.25rem; }
    div[data-testid="stMetric"] {
      border: 1px solid #d8dee4;
      background: #f6f8fa;
      padding: 10px 12px;
    }
    div[data-testid="stMetric"] label { color: #57606a; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("milemate")

scenarios = load_scenarios()
demo_inputs = load_demo_input_map()
default_scenario = (
    "dispatch_recommendation"
    if "dispatch_recommendation" in scenarios
    else next(iter(scenarios))
)

if "demo_inputs" not in st.session_state:
    st.session_state["demo_inputs"] = demo_inputs
if "scenario_id" not in st.session_state:
    st.session_state["scenario_id"] = default_scenario
if "user_input" not in st.session_state:
    st.session_state["user_input"] = scenario_title(demo_inputs, default_scenario)
if "session" not in st.session_state:
    st.session_state["session"] = None
if "stage_response" not in st.session_state:
    st.session_state["stage_response"] = None
if "report" not in st.session_state:
    st.session_state["report"] = None
if "error" not in st.session_state:
    st.session_state["error"] = ""

with st.sidebar:
    scenario_id = st.selectbox(
        "Scenario",
        options=list(scenarios),
        format_func=lambda key: scenarios[key]["label"],
        key="scenario_id",
        on_change=sync_input_to_scenario,
    )
    user_input = st.text_area(
        "Input",
        height=92,
        key="user_input",
    )
    verification_preset = st.selectbox(
        "Stage 3 Check",
        options=list(VERIFICATION_PRESETS),
        key="verification_preset",
    )
    if st.button("Start Session", type="primary", width="stretch"):
        try:
            clear_error()
            st.session_state["session"] = api_request(
                "POST",
                "/sessions",
                {"scenario": scenario_id, "user_input": user_input},
            )
            st.session_state["stage_response"] = None
            st.session_state["report"] = None
        except RuntimeError as exc:
            set_error(str(exc))

    st.divider()
    st.caption(f"Backend {API_BASE_URL}")

if st.session_state["error"]:
    st.error(st.session_state["error"])

session = st.session_state["session"]
if not session:
    st.info("Start a session from the sidebar.")
    st.stop()

if (
    st.session_state["stage_response"]
    and st.session_state["stage_response"].get("stage_id") != session["current_stage"]
):
    st.session_state["stage_response"] = None

render_session(session)

action_cols = st.columns([1, 1, 1, 2])
with action_cols[0]:
    if st.button("Run Stage", width="stretch"):
        try:
            clear_error()
            context = {}
            if session["current_stage"] == "stage_3":
                context = verification_context_for_preset(
                    verification_preset,
                    demo_inputs.get(scenario_id, {}),
                )
            st.session_state["stage_response"] = api_request(
                "POST",
                "/stages/run",
                {
                    "session_id": session["session_id"],
                    "user_input": user_input,
                    "context": context,
                },
            )
            refresh_session(session["session_id"])
            st.session_state["report"] = None
            st.rerun()
        except RuntimeError as exc:
            set_error(str(exc))

with action_cols[1]:
    can_approve = session["current_stage"] in session.get("stage_outputs", {})
    if st.button("Approve / Next", width="stretch", disabled=not can_approve):
        try:
            clear_error()
            previous_stage = session["current_stage"]
            st.session_state["session"] = api_request(
                "POST",
                "/stages/approve",
                {"session_id": session["session_id"]},
            )
            st.session_state["stage_response"] = None
            if previous_stage == "stage_4":
                st.session_state["report"] = api_request("GET", f"/reports/{session['session_id']}")
            st.rerun()
        except RuntimeError as exc:
            set_error(str(exc))

with action_cols[2]:
    if st.button("Refresh", width="stretch"):
        try:
            clear_error()
            refresh_session(session["session_id"])
            st.session_state["stage_response"] = None
            st.rerun()
        except RuntimeError as exc:
            set_error(str(exc))

stage_response = st.session_state["stage_response"] or current_stage_response(session)
rollback_targets = []
if stage_response:
    rollback_targets = stage_response.get("output", {}).get("rollback_targets", [])

if rollback_targets:
    with action_cols[3]:
        rollback_cols = st.columns([1, 2, 1])
        target = rollback_cols[0].selectbox(
            "Rollback",
            rollback_targets,
            label_visibility="collapsed",
        )
        reason = rollback_cols[1].text_input(
            "Reason",
            "scope/data risk",
            label_visibility="collapsed",
        )
        if rollback_cols[2].button("Rollback", width="stretch"):
            try:
                clear_error()
                st.session_state["session"] = api_request(
                    "POST",
                    "/stages/rollback",
                    {
                        "session_id": session["session_id"],
                        "target_stage": target,
                        "reason": reason,
                    },
                )
                st.session_state["stage_response"] = None
                st.session_state["report"] = None
                st.rerun()
            except RuntimeError as exc:
                set_error(str(exc))

if stage_response:
    render_stage_output(stage_response)

if st.session_state["report"]:
    render_report(st.session_state["report"])
