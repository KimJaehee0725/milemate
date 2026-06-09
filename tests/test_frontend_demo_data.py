from pathlib import Path

from app.frontend.demo_data import (
    load_demo_inputs,
    scenario_brief,
    scenario_display_title,
    scenario_initial_input,
    scenario_title,
    verification_context_for_preset,
)

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_demo_inputs_are_loaded_by_scenario():
    inputs = load_demo_inputs(ROOT_DIR)

    assert inputs["dispatch_recommendation"]["title"] == "dynamic dispatch sample"
    assert inputs["eta_prediction"]["title"] == "eta sample"
    assert inputs["failed_delivery_risk"]["title"] == "failed delivery sample"
    assert (
        inputs["dispatch_recommendation"]["display_title"]
        == "CleanGo 적용 예시: 피크타임 배차 추천"
    )


def test_scenario_title_uses_selected_demo_input():
    inputs = load_demo_inputs(ROOT_DIR)

    assert scenario_title(inputs, "eta_prediction") == "eta sample"


def test_scenario_brief_prefers_rich_korean_demo_fields():
    inputs = load_demo_inputs(ROOT_DIR)

    assert scenario_display_title(inputs, "eta_prediction") == "CleanGo 적용 예시: ETA 지연 안내"
    assert "고객은 도착 시간을 신뢰" in scenario_initial_input(inputs, "eta_prediction")

    brief = scenario_brief(inputs, "dispatch_recommendation")
    assert brief["title"] == "CleanGo 적용 예시: 피크타임 배차 추천"
    assert "의사결정 흐름" in brief["demo_highlights"][-1]
    assert brief["decision_focus"]


def test_scenario_brief_falls_back_to_legacy_title_shape():
    inputs = {"legacy": {"scenario": "legacy", "title": "legacy sample"}}

    assert scenario_display_title(inputs, "legacy") == "legacy sample"
    assert scenario_initial_input(inputs, "legacy") == "legacy sample"
    assert scenario_brief(inputs, "legacy")["summary"] == "legacy sample"


def test_stage_3_verification_preset_builds_context():
    context = verification_context_for_preset(
        "Poor labels",
        {"data_sources": ["orders"]},
    )

    assert context["label_quality"] == "poor"
    assert context["data_sources"] == ["orders"]
