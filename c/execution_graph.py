# execution_graph.py
"""
Lightweight directed-graph that records the sequence of steps
an agent takes while answering a question.

Used by agent.py:
    graph = ExecutionGraph()
    graph.add_node("plan", {"prompt": ...})
    graph.add_node("tool", {"name": "run_command", ...})
    graph.add_edge("plan", "tool")
    snapshot = graph.snapshot()   # serializable dict, stored in memory
"""


class ExecutionGraph:
    def __init__(self):
        self.nodes = []
        self.edges = []

    def add_node(self, node_id, data):
        """Add a node to the execution graph"""
        self.nodes.append({"id": node_id, "data": data})

    def add_edge(self, src, dst):
        """Add an edge between two nodes"""
        self.edges.append({"from": src, "to": dst})

    def snapshot(self):
        """Return a serializable snapshot of the graph"""
        return {"nodes": self.nodes, "edges": self.edges}
