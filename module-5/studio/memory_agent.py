import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from trustcall import create_extractor

from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs
from langchain_core.messages import SystemMessage

from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

import configuration

# Initialize the model
model = ChatOpenAI(model="gpt-4o", temperature=0)

# Schema for binary decision to save memories
class SaveMemory(BaseModel):
    """ Profile of a user """
    store_memories: bool = Field(description="Decision to save memories based on the conversation with the user.")

# Memory schema 
class Task(BaseModel):
    task: str = Field(description="The task to be completed.")
    time_to_complete: int = Field(description="Estimated time to complete the task (minutes).")
    deadline: Optional[datetime] = Field(
        description="When the task needs to be completed by (if applicable)",
        default=None
    )
    solutions: list[str] = Field(
        description="List of specific, actionable solutions (e.g., specific locations, service providers, or concrete options relevant to completing the task)",
        min_items=1
    )

# Create the Trustcall extractor
trustcall_extractor = create_extractor(
    model,
    tools=[Task],
    tool_choice="Task",
    # This allows the extractor to insert new memories
    enable_inserts=True,
)

# Chatbot instruction
MODEL_SYSTEM_MESSAGE = """You are a helpful chatbot. You are designed to be a companion to a user.

The user is Lance, located in San Francisco, with a 1 year old. 

You have a long term memory which keeps track of specific tasks for the user over time.

Current Memory (may include updated memories from this conversation): 

{memory}"""

# Trustcall instruction
TRUSTCALL_INSTRUCTION = """Reflect on following interaction. 

Use the provided tools to retain any necessary tasks for the user. 

Use parallel tool calling to handle updates and insertions simultaneously:"""

# Router system message
ROUTER_SYSTEM_MESSAGE = """You are deciding whether to update the task collection for the user.

Here is the current task collection (it may be empty): <memories>{info}</memories>

Here is the chat history. Assess whether the chat history contains any information that should be added to the task collection."""

# Node definitions
def call_model(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Load memories from the store and use them to personalize the chatbot's response."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)

    # Retrieve memory from the store
    namespace = ("memories", configurable.user_id)
    memories = store.search(namespace)

    # Format any tasks for the system prompt
    info = "\n".join(f"- Task: {mem.value['task']}\n  Time: {mem.value['time_to_complete']} minutes\n  Solutions: {', '.join(mem.value['solutions'])}"
                    + (f"\n  Deadline: {mem.value['deadline']}" if mem.value['deadline'] else "")
                    for mem in memories)
    system_msg = MODEL_SYSTEM_MESSAGE.format(memory=info)

    # Respond using memory as well as the chat history
    response = model.invoke([SystemMessage(content=system_msg)]+state["messages"])

    return {"messages": [response]}

def write_memory(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)

    # Define the namespace for the memories
    namespace = ("memories", configurable.user_id)

    # Retrieve the most recent memories for context
    existing_items = store.search(namespace)

    # Format the existing memories for the Trustcall extractor
    tool_name = "Memory"
    existing_memories = ([(existing_item.key, tool_name, existing_item.value)
                          for existing_item in existing_items]
                          if existing_items
                          else None
                        )

    # Merge the chat history and the instruction
    updated_messages=list(merge_message_runs(messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION)] + state["messages"]))

    # Invoke the extractor
    result = trustcall_extractor.invoke({"messages": updated_messages, 
                                         "existing": existing_memories})

    # Save save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )

# Conditional edge
def route_message(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflect on the memories and chat history to decide whether to update the memory collection."""

    # Get the user ID from the config# Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)

    # Retrieve memory from the store
    namespace = ("memories", configurable.user_id)
    memories = store.search(namespace)

    # Format the memories for the system prompt
    info = "\n".join(f"[{mem.key}]: {mem.value}" for mem in memories)

    # Consider whether to save memories
    model_with_structure = model.with_structured_output(SaveMemory)

    # Format the system message
    system_msg = ROUTER_SYSTEM_MESSAGE.format(info=info)
    
    # Invoke the router
    store_memories_flag = model_with_structure.invoke([SystemMessage(content=system_msg)]+state["messages"])

    # Check if model has chosen to store memories
    if store_memories_flag.store_memories:
        return "write_memory"
    
    # Otherwise call model 
    return "call_model"

# Create the graph + all nodes
builder = StateGraph(MessagesState,config_schema=configuration.Configuration)

# Define the flow of the memory extraction process
builder.add_node(call_model)
builder.add_node(write_memory)
builder.add_conditional_edges("__start__", route_message, ["write_memory", "call_model"])
builder.add_edge("write_memory", "call_model")
builder.add_edge("call_model", END)

# Compile the graph
graph = builder.compile()
