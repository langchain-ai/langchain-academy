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

---

## 9. Docs / anchors in our repo (when we’re back in the product repo)

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

We can paste LangGraph code snippets from the academy notebooks (reducers, `StateGraph(..., input_schema=..., output_schema=...)`, private state edges) into an appendix here when we settle on package layout.
