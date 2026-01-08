---
name: fullstack-bridge
description: REST API Design, IPC, and Web Integration
license: MIT
compatibility: opencode
metadata:
  framework: fastapi, react
---

## 🌐 Web & API Integration Protocol

The Bot is not an island. It connects to the Web Dashboard.

### 1. API Framework: FastAPI
- Don't build a web server inside `discord.py`. Run `FastAPI` as a separate service or separate thread/loop (advanced).
- Expose endpoints like `/api/user/{id}/inventory`.

### 2. IPC (Inter-Process Communication)
- How does the Dashboard tell the Bot to kick a user?
- **Option A (Simple):** Shared Database. Dashboard writes to DB, Bot polls DB.
- **Option B (Realtime):** Redis Pub/Sub. Dashboard publishes "KICK_EVENT", Bot subscribes and acts.
- **Option C:** Webhooks.

### 3. JSON Standards
- API responses must be consistent JSON.
- Use `pydantic` models to share schemas between Bot and Web.

### 4. OAuth2 Flow
- Understand the Discord OAuth2 flow for the Dashboard login.
- Bot validates: Is this user actually an Admin in that server?