"""Dense + BM25 index with persistent, content-addressed embedding caches."""

import hashlib
import json
import os
from functools import lru_cache
import numpy as np
from rank_bm25 import BM25Okapi
from core.settings import ROOT, RUNTIME, config
from rag.ingest.loaders import chunks

_encoder = None
_reranker = None


@lru_cache(maxsize=4)
def qdrant_client(url):
    from qdrant_client import QdrantClient

    return QdrantClient(":memory:") if url == ":memory:" else QdrantClient(url=url)


def encoder():
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        import torch

        name = os.getenv("GIGBID_EMBEDDING_PATH", config()["models"]["embeddings"])
        _encoder = SentenceTransformer(
            name,
            device="cuda" if torch.cuda.is_available() else "cpu",
            local_files_only=os.getenv("HF_HUB_OFFLINE") == "1",
        )
    return _encoder


def reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        import torch

        _reranker = CrossEncoder(
            os.getenv("GIGBID_RERANKER_PATH", config()["models"]["reranker"]),
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
    return _reranker


def tokenize(text):
    import re

    return re.findall(r"[a-z0-9+#.]+", text.lower())


class EvidenceIndex:
    def __init__(self, items, tenant="evaluation"):
        self.tenant = tenant
        self.persona = items[0]["persona"] if items else ""
        self.items = items
        self.chunks = [c for item in items for c in chunks(item)]
        self.texts = [c["text"] for c in self.chunks]
        self.bm25 = BM25Okapi([tokenize(x) for x in self.texts]) if self.texts else None
        if not self.texts:
            self.vectors = np.empty((0, 0))
            self.query_cache = {}
            return
        cache_key = hashlib.sha256((config()["models"]["embeddings"] + json.dumps(self.texts)).encode()).hexdigest()
        path = RUNTIME / "embeddings" / f"{cache_key}.npy"
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            self.vectors = np.load(path)
        else:
            self.vectors = encoder().encode(
                self.texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
            )
            np.save(path, self.vectors)
        self.query_cache = {}
        if os.getenv("QDRANT_URL"):
            self._sync_qdrant(cache_key)

    def _sync_qdrant(self, key):
        from qdrant_client import models
        import uuid

        client = qdrant_client(os.environ["QDRANT_URL"])
        name = "evidence_" + hashlib.sha256(config()["models"]["embeddings"].encode()).hexdigest()[:12]
        if not client.collection_exists(name):
            client.create_collection(
                name, vectors_config=models.VectorParams(size=self.vectors.shape[1], distance=models.Distance.COSINE)
            )
        scope = models.Filter(
            must=[
                models.FieldCondition(key="tenant", match=models.MatchValue(value=self.tenant)),
                models.FieldCondition(key="persona", match=models.MatchValue(value=self.persona)),
            ]
        )
        client.delete(name, points_selector=models.FilterSelector(filter=scope))
        client.upsert(
            name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, self.tenant + ":" + c["chunk_id"])),
                    vector=v.tolist(),
                    payload=dict(c, tenant=self.tenant),
                )
                for c, v in zip(self.chunks, self.vectors)
            ],
        )
        self.qdrant = (client, name)
        self.qdrant_filter = scope

    def embed(self, query):
        if query not in self.query_cache:
            self.query_cache[query] = encoder().encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        return self.query_cache[query]

    def dense(self, query):
        if hasattr(self, "qdrant"):
            client, name = self.qdrant
            result = client.query_points(
                name,
                query=self.embed(query).tolist(),
                query_filter=self.qdrant_filter,
                limit=len(self.chunks),
                with_payload=True,
            )
            positions = {c["chunk_id"]: i for i, c in enumerate(self.chunks)}
            scores = np.full(len(self.chunks), -1.0)
            for hit in result.points:
                idx = positions.get(hit.payload.get("chunk_id"))
                if idx is not None:
                    scores[idx] = hit.score
            return scores
        return self.vectors @ self.embed(query)

    def order(self, scores):
        return np.argsort(-np.asarray(scores)).tolist()

    def unique(self, order, k, persona=None, filters=None):
        seen = set()
        results = []
        for i in order:
            item = self.chunks[i]
            if persona and item["persona"] != persona:
                continue
            if filters and any(item.get(key) != val for key, val in filters.items() if key != "persona"):
                continue
            # Proposals/reviews cannot prove a delivered project's implementation.
            if item["type"] not in ("case_study", "readme", "code", "cv"):
                continue
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            results.append(dict(item))
            if len(results) >= k:
                break
        return results


def load_corpus():
    path = ROOT / "data/processed/corpus.json"
    if not path.exists():
        raise RuntimeError("Run python -m scripts.seed_data before starting GigBid")
    return json.loads(path.read_text(encoding="utf-8"))
