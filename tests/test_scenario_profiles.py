from app.backend.services.planner_service import PlannerService
from app.backend.services.scenario_profiles import (
    PROFILE_KEYS,
    get_scenario_profile,
    scenario_keys,
)

SCENARIOS = [
    "dispatch_recommendation",
    "eta_prediction",
    "failed_delivery_risk",
    "rider_onboarding_dropout",
    "return_pickup_flow",
    "checkout_fee_transparency",
    "merchant_prep_visibility",
    "cs_repeat_inquiry_triage",
]


def test_every_profile_exposes_the_same_keys():
    for scenario in scenario_keys():
        assert set(get_scenario_profile(scenario).keys()) == PROFILE_KEYS


def test_unknown_scenario_falls_back_to_dispatch():
    fallback = get_scenario_profile("does_not_exist")
    assert fallback["event_prefix"] == "dispatch"


def test_planner_stage_outputs_differ_by_scenario():
    planner = PlannerService()
    summaries = {
        scenario: planner.build_stage_output("stage_1", scenario).prd_packet.one_page_summary
        for scenario in SCENARIOS
    }
    assert len({summary[:40] for summary in summaries.values()}) == len(SCENARIOS)


def test_planner_screens_are_scenario_specific():
    planner = PlannerService()
    eta = planner.build_stage_output("stage_2", "eta_prediction").prd_packet.screens[0].name
    failed = planner.build_stage_output(
        "stage_2", "failed_delivery_risk"
    ).prd_packet.screens[0].name
    assert "알림" in eta
    assert "실패" in failed


def test_event_log_names_carry_scenario_prefix():
    planner = PlannerService()
    for scenario in SCENARIOS:
        packet = planner.build_stage_output("stage_1", scenario).prd_packet
        prefix = get_scenario_profile(scenario)["event_prefix"]
        assert packet.event_logs[0].event_name.startswith(prefix)
