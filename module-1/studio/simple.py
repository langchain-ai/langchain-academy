import random
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    graph_state: str


def decide_mood(state: State) -> Literal["node_2", "node_3", "node_4", "node_5"]:
    # Randomly choose one feeling node each run.
    _ = state["graph_state"]
    return random.choice(["node_2", "node_3", "node_4", "node_5"])


def node_1(state: State) -> State:
    print("---Node 1---")
    return {"graph_state": state["graph_state"] + " I am"}


def node_2(state: State) -> State:
    print("---Node 2---")
    return {"graph_state": state["graph_state"] + " happy!"}


def node_3(state: State) -> State:
    print("---Node 3---")
    return {"graph_state": state["graph_state"] + " sad!"}


def node_4(state: State) -> State:
    print("---Node 4---")
    return {"graph_state": state["graph_state"] + " angry!"}


def node_5(state: State) -> State:
    print("---Node 5---")
    return {"graph_state": state["graph_state"] + " confused!"}

def node_6(state: State) -> State:
    print("---Node 6---")
    return {"graph_state": state["graph_state"] + " But it is okay!!!!!"}

builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_node("node_4", node_4)
builder.add_node("node_5", node_5)
builder.add_node("node_6", node_6)
# Routing:
# START -> node_1 -> random feeling node (node_2/node_3/node_4/node_5)
builder.add_edge(START, "node_1")
builder.add_conditional_edges("node_1", decide_mood)
builder.add_edge("node_2", "node_6")
builder.add_edge("node_3", "node_6")
builder.add_edge("node_2", "node_6")
builder.add_edge("node_4", "node_6")
builder.add_edge("node_5", "node_6")
builder.add_edge("node_6", END)

graph = builder.compile()