# Food Forest — AI sourcing assistant cheat sheet

Quick reference while we build the LangGraph graph, tools, and chat layer against Search API v2 and Next.js. We can trim or expand sections as the repo evolves.

---

## 1. What we’re building (north star)

- **Today:** Member discovery (manufacturers, suppliers, network members).
- **Phase 5:** Conversational sourcing — users describe what they need; we help find members, explain results, and support actions (shortlist, outreach handoffs).
- **Later:** Sourcing workspace (projects, shortlists) and enterprise / two-sided network.

**Strategic framing:** Retrieval and chat should feel like one system in UX and data contracts, with **clear boundaries** in code and deployment so we can ship incrementally.

---

## 2. Architecture map (target shape)

| Layer | Role |
|--------|------|
| `apps/web` | Next.js App Router — chat UI, streaming (`useChat` → Route Handler → `streamText` pattern). |
| `apps/search-api` | Search API v2 — canonical retrieval boundary for tools and chat. |
| `packages/search-contracts` | Request/response types + Zod (single source of truth for tool I/O vs raw Dgraph). |
| `packages/search-core` | Entity recognition, scoring, orchestration (extract from legacy paths over time). |
| Agent / orchestration | Prefer **outside** the Next.js server long-term (e.g. dedicated agent app + LangSmith), with the web app as client — matches our Phase 5 delivery notes. |

**Rule of thumb:** Chat calls stable HTTP/contracts; we don’t embed retrieval critical path inside the UI bundle.

---

## 3. LangGraph — patterns we’ll actually use

### 3.1 One main state vs many schemas

- **`OverallState` (or internal `GraphState`):** Everything the graph needs across nodes — messages, user/session ids, last search payload, flags, etc.
- **`input_schema` / `output_schema`:** Filter what **callers** pass in and what **`invoke` returns** (e.g. input: `user_message` + `session_id`; output: `assistant_message` + `citations` only).
- **Private / intermediate TypedDicts:** Fields that **only pass between specific nodes** and must **not** land in checkpointed “public” state or final API responses (e.g. raw retrieval blobs, large context packs, internal scoring debug). *Private state is schema hygiene and I/O control — not a security boundary by itself.*

### 3.2 When to use private state (Food Forest examples)

- **Search tool pipeline:** Node A returns ranked hits + explanation draft; Node B compresses to user-facing summary — we keep full hit payloads private between them if we don’t want them in `OverallState`.
- **Entity resolution:** Intermediate “recognized entities” JSON for the next node only; graph output stays `answer` + `member_ids`.
- **Tuning / shadow:** Internal `profile_id` or v2 experiment metadata between nodes without exposing to the client.

### 3.3 Tools vs graph nodes

- **Tools:** LLM-callable, bounded operations with clear args — `search_members`, `explain_results`, `shortlist_members`, `outreach_handoff`, etc.
- **Nodes:** Orchestration, routing, persistence hooks, “always run” logic, state reducers.

**Check before adding a tool:** Is it idempotent enough? Does it need user consent? Does it map 1:1 to Search API or workspace API contracts?

### 3.4 Reducers & channels (from Module 2)

- Lists we append (e.g. messages, audit steps): use **`Annotated[list, operator.add]`** or the right reducer — don’t rely on last-write-wins by accident.
- Single-value fields: default replace semantics is usually fine.

### 3.5 Trim & filter messages (long-running chat, token budget)

Our **`messages`** channel will grow forever if we only append. For Phase 5+ threads we should **bound what we send to the model** each turn: cost, latency, and context-window limits all depend on it.

**Where in the graph:** Run trimming/filtering in a node **before** the LLM (or inside a small “prepare context” node) so checkpointed history can stay full while **model input** stays capped — or trim before writing back to state if we want the persisted thread to match what the model saw (product choice).

**`trim_messages`** (`langchain_core.messages`): shrink history to **`max_tokens`** using a **`token_counter`** (pass our chat **`BaseLanguageModel`** for exact counts, or **`"approximate"`** on the hot path when near-enough is fine). Typical chat defaults:

