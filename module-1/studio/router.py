# This file demonstrates: "chain logic" inside nodes + graph routing between nodes.
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt

# ----- Tool definition -----
# This is a plain Python function. The model can decide to call it.
def multiply(a: int, b: int) -> int:
    """Multiplies a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

# ----- Chain setup (inside node functions) -----
# We bind tools to the LLM so one model call can either:
# 1) answer directly, or 2) emit a tool call request.
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([multiply])

# Starter state for Studio. If we press Run with empty input, we still have context.
DEFAULT_MESSAGES = [
    SystemMessage(content="You are a helpful assistant. Use tools when useful."),
    HumanMessage(content="Hi I'm Avery. Help me warm up with 7 * 9."),
]


def seed_history(state: MessagesState):
    # Graph node: initialize state once at the start.
    # If Studio already sends messages, we preserve them.
    if state.get("messages"):
        return {}
    return {"messages": DEFAULT_MESSAGES}


# Graph node: one "chain step" that calls the LLM-with-tools.
# This does not route by itself; it only returns updated state.
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


def human_followup(state: MessagesState):
    # Graph node: explicit human-in-the-loop pause.
    # Studio interrupts here and asks us for a follow-up instruction.
    _ = state["messages"]
    followup = interrupt(
        {
            "instruction": "We ran the multiply tool. Please add a follow-up request for the assistant.",
            "example": "Now create a beginner algebra equation that uses this result.",
        }
    )
    if isinstance(followup, dict):
        followup_text = str(
            followup.get("text")
            or followup.get("message")
            or followup.get("response")
            or followup
        )
    else:
        followup_text = str(followup)
    return {"messages": [HumanMessage(content=followup_text)]}


def algebra_llm(state: MessagesState):
    # Graph node: final LLM call after we provide human follow-up.
    return {"messages": [llm.invoke(state["messages"])]}


# ----- Graph wiring (nodes + edges) -----
# Nodes are computation units; edges define execution order.
builder = StateGraph(MessagesState)
builder.add_node("seed_history", seed_history)
builder.add_node("tool_calling_llm", tool_calling_llm)
# Prebuilt ToolNode executes requested tool calls found in messages.
builder.add_node("tools", ToolNode([multiply]))
builder.add_node("human_followup", human_followup)
builder.add_node("algebra_llm", algebra_llm)

# Normal edges: always go to the next node.
builder.add_edge(START, "seed_history")
builder.add_edge("seed_history", "tool_calling_llm")

# Conditional edge: tools_condition inspects the latest assistant message.
# - If assistant requested a tool -> route to "tools"
# - If no tool request -> route to END
builder.add_conditional_edges(
    "tool_calling_llm",
    tools_condition,
)

# After tool execution, we pause for human input, then do a final LLM step.
builder.add_edge("tools", "human_followup")
builder.add_edge("human_followup", "algebra_llm")
builder.add_edge("algebra_llm", END)

# Compile turns builder config into an executable graph object.
graph = builder.compile()