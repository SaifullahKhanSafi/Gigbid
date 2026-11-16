import numpy as np


def rank(index, query, requirements):
    scores = np.zeros(len(index.chunks))
    for requirement in requirements or [query]:
        for position, idx in enumerate(index.order(index.dense(requirement))):
            scores[idx] += 1 / (60 + position + 1)
    return index.order(scores)
