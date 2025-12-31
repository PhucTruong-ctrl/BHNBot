# ARCHITECTURE OPTIMIZATION PLAN
**Benchmark Target:** [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot)
**Goal:** Professionalize BHNBot source code for Scalability, Security, and Maintainability.

---

## 1. Red-DiscordBot Analysis (The Benchmark)

Red-DiscordBot is widely considered the "Gold Standard" for Python Discord Bots. Its architecture handles thousands of self-hosted instances with high stability.

### 1.1 Core Architecture
*   **Modular Cogs:** Every feature is a self-contained module (folder) with a `setup` entry point. It never puts logic in the main bot file.
*   **Data Abstraction (Config):** Red uses `redbot.core.Config` - an abstraction layer that handles JSON/MongoDB/Postgres drivers transparently. Developers don't write SQL; they write `await config.user(user).seeds.set(100)`.
*   **Event Loop Management:** Heavy tasks are pushed to thread pools executors automatically to avoid blocking the Gateway heartbeat (keeping the bot responsive).

### 1.2 Security & Permissions
*   **Decorators over If-Statements:** Instead of hardcoding `if ctx.author.id == 123:`, Red uses decorators:
    ```python
    @commands.command()
    @checks.is_owner()
    @checks.admin_or_permissions(manage_guild=True)
    async def ban(self, ctx, ...):
    ```
*   **Granular Control:** Permissions are checkable at Cog, Command, and Group levels.

### 1.3 Error Handling
*   **Global Error Handler:** A centralized system catches *all* unhandled exceptions. It formats the traceback safely and logs it, preventing the bot process from dying.
*   **User Feedback:** The bot tells the user "Something went wrong" politely, while sending the full crash log to the Ops channel/Console.

### 1.4 Deployment & Lifecycle
*   **Systemd/Docker:** Red runs as a background service.
*   **Auto-Restart:** If the process dies (OOM, Error), the service manager automatically restarts it.

---

## 2. GAP Analysis: BHNBot vs. Red-DiscordBot

| Feature | Red-DiscordBot Standard | BHNBot Current State | Risk / Gap |
| :--- | :--- | :--- | :--- |
| **Project Structure** | 100% Folder-based Cogs (Standardized) | Hybrid: Mix of file cogs (`economy.py`) and folders (`fishing/`) | 🟡 **Messy:** Hard to navigate & scale. |
| **Data Access** | `Config` Abstraction Layer (No SQL in commands) | Direct SQL (`await db.execute(...)`) inside Cogs | 🔴 **High:** Hard to maintain SQL, risk of injection if not careful. |
| **Permissions** | `@checks.is_admin()` decorators | Mixed: Hardcoded IDs + some role checks | 🔴 **Critical:** Hardcoded IDs are unmaintainable. |
| **Error Handling** | Global Handler + Sentry Integration | Basic `try/except` per command or None | 🔴 **Critical:** Bot can crash silently or spam console. |
| **Shared Utils** | `redbot.core.utils` (Menus, Chat formatting) | Scattered helper functions (duplicated in cogs) | 🟡 **Inefficient:** Code duplication. |
| **Consistency** | ACID Transactions handled by Core | Manual Transaction management in some places | 🔴 **Data Risk:** Race conditions possible. |
| **Logging** | Structured Logging (Rotation, Levels) | Basic `print` or simple Logger | 🟡 **Warning:** Difficult to debug history. |

---

## 3. Optimization Roadmap

To elevate BHNBot to Red's level, we will execute the following phases:

### Phase 1: Core Foundation (The "Red" Core)
*   [x] **Create `core.checks`:** Implement decorators for permissions.
    *   `@checks.is_owner()`, `@checks.mod_or_permissions()`.
*   [x] **Create `core.utils`:** Centralize common utilities.
    *   `chat_formatting.py`: box, pagify, humanize_number.
    *   `menus.py`: Standards for Button/Select menus. [COMPLETED]
*   [x] **Standardize Database Manager:**
    *   (Skipped/Reserved) User prefers Keeping AsyncPG direct calls but using DAO pattern.

### Phase 2: Structural Refactoring
*   [x] **Convert Single-File Cogs to Folders:**
    *   `cogs/economy.py` -> `cogs/economy/__init__.py`, `cogs/economy/cog.py` [COMPLETED].
    *   `cogs/shop.py` -> `cogs/shop/` [COMPLETED].
*   [x] **Logic Separation (MVC Pattern):**
    *   **Model:** Database queries (in `core/models` or `cog/core`).
    *   **View:** Embeds & UI (in `cog/ui`).
    *   **Controller:** Command handling (in `cog/cog.py`).
*   [x] **Admin Refactor:**
    *   Updated `cogs/admin/management.py` to use `@checks.is_owner()`.

### Phase 3: Reliability & DevEx
*   [x] **Robust Global Error Handler:** Implements `on_command_error` in a separate `ErrorHandler` cog.
    *   [x] `core/errors.py` created.
    *   [x] Loaded in `main.py`.
*   [x] **Systemd Service File:** Verified existing `discordbot.service`.
*   [x] **Hot-Reloading:** Verified existing `!cog reload` command in `admin/management.py` (supports new folder structure).

---

## 4. Immediate Action Plan (Next Steps)

1.  **Refactor `shop.py`** following the Economy Cog pattern.
2.  **Refactor `admin/` cogs** to use `@checks` instead of manual checks.
3.  **Implement `!reload`** command.
