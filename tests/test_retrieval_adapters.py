import pytest

from app.backend.core.config_loader import load_app_config


def test_source_categories_exist_in_config():
    cfg = load_app_config()
    for key in ["papers", "technical_docs", "laws", "patents", "datasets", "industry_cases"]:
        assert key in cfg.sources.categories


def test_law_source_references_legalize_repository():
    cfg = load_app_config()
    laws = cfg.sources.categories["laws"]
    assert any("legalize-kr" in repo for repo in laws.repositories)


@pytest.mark.xfail(reason="Retrieval adapter contract not implemented yet")
def test_retrieval_adapter_returns_citation_ready_results():
    from app.backend.integrations.retrieval_adapter import RetrievalAdapter

    adapter = RetrievalAdapter()
    results = adapter.search("dynamic dispatch last-mile", source_type="technical_docs")

    assert isinstance(results, list)
    assert results
    first = results[0]
    for key in ["source_type", "title", "locator", "relevance_note"]:
        assert key in first


@pytest.mark.xfail(reason="Legal adapter contract not implemented yet")
def test_legal_adapter_can_search_korean_law_sources():
    from app.backend.integrations.legal_adapter import LegalAdapter

    adapter = LegalAdapter()
    results = adapter.search("개인정보 위치정보 배송 알림")

    assert isinstance(results, list)
    assert results is not None
