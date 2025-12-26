---
applyTo: '**'
---

BHNBot Development Knowledge Base & Session Summary
1. Core Philosophy & Coding Standards
Language Policy:
Internal: English for all comments, docstrings, logs, and variable names.
User-Facing: Vietnamese for all Discord messages, embeds, and UI elements.
Docstring Style: Google Style is mandatory for all functions and classes.
def example_func(param1: int) -> bool:
    """Brief description.
    Args:
        param1 (int): Description.
    Returns:
        bool: usage description.
    """
Async/IO:
Strict Non-blocking: Never use time.sleep or synchronous file/network I/O in async functions.
Database: Use aiosqlite via the standardized 
DatabaseManager
.
Heavy Tasks: Image processing/calculations must use run_in_executor.
State Management: Critical game state must be persisted to SQLite. RAM usage is for cache only.
2. System Architecture
configs/: Static settings (settings.py, game_config.json). No logic here.
core/: Shared utilities.
database_manager.py
: Singleton 
DatabaseManager
 with connection pooling and caching.
logger.py
: Standardized rotating file logging.
cogs/
: Feature modules (Fishing, Economy, Shop).
Fishing: Complex logic split into 
cog.py
 (logic), 
views.py
 (UI), 
events.py
 (mechanics), 
models.py
 (data).
3. Critical Engineering Learnings
Case Study: The Reentrant Deadlock (Fishing Command)
Symptom: The !cauca command hung on "Waiting..." and sometimes sent duplicate start messages.
Root Cause: Reentrant Deadlock. The main handler 
_fish_action
 acquired self.user_locks[user_id] (Outer Scope). Inside the execution loop, helper logic attempted to acquire the same lock again (Inner Scope). Since asyncio.Lock is not reentrant, the inner request waited forever for the outer request to release.
Solution: Removed redundant inner locks. The Outer Lock is sufficient to protect the entire user transaction scope.
Rule: Never nest asyncio.Lock acquisitions for the same resource within the same execution context.
Common Patterns
Atomic Transactions: Use db_manager.batch_modify for multi-step items/money exchanges (e.g., Selling items).
Update Protocols: When updating a Cog, always standardize its docstrings to Google Style first to ensure readability.
4. Work Status & Next Steps
Completed Standardization: 
database_manager.py
, 
core/logger.py
, cogs/fishing (all files), cogs/shop.py, cogs/economy.py.
Pending Standardization:
cogs/werewolf/ (Complex OOP structure)
cogs/minigames/ (baucua.py, noitu.py)
Action Items: Continue applying the English/Google Style standard to the remaining cogs in the next session.