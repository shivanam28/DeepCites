from app.graph.builder import build_graph

graph = build_graph()
result = graph.invoke({"question": "Is intermittent fasting effective?"})

print("TRACE:", result["trace"])
print("SOURCES:", len(result.get("evidence", [])))
print("VALID CLAIMS:", len(result.get("claims", [])))
print("CITATION PROBLEMS:", result.get("citation_problems"))
print()
print(result["answer"])