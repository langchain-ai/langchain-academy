from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore


def _get_user_id(config: RunnableConfig) -> str:
    configurable = (config or {}).get("configurable", {})
    return str(configurable.get("user_id", "default-user"))


MODEL_SYSTEM_MESSAGE = """You are a helpful assistant for arithmetic.
We personalize responses with the user's long-term profile when available.

Long-term profile:
{memory}
"""

UPDATE_MEMORY_PROMPT = """We are updating long-term memory for this user.
Keep only stable user facts explicitly stated in the conversation.
Return 3-6 bullet points max.

Current stored memory:
{memory}
"""

llm = ChatOpenAI(model="gpt-4o", temperature=0)


def call_model(state: MessagesState, config: RunnableConfig, store: BaseStore):
    # We read cross-thread memory keyed by user_id.
    user_id = _get_user_id(config)
    namespace = ("memory", user_id)
    memory_item = store.get(namespace, "user_profile")
    memory_text = (
        memory_item.value.get("memory", "No memory stored yet.")
        if memory_item
        else "No memory stored yet."
    )

    system = SystemMessage(content=MODEL_SYSTEM_MESSAGE.format(memory=memory_text))
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


def write_memory(state: MessagesState, config: RunnableConfig, store: BaseStore):
    # We summarize durable user facts and store them for future sessions.
    user_id = _get_user_id(config)
    namespace = ("memory", user_id)
    existing = store.get(namespace, "user_profile")
    existing_text = (
        existing.value.get("memory", "No memory stored yet.")
        if existing
        else "No memory stored yet."
    )

    updater_prompt = SystemMessage(
        content=UPDATE_MEMORY_PROMPT.format(memory=existing_text)
    )
    # We only use human turns to avoid model-generated self-referential memory.
    human_turns = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not human_turns:
        return {}

    updated = llm.invoke([updater_prompt] + human_turns)
    store.put(namespace, "user_profile", {"memory": str(updated.content)})
    return {}


builder = StateGraph(MessagesState)
builder.add_node("call_model", call_model)
builder.add_node("write_memory", write_memory)

builder.add_edge(START, "call_model")
builder.add_edge("call_model", "write_memory")
builder.add_edge("write_memory", END)

# Long-term memory pattern:
# - checkpointer keeps short-term thread state
# - store keeps cross-thread user memory
within_thread_memory = MemorySaver()
across_thread_memory = InMemoryStore()
graph = builder.compile(
    checkpointer=within_thread_memory,
    store=across_thread_memory,
)
