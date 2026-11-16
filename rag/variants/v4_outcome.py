from collections import defaultdict
from rag.variants.v2_hybrid import rank as hybrid


def rank(index, query, requirements):
    """Only historical corpus outcomes influence rank; dev labels are never read here."""
    outcomes = defaultdict(list)
    for item in index.items:
        if item["type"] == "proposal":
            outcomes[item["project"]].append({"won": 1, "replied": 0.6, "ignored": 0}.get(item["outcome"], 0))
    boosts = {p: sum(v) / (len(v) + 5) for p, v in outcomes.items()}
    order = hybrid(index, query, requirements)
    return sorted(
        order,
        key=lambda i: (1 / (60 + order.index(i) + 1)) * (1 + 0.25 * boosts.get(index.chunks[i]["project"], 0)),
        reverse=True,
    )
