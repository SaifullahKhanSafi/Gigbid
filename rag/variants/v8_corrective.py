from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from rag.variants.v3_reranked import rank as rerank
from rag.variants.v2_hybrid import rank as hybrid
from core.settings import config


class RetrievalState(TypedDict, total=False):
    query: str
    requirements: list[str]
    order: list[int]
    weak: bool
    attempts: int


def rank(index, query, requirements):
    threshold = config()["rag"]["corrective_threshold"]

    def retrieve(s):
        return {"order": rerank(index, s["query"], s["requirements"]), "attempts": s.get("attempts", 0) + 1}

    def grade(s):
        top = s["order"][:5]
        similarities = index.dense(s["query"])
        return {"weak": not top or max(float(similarities[i]) for i in top) < threshold}

    def correct(s):
        # Query expansion uses observed requirements only, never imaginary experience.
        return {"order": hybrid(index, " ".join(s["requirements"]), s["requirements"]), "attempts": s["attempts"] + 1}

    graph = StateGraph(RetrievalState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade", grade)
    graph.add_node("correct", correct)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges("grade", lambda s: "correct" if s["weak"] else END)
    graph.add_edge("correct", END)
    state = graph.compile().invoke({"query": query, "requirements": requirements, "attempts": 0})
    # Final abstention prevents a weak match from becoming evidence.
    return [i for i in state["order"] if float(index.dense(query)[i]) >= threshold]
