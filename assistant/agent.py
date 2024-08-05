from typing import Annotated, List
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.graph import START, END, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode

from langchain_openai import ChatOpenAI

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
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b

tools = [add, multiply, divide]


# State
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Assistant
class Assistant:
    def __init__(self, runnable: Runnable):
        """
        Initialize the Assistant with a runnable object.
        """
        self.runnable = runnable

    def __call__(self, state: MessagesState, config: RunnableConfig):
        """
        Call method to invoke
        """
        result = self.runnable.invoke(state)  
        return {"messages": result}

# Assistant prompt
primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            " You are a helpful assistant tasked with writing performing arithmatic on a set of inputs. "
         ),
        ("placeholder", "{messages}"),
    ]
)

# Prompt our LLM and bind tools
llm = ChatOpenAI(model="gpt-4o")
assistant_runnable = primary_assistant_prompt | llm.bind_tools(tools)

# Graph
builder = StateGraph(MessagesState)

# Define nodes: these do the work
builder.add_node("assistant", Assistant(assistant_runnable))
builder.add_node("tools", ToolNode(tools))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")
# graph = builder.compile()

# Add a breakpoint 
graph = builder.compile(interrupt_before=["tools"])

