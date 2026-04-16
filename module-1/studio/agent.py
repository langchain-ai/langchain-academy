# This graph mirrors the "agent loop" pattern from module-1/agent.ipynb:
# assistant -> (optional tool call) -> tools -> assistant ... until no tool is needed.
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from langgraph.graph import START, StateGraph, MessagesState
from langgraph.prebuilt import tools_condition, ToolNode

# ----- Tool functions -----
# These are regular Python callables. The model may choose to call them.
def add(a: int, b: int) -> int:
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a + b

def multiply(a: int, b: int) -> int:
    """Multiplies a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

def divide(a: int, b: int) -> float:
    """Divide a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b

tools = [add, multiply, divide]

# ----- Chain setup (inside node execution) -----
# Binding tools lets a single model call either:
# 1) answer directly in natural language, or
# 2) return a structured tool call.
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)

# System message is prepended on each assistant turn.
sys_msg = SystemMessage(
    content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
)

# ----- Graph node: assistant -----
# A node contains "chain logic" for one step:
# we invoke the LLM and return state updates (messages).
def assistant(state: MessagesState):
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# ----- Graph wiring (nodes + edges) -----
# Nodes are compute units. Edges define how control moves between them.
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
# ToolNode executes tool calls emitted by the assistant message.
builder.add_node("tools", ToolNode(tools))

# Normal edge: graph always starts at assistant.
builder.add_edge(START, "assistant")

# Conditional edge: tools_condition inspects assistant output:
# - If output contains a tool call -> route to "tools"
# - Otherwise -> route to END
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)

# Tool loop edge: after tool execution, we return to assistant,
# so we can incorporate tool results and decide the next action.
builder.add_edge("tools", "assistant")

# Compile turns the builder config into an executable graph object.
graph = builder.compile()
