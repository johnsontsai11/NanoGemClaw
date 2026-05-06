# Architectural Map

## Monorepo Overview
NanoGemClaw is a Node.js monorepo built on npm workspaces (PNPM). It manages an agentic AI assistant with multiple persistence layers and a plugin system.

### Core Component Relationships
- **@nanogemclaw/core**: Shared foundation (types, logger, config). Imported by all.
- **@nanogemclaw/db**: SQLite persistence layer (messages, tasks, stats).
- **@nanogemclaw/gemini**: AI client layer with Context Caching and Tool dispatch.
- **@nanogemclaw/telegram**: Telegram Bot adapter with rate limiting and message consolidation.
- **@nanogemclaw/server**: Express + Socket.IO dashboard API (dependency inversion via application layer).
- **@nanogemclaw/plugin-api**: Stable interface for external plugins (zero runtime deps).

## Application Layer (src/)
- **index.ts**: Orchestrates database, plugins, bot, scheduler, and server.
- **message-handler.ts**: Decision engine for routing messages (Fast Path vs Container Mode).
- **fast-path.ts**: High-performance Gemini streaming for text-only/native tool queries.
- **container-runner.ts**: Isolated agent execution for complex tasks (code execution, browser automation).

## Data Flow
1. **Input**: Telegram User -> Bot API -> `@nanogemclaw/telegram` (Rate Limiting/Consolidation).
2. **Routing**: `message-handler.ts` decides:
   - **Fast Path**: Direct `@nanogemclaw/gemini` call.
   - **Container Mode**: Isolated execution via `container-runner.ts`.
3. **Persistence**: Every interaction is logged via `@nanogemclaw/db`.
4. **Real-time**: Events emitted via `@nanogemclaw/server` (Socket.IO) to the Dashboard.

## Persistence Layers
- **SQLite**: `store/*.db` (Messages, Tasks, Stats, Knowledge).
- **JSON**: `data/*.json` (Groups, Personas, Skills).
- **Filesystem**: `groups/<chat_id>/` (Conversation logs, Workspace).

---
*For detailed documentation, see [docs-site/reference/architecture.md](file:///Volumes/DevDisk/NanoGemClaw/docs-site/reference/architecture.md)*
