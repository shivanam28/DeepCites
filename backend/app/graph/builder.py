from langgraph.graph import END, START, StateGraph

from app.graph.nodes import planner, researcher, route_after_research, verifier, writer
from app.graph.state import ResearchState


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("planner", planner)
    g.add_node("researcher", researcher)
    g.add_node("writer", writer)

    g.add_edge(START, "planner")
    g.add_edge("planner", "researcher")
    g.add_conditional_edges(
        "researcher",
        route_after_research,
        {"researcher": "researcher", "writer": "writer"},
    )
    g.add_node("verifier", verifier)
    g.add_edge("writer", "verifier")
    g.add_edge("verifier", END)
    return g.compile()