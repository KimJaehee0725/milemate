import importlib.util
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "eval_pipeline", ROOT_DIR / "eval" / "pipeline.py"
)
pipeline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pipeline)


def _all_pass_grades():
    return {item_id: "pass" for item_id in pipeline.ALL_ITEM_IDS}


def test_checklist_structure_is_32_items():
    assert len(pipeline.ALL_ITEM_IDS) == 32
    assert pipeline.NA_ALLOWED_ITEMS == {"D5-4", "D8-1"}


def test_dimension_score_formula():
    grades = _all_pass_grades()
    assert pipeline.dimension_score(grades, "D1") == 5.0

    grades["D1-1"] = "fail"
    grades["D1-2"] = "partial"
    # earned 2.5 / 4 items -> 1 + 4 * 0.625 = 3.5
    assert pipeline.dimension_score(grades, "D1") == 3.5


def test_na_excluded_from_denominator_only_where_allowed():
    grades = _all_pass_grades()
    grades["D5-4"] = "na"
    # D5 has 4 items, one valid na -> 3 valid, all pass -> 5.0
    assert pipeline.dimension_score(grades, "D5") == 5.0

    grades["D1-1"] = "na"  # not allowed -> treated as fail
    assert pipeline.dimension_score(grades, "D1") == 4.0


def test_penalty_caps():
    assert pipeline.penalty_deduction([]) == 0.0
    assert pipeline.penalty_deduction(["P1", "P1"]) == 0.5
    assert pipeline.penalty_deduction(["P2"] * 5) == 1.5
    assert pipeline.penalty_deduction(["P3"] * 4) == 1.5
    assert pipeline.penalty_deduction(["P4", "P4"]) == 2.0


def test_document_scores_total_subtracts_penalty():
    scores = pipeline.document_scores(_all_pass_grades(), ["P4"])
    assert scores["base_total"] == 5.0
    assert scores["total"] == 4.0


def test_swapped_order_agreement():
    assert pipeline.agreed_verdict("B", "B") == "B"
    assert pipeline.agreed_verdict("A", "A") == "A"
    assert pipeline.agreed_verdict("B", "A") == "tie"
    assert pipeline.agreed_verdict("B", "tie") == "tie"


def test_doc_verdict_condition_mapping():
    assert pipeline.doc_verdict_to_condition("doc1", "AB") == "A"
    assert pipeline.doc_verdict_to_condition("doc1", "BA") == "B"
    assert pipeline.doc_verdict_to_condition("doc2", "BA") == "A"
    assert pipeline.doc_verdict_to_condition("tie", "AB") == "tie"


def test_mask_strips_process_mentions():
    text = "이 보고서는 1단계 문제 정의와 stage_3 검증을 거쳐 작성됐다."
    masked = pipeline.mask_process_mentions(text)
    assert "1단계" not in masked
    assert "stage_3" not in masked
    assert "[프로세스]" in masked


def test_normalize_flattens_headers_and_tables():
    text = "### 제목\n| a | b |\n|---|---|\n| 1 | 2 |\n**굵게**"
    normalized = pipeline.normalize_plain_text(text)
    assert normalized.startswith("## 제목")
    assert "|---|" not in normalized
    assert "**" not in normalized


def test_stage_requests_extracted_without_importing_streamlit():
    requests = pipeline.load_stage_requests()
    assert set(requests["default"]) == set(pipeline.STAGE_IDS)
    assert len(requests["per_scenario"]) == 8
    for stage_map in requests["per_scenario"].values():
        assert set(stage_map) == set(pipeline.STAGE_IDS)


def test_stage_inputs_use_initial_input_for_stage_1():
    requests = pipeline.load_stage_requests()
    inputs = pipeline.stage_inputs_for("dispatch_recommendation", "원래 훅", requests)
    assert inputs["stage_1"] == "원래 훅"
    assert inputs["stage_2"] == requests["per_scenario"]["dispatch_recommendation"][
        "stage_2"
    ]


def test_judge_schema_is_strict_and_complete():
    schema = pipeline.judge_output_schema()
    assert schema["additionalProperties"] is False
    item_enum = schema["properties"]["items"]["items"]["properties"]["item_id"]["enum"]
    assert len(item_enum) == 32


def test_checklist_body_extraction():
    body = pipeline.checklist_body()
    assert "채점 규칙" in body
    assert "D8-4" in body
    assert "판정자 출력 형식" not in body


def test_validate_judgment_flags_problems():
    judgment = {
        "items": [
            {
                "item_id": "D1-1",
                "doc1": {"grade": "na", "evidence": "", "missing": ""},
                "doc2": {"grade": "pass", "evidence": "", "missing": ""},
            }
        ],
        "penalties": {"doc1": [], "doc2": []},
        "overall_verdict": "tie",
        "confidence": "high",
    }
    warnings = pipeline.validate_judgment(judgment)
    assert any("missing items" in w for w in warnings)
    assert any("invalid na" in w for w in warnings)
    assert any("without evidence" in w for w in warnings)


def test_sign_test_and_bootstrap():
    assert pipeline.sign_test_p(0, 0) == 1.0
    assert pipeline.sign_test_p(10, 0) < 0.01
    assert abs(pipeline.sign_test_p(5, 5) - 1.0) < 1e-9
    low, high = pipeline.bootstrap_ci([1.0, 1.0, 1.0])
    assert low == high == 1.0


def test_render_report_text_walks_bundle():
    bundle = {
        "prd_report": {"one_page_summary": "요약", "screens": [{"name": "화면"}]},
        "risks": [{"description": "위험", "category": "data"}],
        "prd_quality": {"status": "ready"},
    }
    text = pipeline.render_report_text(bundle)
    assert "## 기획서 본문" in text
    assert "one_page_summary: 요약" in text
    assert "description: 위험" in text
    assert "prd_quality" not in text
