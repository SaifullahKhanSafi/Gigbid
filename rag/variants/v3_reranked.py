from rag.variants.v2_hybrid import rank as hybrid
from rag.index.engine import reranker


def rank(index, query, requirements):
    candidates = hybrid(index, query, requirements)[:40]
    scores = reranker().predict(
        [(query, index.chunks[i]["text"]) for i in candidates], batch_size=32, show_progress_bar=False
    )
    ranked = [i for _, i in sorted(zip(scores, candidates), reverse=True)]
    return ranked + [i for i in range(len(index.chunks)) if i not in set(candidates)]
