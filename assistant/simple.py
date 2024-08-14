import random 
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

# State
class State(TypedDict):
    input: str

# Conditional edge
def decide_mood(state) -> Literal["node_2", "node_3"]:
    
    # Often, we will use state to decide on the next node to visit
    user_input = state['input'] 
    
    # Here, let's just do a 50 / 50 split between nodes 2, 3
    if random.random() < 0.5:

        # 50% of the time, we return Node 2
        return "node_2"
    
    # 50% of the time, we return Node 3
    return "node_3"

# Nodes
def node_1(state):
    print("---Node 1---")
    return {"input":state['input'] +" I am"}


def node_2(state):
    print("---Node 2---")
    return {"input":state['input'] +" happy!"}


def node_3(state):
    print("---Node 3---")
    return {"input":state['input'] +" sad!"}

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)
builder.add_edge(START, "node_1")
builder.add_conditional_edges("node_1", decide_mood)
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()