- **`strategy="last"`** — keep recent turns, drop old ones.
- **`start_on="human"`** — avoid invalid histories (many models expect history to start with human or system+human).
- **`include_system=True`** — keep the leading **`SystemMessage`** when we use one.

Optional: **`end_on`** / **`allow_partial`** when we need stricter shape or to clip a huge single message.

**`filter_messages`** (`langchain_core.messages`): drop noise **before** or **after** trim, depending on goal:

- **`include_types`** / **`exclude_types`** — e.g. only **`human`** + **`ai`** for a slim replay (watch tool-call validity if we strip tool messages).
- **`exclude_tool_calls`** — **`True`** or specific IDs to shed old tool **`AIMessage` / `ToolMessage`** pairs once we no longer need them in context (saves tokens when past turns are irrelevant).

**Order of operations:** Often **filter** (remove classes we never want in the prompt) **then** **`trim_messages`** (enforce token ceiling). If we filter tool traces, we should ensure the remaining sequence is still **valid** for the model (tool messages only after their tool-calling AI turn).

**Heavier option:** A **summarize** node that writes a rolling **`summary`** string (or message) into state and keeps only **summary + last N messages** — use when semantic memory of the full thread matters more than raw verbatim history.

### 3.6 Persistent memory / storage (per user, per conversation)

Academy reference: `module-2/chatbot-external-memory.ipynb` — **external checkpointer** (e.g. SQLite on disk) so graph state survives restarts; same ideas extend to Postgres in production.

**What “persistent memory” means here:** LangGraph **checkpoints** the graph’s state (messages, custom fields like **`summary`**, flags, etc.) to a **saver** backend. We **`compile(..., checkpointer=...)`** and pass a **`thread_id`** on every **`invoke` / `stream`** so each **thread** is an isolated conversation timeline.

**Per-user shape:** We treat **`config["configurable"]["thread_id"]`** as **our** conversation key — typically something we derive server-side, e.g. **`{user_id}:{conversation_id}`** or a stable UUID we issue when a chat session starts. Different **`thread_id`** ⇒ different checkpoint namespaces; same id across requests ⇒ resumed history. **`thread_id` is not auth** — we still verify the caller owns that conversation before loading or appending state.

**Local / dev:** **`SqliteSaver`** over a file path (see notebook’s `state_db/example.db` pattern) is enough to prove persistence across kernel or process restarts.

**Production entailments:**

- **Store:** Prefer **Postgres** (or another supported checkpointer) for concurrency, backups, and ops we already run for the product — SQLite is a stepping stone, not our multi-instance default.
- **Isolation:** One logical **conversation** per **`thread_id`**; enforce **tenant / user** boundaries in our API so we never mix checkpoints across accounts.
- **Retention & compliance:** Define how long we keep threads, export/delete paths (GDPR-style requests), and whether **PII** in messages belongs in the same store as analytics — aligns with **`ff_chat_context_persistence`** and policy when we turn persistence on.
- **Capacity:** Checkpoint rows grow with turns; pair persistence with **§3.5** (trim / filter / summarize) so **stored** history and **model** context stay intentional — we can store a long thread but still send only a bounded window to the LLM.
- **Migrations & upgrades:** Checkpointer libraries evolve; we plan **schema / version** upgrades and test restore paths like any app database.

**Inspecting state:** **`graph.get_state(config)`** (and related APIs) help debug “what the graph remembers” for a **`thread_id`** during development and support.

---

## 4. Search API v2 — agent-facing discipline

- **Canonical contract:** Query input schema, entity model, ranking/scoring profile, response shape for **cards + explanations + tool payloads** — define once in `search-contracts`, consume from agent and web.
- **Observability:** Attach session- and query-scoped analytics at the **search boundary** (Firestore user-sessions aligned with migration — server-mediated ingestion; tight rules until contract is final).
- **Feature flags (retrieval):** `ff_search_v2_shadow`, `ff_search_v2_internal`, `ff_search_v2_beta`, `ff_search_v2_default`, `ff_search_lab_internal`, `ff_search_explanations_v2` — agent should accept a **search mode / profile** from config or request context, not hardcode v1/v2.
- **Rollback levers:** Route switch v2→v1, API host swap, shadow-only, tuning profile rollback — our agent layer should degrade to “search page” or simplified flow when flags demand it.

