# This file demonstrates: "chain logic" inside nodes + graph routing between nodes.
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
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


def route_after_tool_llm(state: MessagesState):
    # After the LLM step: mirror tool-call routing, but only pause for human follow-up
    # once the assistant has incorporated tool output (so we never interrupt before
    # the natural-language answer).
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    if len(state["messages"]) >= 2 and isinstance(state["messages"][-2], ToolMessage):
        return "human_followup"
    return END


# ----- Graph wiring (nodes + edges) -----
# Nodes are computation units; edges define execution order.
# add_node("name", function): the first string is the node id in the graph; the second is the Python callable.
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

# Conditional edge: if the assistant requested tools, run them; if the assistant
# just answered after tool output, pause for human follow-up; otherwise end.
builder.add_conditional_edges(
    "tool_calling_llm",
    route_after_tool_llm,
    {"tools": "tools", "human_followup": "human_followup", END: END},
)

# After tool execution, we run the LLM again so it can answer the user before
# we interrupt for human follow-up.
builder.add_edge("tools", "tool_calling_llm")
builder.add_edge("human_followup", "algebra_llm")
builder.add_edge("algebra_llm", END)

# Compile turns builder config into an executable graph object.
graph = builder.compile()

# -----------------------------------------------------------------------------
# Novice walkthrough: what happens when this graph runs?
# -----------------------------------------------------------------------------
#
# Big picture: we have five nodes (steps). Arrows between them say what runs next.
# State is mainly the chat history (`messages`); each node can append to it.
#
# 1) START -> seed_history
#    If there are no messages yet, we inject a default opening conversation for Studio.
#    If the user/thread already has messages, we leave state alone.
#
# 2) seed_history -> tool_calling_llm
#    We call the model with tools bound (`llm_with_tools`). The model either replies in
#    plain text or asks to run `multiply` (a tool call on the latest assistant message).
#
# 3) tool_calling_llm -> route_after_tool_llm (conditional — three outcomes)
#    - "tools": the last assistant message includes tool_calls -> run the ToolNode, which
#      executes our Python `multiply` function and appends a ToolMessage (e.g. "800").
#    - "human_followup": the last assistant message does NOT request tools, but the
#      message right before it IS a ToolMessage -> we already answered using tool output,
#      so we pause for human-in-the-loop (interrupt in Studio) before continuing.
#    - END: otherwise the turn is done (e.g. a normal chat reply with no recent tool).
#
# 4) tools -> tool_calling_llm (loop)
#    After a tool runs, we call the model again so it can read the tool result and answer
#    the user in natural language. If it asks for another tool, we go back to `tools`
#    again; that's the "agent loop" inside a single graph run.
#
# 5) human_followup -> algebra_llm -> END
#    After you resume from interrupt, your text becomes a HumanMessage. `algebra_llm`
#    calls the plain `llm` (no tools) once for that follow-up, then the graph stops.
#
# Tools vs nodes: `multiply` is the only tool (model-invokable via bind_tools + ToolNode).
# `algebra_llm` is just another node — a single non-tool chat completion — not a tool.
# -----------------------------------------------------------------------------