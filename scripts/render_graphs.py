import os
from core.settings import ROOT, RUNTIME

os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME / "matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from langgraph.checkpoint.memory import InMemorySaver


def render(name, compiled, positions, size):
    graph = compiled.get_graph()
    (ROOT / "docs/images" / f"{name}.mmd").write_text(graph.draw_mermaid())
    fig, ax = plt.subplots(figsize=size)
    fig.patch.set_facecolor("#f8faf6")
    ax.set_facecolor("#f8faf6")
    labels = {
        "__start__": "New job" if name == "bid_graph" else "Client thread",
        "__end__": "Saved outcome",
        "analyst": "Job analyst",
        "risk": "Risk assessor",
        "fit": "Fit matcher",
        "approval": "Human approval\ninterrupt",
        "verifier": "Claim verifier",
        "compliance": "Compliance\nguard",
        "preview": "Dry-run preview",
        "dispatch": "Approved\ndispatch",
        "liaison": "Client liaison",
        "send": "Approved send",
    }
    for edge in graph.edges:
        if edge.source not in positions or edge.target not in positions:
            continue
        x, y = positions[edge.source]
        tx, ty = positions[edge.target]
        if edge.target == "__end__" and edge.source not in ("dispatch", "send"):
            side = 4.4 if name == "bid_graph" else 1.7
            ax.plot(
                [x + 0.93, side, side, tx + 0.93],
                [y, y, ty, ty],
                color="#b5c3af",
                linewidth=1,
                linestyle="--",
                zorder=0,
            )
            ax.add_patch(
                FancyArrowPatch((tx + 1.2, ty), (tx + 0.9, ty), arrowstyle="-|>", mutation_scale=10, color="#a7b99e")
            )
            continue
        rad = 0
        if edge.source == "critic" and edge.target == "writer":
            rad = -0.65
        if edge.source == "approval" and edge.target == "preview":
            rad = -0.65
        if edge.target == "__end__" and edge.source not in ("dispatch", "send"):
            rad = 0.42
        patch = FancyArrowPatch(
            (x, y - 0.22),
            (tx, ty + 0.22),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.2,
            color="#9aaf9a",
            connectionstyle=f"arc3,rad={rad}",
            linestyle="--" if edge.conditional else "-",
        )
        ax.add_patch(patch)
    for node, (x, y) in positions.items():
        fill = "#fff4d6" if node == "approval" else "#ffffff"
        if node in ("__start__", "__end__"):
            fill = "#e3eddf"
        box = FancyBboxPatch(
            (x - 0.88, y - 0.25),
            1.76,
            0.5,
            boxstyle="round,pad=0.05,rounding_size=.09",
            facecolor=fill,
            edgecolor="#cbd9c5",
            linewidth=1.2,
        )
        ax.add_patch(box)
        ax.text(
            x,
            y,
            labels.get(node, node.title()),
            ha="center",
            va="center",
            fontsize=14,
            color="#294737",
            fontweight="medium",
        )
    ax.set_xlim(min(x for x, y in positions.values()) - 1.8, max(x for x, y in positions.values()) + 2.7)
    ax.set_ylim(-0.4, max(y for x, y in positions.values()) + 0.6)
    ax.axis("off")
    fig.tight_layout(pad=0.4)
    fig.savefig(ROOT / "docs/images" / f"{name}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    positions = {
        name: (0, 13 - i)
        for i, name in enumerate(
            [
                "__start__",
                "scout",
                "decision",
                "pricing",
                "writer",
                "verifier",
                "critic",
                "compliance",
                "preview",
                "approval",
                "dispatch",
                "__end__",
            ]
        )
    }
    positions.update(analyst=(-2.3, 11.8), risk=(0, 11.8), fit=(2.3, 11.8))
    # Allocate the parallel superstep between scout and decision.
    positions["__start__"] = (0, 14)
    positions["scout"] = (0, 13)
    positions["decision"] = (0, 10.5)
    for i, node in enumerate(
        ["pricing", "writer", "verifier", "critic", "compliance", "preview", "approval", "dispatch", "__end__"]
    ):
        positions[node] = (0, 9.5 - i)
    render("bid_graph", build_bid_graph(None, InMemorySaver(), {}), positions, (7, 11))
    render(
        "conversation_graph",
        build_conversation_graph(None, InMemorySaver()),
        {n: (0, 5 - i) for i, n in enumerate(["__start__", "liaison", "preview", "approval", "send", "__end__"])},
        (4, 6),
    )
    print("Rendered both compiled StateGraphs.")
