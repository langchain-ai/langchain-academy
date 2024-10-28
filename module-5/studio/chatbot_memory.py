import uuid
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
import configuration

# Initialize the LLM
model = ChatOpenAI(model="gpt-4o", temperature=0) 

def call_model(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Load memory from the store and use it to personalize the chatbot's response."""
    
    # Get configuration
    configurable = configuration.Configuration.from_runnable_config(config)

    # Get the user ID from the config
    user_id = configurable.user_id

    # Retrieve memory from the store
    namespace = ("memory", user_id)
    existing_memory = store.get(namespace, "user_memory")

    # Format the memory in the system prompt
    system_msg = f"""You are a helpful assistant with memory that provides information about the user. 
    If you have memory for this user, use it to personalize your responses.
    Here is the memory (it may be empty): {existing_memory.value if existing_memory else None}"""

    # Respond using memory as well as the chat history
    response = model.invoke([SystemMessage(content=system_msg)]+state["messages"])

    return {"messages": response}

def write_memory(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and save a memory to the store."""
    
    # Get configuration
    configurable = configuration.Configuration.from_runnable_config(config)

    # Get the user ID from the config
    user_id = configurable.user_id

    # Retrieve existing memory from the store
    namespace = ("memory", user_id)
    existing_memory = store.get(namespace, "user_memory")
        
    # Create new memory from the chat history and existing memory
    system_msg = f"""Create or update a user profile memory based on the user's chat history. 
    This will be saved for long-term memory. If there is an existing memory, simply update it. 
    Here is the existing memory (it may be empty): {existing_memory.value if existing_memory else None}"""
    user_msg = f"Chat history: {state['messages']}"
    new_memory = model.invoke([SystemMessage(content=system_msg)]+[HumanMessage(content=user_msg)])

    # Overwrite the existing use profile memory in the store as a string 
    key = "user_memory"
    store.put(namespace, key, {"user_profile": new_memory.content})

# Define the graph
# TODO(review with Will): Default user ID is not getting passed through. 
builder = StateGraph(MessagesState,config_schema=configuration.Configuration)
builder.add_node("call_model", call_model)
builder.add_node("write_memory", write_memory)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", "write_memory")
builder.add_edge("write_memory", END)
graph = builder.compile()