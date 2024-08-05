from langchain_openai import ChatOpenAI

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AnyMessage

from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from typing import Annotated

# This will be a tool
def multiply(a: int, b: int) -> int:
    """Multiplies a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

# LLM with bound tool
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([multiply])

# State
class MessagesState(MessagesState):
    messages: Annotated[list[AnyMessage], add_messages]

# Node
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build grapph
builder = StateGraph(MessagesState)
builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_node("tools", ToolNode([multiply]))
builder.add_edge(START, "tool_calling_llm")
builder.add_edge("tool_calling_llm", "tools")
builder.add_edge("tools", END)
graph = builder.compile()