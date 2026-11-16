import numpy as np
from rag.index.engine import tokenize


def rank(index, query, requirements):
    scores = np.zeros(len(index.chunks))
    for requirement in requirements or [query]:
        orders = [index.order(index.dense(requirement)), index.order(index.bm25.get_scores(tokenize(requirement)))]
        for order in orders:
            for position, idx in enumerate(order):
                scores[idx] += 1 / (60 + position + 1)
    return index.order(scores)
