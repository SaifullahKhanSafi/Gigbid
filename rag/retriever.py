from functools import lru_cache
from importlib import import_module
from rag.index.engine import EvidenceIndex, load_corpus
from core import db
from core.settings import config

VARIANTS = {
    "V0": "v0_naive",
    "V1": "v1_decomposed",
    "V2": "v2_hybrid",
    "V3": "v3_reranked",
    "V4": "v4_outcome",
    "V8": "v8_corrective",
}


@lru_cache(maxsize=16)
def _index(tenant, persona, revision):
    items = [x for x in load_corpus() if x["persona"] == persona]
    items.extend(x for x in db.scan(tenant, "evidence") if x["persona"] == persona)
    deleted = {x["id"] for x in db.scan(tenant, "deleted_evidence")}
    items = [x for x in items if x["id"] not in deleted]
    return EvidenceIndex(items, tenant=tenant)


def retrieve(query, persona, k=5, variant=None, requirements=None, tenant="evaluation", filters=None):
    version = db.get(tenant, "settings", "index_revision") or {"value": 0}
    index = _index(tenant, persona, version["value"])
    if not index.chunks:
        return []
    module = import_module("rag.variants." + VARIANTS[variant or config()["rag"]["variant"]])
    order = module.rank(index, query, requirements or [])
    return index.unique(order, k, persona, filters)


def reindex(tenant):
    version = db.get(tenant, "settings", "index_revision") or {"value": 0}
    db.put(tenant, "settings", "index_revision", {"value": version["value"] + 1})
    _index.cache_clear()
