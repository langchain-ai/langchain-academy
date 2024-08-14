from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# State
class State(TypedDict):
    input: str

# Nodes
def node_1(state):
    print("---Node 1---")
    return {"input":state['input'] +" my"}


def node_2(state):
    print("---Node 2---")
    return {"input":state['input'] +" first"}


def node_3(state):
    print("---Node 3---")
    return {"input":state['input'] +" graph"}

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

# Add
graph = builder.compile()