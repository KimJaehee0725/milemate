from pathlib import Path

from app.frontend.demo_data import (
    load_demo_inputs,
    scenario_title,
    verification_context_for_preset,
)

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_demo_inputs_are_loaded_by_scenario():
    inputs = load_demo_inputs(ROOT_DIR)

    assert inputs["dispatch_recommendation"]["title"] == "강남/서초 피크타임 배차 집중 완화"
    assert inputs["eta_prediction"]["title"] == "지연 위험 주문 선제 안내"
    assert inputs["failed_delivery_risk"]["title"] == "실패 위험 주문 사전 개입"


def test_demo_inputs_expose_context_and_data_sources():
    inputs = load_demo_inputs(ROOT_DIR)

    for scenario_id in ("dispatch_recommendation", "eta_prediction", "failed_delivery_risk"):
        item = inputs[scenario_id]
        assert item.get("context")
        assert item.get("data_sources")
        assert item.get("constraints")


def test_scenario_title_uses_selected_demo_input():
    inputs = load_demo_inputs(ROOT_DIR)

    assert scenario_title(inputs, "eta_prediction") == "지연 위험 주문 선제 안내"


def test_stage_3_verification_preset_builds_context():
    context = verification_context_for_preset(
        "Poor labels",
        {"data_sources": ["orders"]},
    )

    assert context["label_quality"] == "poor"
    assert context["data_sources"] == ["orders"]
