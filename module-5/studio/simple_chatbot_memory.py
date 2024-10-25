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
    
    # Get the user ID from the config
    user_id = config["configurable"]["user_id"]

    # Define the namespace for the memories
    namespace = ("memories", user_id)

    # Retrieve the most recent memories for context
    memories = store.search(namespace)

    # Get the last message from the user 
    last_message = state["messages"][-1]

    # Check if it contains the keyword "remember"
    if "remember" in last_message.content.lower():
        
        # Distill chat message as a memory 
        system_msg = f"Create a simple user profile based on the user's message history to save for long-term memory."
        user_msg = f"User message: {last_message.content}"
        memory = model.invoke([SystemMessage(content=system_msg)]+[HumanMessage(content=user_msg)])

        # Save the memory to the store
        store.put(namespace, str(uuid.uuid4()), {"data": memory.content})

    # Format all memories for the system prompt
    user_memories = "\n".join([d.value["data"] for d in memories])
    system_msg = f"You are a helpful assistant. Here is relevant information about the user: {user_memories}"
    
    # Invoke the model with the system prompt that contains the memories as well as the user's messages
    response = model.invoke([SystemMessage(content=system_msg)]+state["messages"])
    return {"messages": response}

# Define the graph
builder = StateGraph(MessagesState, ChatbotConfigurable)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)
graph = builder.compile()