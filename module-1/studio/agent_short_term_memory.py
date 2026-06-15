from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


def add(a: int, b: int) -> int:
    """Adds a and b."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiplies a and b."""
    return a * b


def divide(a: int, b: int) -> float:
    """Divides a by b."""
    return a / b


tools = [add, multiply, divide]

# We keep the same arithmetic agent behavior, but add persistence.
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)

sys_msg = SystemMessage(
    content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
)


def assistant(state: MessagesState):
    # Inside this node, we run chain logic (one model invocation).
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_edge("tools", "assistant")

# Short-term memory demo: we persist state checkpoints per thread_id.
# Note: when we run through the hosted LangGraph API, thread-level persistence is
# already handled for us, so this explicit MemorySaver is usually unnecessary.
# We keep it here as a local-learning example of how checkpointing works.
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