---

## 5. Phase 5 chat — tool inventory (v1 targets)

| Tool (concept) | Purpose | Contract note |
|----------------|---------|----------------|
| **Member / supplier search** | Natural language → structured query → Search API | Map to Query Gap Taxonomy — when to clarify vs search. |
| **Explain results** | Why these members, scores, facets | May use `ff_search_explanations_v2` / explanation field from API. |
| **Shortlist / save** | User picks → MyPicks / user context | Auth + user id required; match existing shortlist flows. |
| **Quote / outreach handoff** | Hand off to messaging workflow | Explicit user confirmation; avoid silent sends. |

**Spike (non-blocking):** Apollo MCP — 1–2 ops for internal evaluation; product dependency comes later.

---

## 6. Conversation design — Query Gap Taxonomy

Treat the taxonomy as the **functional contract** between:

- what we **ask** vs **don’t ask**,
- what belongs in **search** vs **clarifying dialog** vs **messaging handoff**,
- how much **structured context** we persist per turn.

**When designing prompts + tools:** For each user utterance class, we should know: required tool params, optional params, and when to emit a clarifying question instead of calling search.

---

## 7. Chat feature flags & rollback

- **Flags:** `ff_chat_v1_internal`, `ff_chat_v1_beta`, `ff_chat_tool_search`, `ff_chat_tool_explain`, `ff_chat_tool_shortlist`, `ff_chat_tool_outreach_handoff`, `ff_chat_context_persistence`.
- **Rollback:** Hide chat entry; disable tools individually; fallback to classic search page; turn off persistence.
- **Implementation hint:** Read flags in the **API route / agent runner**, pass a `capabilities` object into graph state so nodes and tool bindings stay dumb and testable.

---

## 8. Pre-flight checklists

### Before we add a graph node

- [ ] Which state keys does it read/write?
- [ ] Should any writes be **private** (intermediate only)?
- [ ] Does this belong in a **tool** instead (LLM-invoked, well-scoped)?
- [ ] Reducer correct for list vs scalar fields?

### Before we add a tool

- [ ] Zod/schema in `search-contracts` or shared agent package?
- [ ] Auth — whose data, which org?
- [ ] Idempotency and error shape for the UI?
- [ ] Feature flag name and default-off in production?
- [ ] Does it respect Query Gap Taxonomy (no search with missing critical params)?

### Before we ship a chat build

- [ ] Streaming path tested (loading UI + SSE).
- [ ] Search v2 shadow/beta behavior verified under flags.
- [ ] No secrets in client state; server-only keys for Dgraph / Admin SDK paths.
- [ ] If persistence is on: **`thread_id`** is server-issued / validated; retention and delete/export story matches policy; checkpointer store sized and backed up like our other DBs.

---

## 9. Docs / anchors in our repo (when we’re back in the product repo)

- LangChain Academy — `module-2/chatbot-external-memory.ipynb` (SQLite checkpointer, `thread_id`, durable state).
- Phase 04 — Search API development (migration, tuning, sessions).
- Phase 02 step 04 — LangGraph agent package + LangSmith boundaries.
- Query Gap Taxonomy — conversation spec.
- Apollo MCP viability report — tool boundaries, not retrieval critical path.
- Food Forest Data North Star — domain boundaries; keep federation off retrieval hot path early.

---

## 10. One-line reminders

- **Retrieval contract first, chat second** — tools are thin adapters over stable APIs.
- **State schemas are product boundaries** — input/output filtering saves us from leaking internal keys to the client.
- **Private state** — for handoffs between nodes, not for hiding PII from ourselves.
- **Flags everywhere** — ship search and chat toggles independently.
- **Trim then model** — `filter_messages` + `trim_messages` (or summarize + recent window) so long sessions don’t blow token usage or context limits.
- **Checkpoint + thread_id** — durable per-conversation state via a checkpointer; **`thread_id`** is ours to map to user/session and must be authorized, not guessed.

We can paste LangGraph code snippets from the academy notebooks (reducers, `StateGraph(..., input_schema=..., output_schema=...)`, private state edges) into an appendix here when we settle on package layout.
