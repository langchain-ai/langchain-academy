import uuid
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore

from configuration import ChatbotConfigurable

# Initialize the LLM
model = ChatOpenAI(model="gpt-4o", temperature=0) 

def call_model(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """If the user says the keyword "remember", save a memory to the store.
    Load any existing memory from the store and use it to personalize the chatbot's response."""
    
    # Get the user ID from the config
    user_id = config["configurable"]["user_id"]

    # Retrieve any existing memory from the store
    namespace = ("memory", user_id)
    existing_memory = store.get(namespace, "user_memory")

    # Format the existing memory for the system prompt
    system_msg = f"""You are a helpful assistant. Here is the memory for the user. 
    Use this to personalize responses: {existing_memory.value if existing_memory else None}"""

    # Respond using existing memory as well as the chat history
    response = model.invoke([SystemMessage(content=system_msg)]+state["messages"])

    # Now, consider if we want to update memory  
    # Check if the last message contains the keyword "remember"
    last_message = state["messages"][-1]
    if "remember" in last_message.content.lower():
        
        # If the user instructs us to "remember", distill the chat history into a memory  
        system_msg = f"Create a simple user profile based on the user's message history to save for long-term memory."
        user_msg = f"User messages: {state['messages']}"
        new_memory = model.invoke([SystemMessage(content=system_msg)]+[HumanMessage(content=user_msg)])

        # Overwrite the memory to the store as a string 
        key = "user_memory"
        store.put(namespace, key, {"user_profile": new_memory.content})

    return {"messages": response}

# Define the graph
builder = StateGraph(MessagesState, ChatbotConfigurable)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)
graph = builder.compile()