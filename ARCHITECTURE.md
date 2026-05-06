# Architectural Map
> Last synced: 2026-05-06 | Version: 1.4.0 | Mode: Logic-Only (437k tokens, 587 files)

## Monorepo Overview
NanoGemClaw is a **pnpm monorepo** (Node.js v20+, TypeScript) that runs an agentic AI assistant powered by Google Gemini. It exposes a Telegram Bot interface, a React dashboard, and an isolated container execution environment.

**Workspaces:** `packages/*`, `app/`

---

## Package Layer (`packages/`)

| Package | Role |
|---|---|
| `@nanogemclaw/core` | Shared types, logger, config schema, Zod validators |
| `@nanogemclaw/db` | SQLite via `better-sqlite3` — messages, tasks, stats, preferences |
| `@nanogemclaw/gemini` | Gemini API client, context caching, tool dispatch |
| `@nanogemclaw/telegram` | grammY bot adapter, rate limiter, message consolidator |
| `@nanogemclaw/event-bus` | Typed in-process event bus for decoupled component comms |
| `@nanogemclaw/plugin-api` | Public stable interface for external plugins (zero runtime deps) |
| `@nanogemclaw/dashboard` | React + Vite + Tailwind frontend — the web UI |

---

## Application Layer (`src/`)

### Entry & Orchestration
- **`index.ts`** — Bootstraps DB, plugins, Telegram bot, scheduler, Express server, and MCP bridge.
- **`state.ts`** — Singleton runtime state shared across modules.

### Message Routing
- **`message-handler.ts`** — Decision engine: routes to Fast Path or Container Mode.
- **`fast-path.ts`** — Direct Gemini streaming for text/native tool queries (low latency).
- **`container-runner.ts`** — Spawns isolated Docker container for complex tasks (code exec, browser).
- **`ipc-watcher.ts`** — Monitors IPC pipe from container for tool call results.

### IPC Handlers (`src/ipc-handlers/`)
Handles tool calls emitted from the container agent back to the host:
`send-document`, `generate-image`, `schedule-task`, `cancel-task`, `pause-task`, `resume-task`, `register-group`, `set-preference`, `suggest-actions`

### Skills & Knowledge
- **`skills.ts`** — Loads and serves container skill configs.
- **`knowledge.ts`** — Hybrid semantic/keyword search over user knowledge base.
- **`embeddings.ts`** — Embedding generation for knowledge RAG.
- **`query-rewriter.ts`** — Query rewriting for improved retrieval.

### Memory & Personas
- **`memory-compounder.ts`** / **`memory-summarizer.ts`** — Long-term memory lifecycle.
- **`temporal-memory.ts`** / **`fact-extractor.ts`** — Structured fact extraction.
- **`personas.ts`** / **`persona-templates.ts`** — Multi-persona management.

### Scheduling
- **`task-scheduler.ts`** — Cron-based task scheduling with persistence.
- **`compounder-scheduler.ts`** — Runs periodic memory compounding jobs.
- **`natural-schedule.ts`** — NLP-to-cron conversion.

### Infrastructure
- **`server.ts`** — Express + Socket.IO API server for the Dashboard.
- **`auth.ts`** / **`admin-auth.ts`** — Auth middleware and admin access control.
- **`gemini-tools.ts`** — Gemini function declarations registry.
- **`gemini-client.ts`** — Low-level Gemini API wrapper.
- **`zod-tools.ts`** — Zod-based tool schema builder.
- **`logger.ts`** — Structured logging.

---

## App Layer (`app/`)
- **`plugin-discovery.ts`** / **`plugin-loader.ts`** — Discovers and loads external plugins at runtime.
- **`mcp/mcp-bridge.ts`** — Model Context Protocol (MCP) bridge for external tool servers.
- **`mcp/mcp-config.ts`** — MCP server configuration management.

---

## Container Layer (`container/`)
- **`Dockerfile`** — Isolated agent container image.
- **`agent-runner/`** — Lightweight Node.js process that runs inside the container, calls Gemini, and pipes IPC tool results back to the host.
- **`skills/`** — Bundled skills (`git-to-report`, `long-memory`) loaded into agent context.

---

## Plugins (`plugins/`)
Hot-loadable plugins that extend agent capabilities via `@nanogemclaw/plugin-api`:

| Plugin | Role |
|---|---|
| `google-auth` | OAuth2 flow + token refresh |
| `google-calendar-rw` | Calendar read/write |
| `google-drive` | Drive file access |
| `google-tasks` | Tasks sync |
| `discord-reporter` | Discord embed reporting |
| `drive-knowledge-rag` | RAG over Google Drive docs |
| `memorization-service` | Persistent memorization pipeline |
| `proactive-engine` | Proactive nudge generation |
| `group-profiler` | Group-level user profiling |

---

## Data Flow

```
Telegram User
    │
    ▼
@nanogemclaw/telegram  ← rate-limiter, consolidator
    │
    ▼
src/message-handler.ts
    ├─── Fast Path ──────► @nanogemclaw/gemini ──► Telegram Response
    │
    └─── Container Mode ─► container-runner.ts
                               │
                               ▼
                         Docker (agent-runner)
                               │  IPC pipe
                               ▼
                         ipc-watcher.ts → ipc-handlers/*
                               │
                               ▼
                         Telegram Response / Side Effects
```

**Real-time Dashboard:** Events flow via `@nanogemclaw/event-bus` → `src/server.ts` (Socket.IO) → React Dashboard.

---

## Persistence Layers

| Layer | Location | Contents |
|---|---|---|
| SQLite | `store/*.db` | Messages, Tasks, Stats, Tool calls, Temporal memory |
| JSON | `data/*.json` | Groups, Personas, Skills |
| Filesystem | `groups/<chat_id>/` | Conversation logs, Workspace files |

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Runtime | Node.js 20+, TypeScript 5, tsx |
| AI | `@google/genai` (Gemini 2.x) |
| Bot | grammY |
| DB | better-sqlite3 |
| API | Express 5, Socket.IO, Zod |
| Dashboard | React 18, Vite, Tailwind CSS |
| MCP | `@modelcontextprotocol/sdk` |
| Test | Vitest, Playwright (e2e) |
| Package manager | pnpm (workspaces) |

---

## Quality Gate Results (context-sync 2026-05-06)
- **JSON Audit**: 182 files checked. 1 flagged: `packages/dashboard/tsconfig.json` — uses JSONC comments (`/* ... */`), valid for TypeScript tooling, not a defect.
- **Git status**: Clean working tree (merge in progress on `feat/git-to-report-skill`).

---
*For detailed documentation, see [docs-site/reference/architecture.md](file:///Volumes/DevDisk/NanoGemClaw/docs-site/reference/architecture.md)*
