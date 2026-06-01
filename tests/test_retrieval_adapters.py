from app.backend.core.config_loader import load_app_config
from app.backend.integrations.retrieval_adapter import RetrievalAdapter
from app.backend.integrations.vllm_client import VLLMClient
from app.backend.schemas.retrieval import RetrievalResult


def test_source_categories_exist_in_config():
    cfg = load_app_config()
    for key in ["papers", "technical_docs", "laws", "patents", "datasets", "industry_cases"]:
        assert key in cfg.sources.categories


def test_law_source_references_legalize_repository():
    cfg = load_app_config()
    laws = cfg.sources.categories["laws"]
    assert any("legalize-kr" in repo for repo in laws.repositories)


def test_retrieval_adapter_returns_citation_ready_results():
    adapter = RetrievalAdapter()
    results = adapter.search("dynamic dispatch last-mile", source_type="technical_docs")

    assert isinstance(results, list)
    assert results
    first = results[0]
    for key in load_app_config().sources.citation_schema.required_fields:
        assert key in first
    assert first["metadata"]["provider"] == "static"


def test_legal_adapter_can_search_korean_law_sources():
    from app.backend.integrations.legal_adapter import LegalAdapter

    adapter = LegalAdapter()
    results = adapter.search("개인정보 위치정보 배송 알림")

    assert isinstance(results, list)
    assert results is not None
    assert results[0]["source_type"] == "laws"
    assert "not legal advice" in results[0]["metadata"]["disclaimer"]


def test_retrieval_adapter_accepts_fake_provider_without_network():
    class FakeProvider:
        def search(self, query, source_type="technical_docs", scenario=None, top_k=5):
            return [
                RetrievalResult(
                    source_type=source_type,
                    title="fake provider result",
                    locator=f"fake://{scenario or 'general'}",
                    relevance_note=query,
                    metadata={"provider": "fake"},
                )
            ]

    adapter = RetrievalAdapter(providers=[FakeProvider()])
    results = adapter.search(
        "dispatch evidence",
        source_type="industry_cases",
        scenario="dispatch_recommendation",
    )

    assert results[0]["title"] == "fake provider result"
    assert results[0]["metadata"]["provider"] == "fake"


def test_vllm_client_builds_openai_compatible_request_without_calling_network():
    client = VLLMClient(
        runtime_config={
            "model_id": "local-test-model",
            "temperature": 0.1,
            "max_output_tokens": 128,
            "chat_completions_url": "http://127.0.0.1:8001/v1/chat/completions",
            "api_key": None,
            "timeout": 5,
        }
    )

    payload = client.build_chat_completion_request(
        messages=[{"role": "user", "content": "hello"}],
        response_format={"type": "json_object"},
    )

    assert payload["model"] == "local-test-model"
    assert payload["messages"][0]["role"] == "user"
    assert payload["temperature"] == 0.1
    assert payload["max_tokens"] == 128
    assert payload["response_format"] == {"type": "json_object"}
