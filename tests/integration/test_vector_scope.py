import numpy as np
from rag.index.engine import EvidenceIndex


def test_qdrant_queries_are_tenant_scoped(monkeypatch):
    import rag.index.engine as engine

    class Encoder:
        def encode(self, texts, **kwargs):
            return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)

    monkeypatch.setattr(engine, "encoder", lambda: Encoder())
    monkeypatch.setenv("QDRANT_URL", ":memory:")
    base = {
        "id": "scope-evidence",
        "persona": "ml",
        "type": "case_study",
        "text": "tenant scope test unique text",
        "project": "scope-project",
    }
    one = EvidenceIndex([dict(base, source="private-one")], tenant="vector-one")
    two = EvidenceIndex([dict(base, source="private-two")], tenant="vector-two")
    assert len(one.dense("scope test")) == 1 and len(two.dense("scope test")) == 1
    client, name = one.qdrant
    hits = client.query_points(name, query=[1.0, 0.0], query_filter=one.qdrant_filter, with_payload=True).points
    assert len(hits) == 1 and hits[0].payload["source"] == "private-one"


def test_empty_portfolio_abstains(monkeypatch):
    import rag.retriever as retriever

    retriever._index.cache_clear()
    monkeypatch.setattr(retriever, "load_corpus", lambda: [])
    assert retriever.retrieve("Unknown work", "ml", tenant="empty-portfolio") == []
