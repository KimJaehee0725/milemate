from pathlib import Path

from app.frontend.demo_data import (
    load_demo_inputs,
    scenario_title,
    verification_context_for_preset,
)

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_demo_inputs_are_loaded_by_scenario():
    inputs = load_demo_inputs(ROOT_DIR)

    assert inputs["dispatch_recommendation"]["title"] == "dynamic dispatch sample"
    assert inputs["eta_prediction"]["title"] == "eta sample"
    assert inputs["failed_delivery_risk"]["title"] == "failed delivery sample"


def test_scenario_title_uses_selected_demo_input():
    inputs = load_demo_inputs(ROOT_DIR)

    assert scenario_title(inputs, "eta_prediction") == "eta sample"


def test_stage_3_verification_preset_builds_context():
    context = verification_context_for_preset(
        "Poor labels",
        {"data_sources": ["orders"]},
    )

    assert context["label_quality"] == "poor"
    assert context["data_sources"] == ["orders"]
