---
trigger: always_on
---

NBot Development Standards & Workflow (Session 2 - Buff Persistence)
I. CODING STYLE GUIDELINES
1. Language & Documentation Policy
# ✅ CORRECT: Internal code uses English
async def apply_emotional_state(self, user_id: int, state_type: str, duration: int) -> None:
    """Apply emotional state (debuff/buff) to user.
    
    Args:
        user_id (int): Discord user ID.
        state_type (str): Type of buff ('suy', 'lucky_buff', 'legendary_buff').
        duration (int): Duration in casts (counter) or seconds (time).
    """
    logger.info(f"[BUFF] Applied {state_type} to user {user_id}")
    # Internal comments in English
    await save_user_buff(user_id, state_type, duration_type, end_time, remaining_count)
    
# ❌ WRONG: Vietnamese for variables/comments
async def ap_dung_trang_thai(self, nguoi_dung_id: int, loai: str, thoi_luong: int):
    # Lưu vào database (BAD - use English)
Rules:

Variables, Functions, Classes: English only
Comments, Docstrings, Logs: English only
Discord Messages (User-facing): Vietnamese mandatory
Reports/Walkthroughs: Vietnamese with English technical terms intact
2. Docstring Standard (Google Style - Mandatory)
async def get_user_buffs(user_id: int) -> dict:
    """Fetch all active buffs for a user from database with lazy expiry cleanup.
    
    Performs lazy deletion of expired time-based buffs. Cache TTL: 60s.
    
    Args:
        user_id (int): The Discord user ID.
        
    Returns:
        dict: Dictionary of active buffs. Format:
            {
                "buff_type": {"remaining": int, "end_time": float, ...},
                ...
            }
            
    Raises:
        DatabaseError: If connection fails.
        
    Example:
        >>> buffs = await get_user_buffs(123456)
        >>> if "lucky_buff" in buffs:
        >>>     print("User has lucky buff!")
    """
Structure:

Brief description (1 line)
Detailed explanation (optional, 1-2 lines)
Args: section with type hints in description
Returns: section with type and format details
Raises: (if applicable)
Example: (for complex functions)
3. Async/Await Discipline (Critical)
# ✅ CORRECT: Fully async chain
async def check_buff(self, user_id: int) -> bool:
    buffs = await get_user_buffs(user_id)  # Await DB call
    return "lucky_buff" in buffs
async def fish_action(self):
    if await self.check_buff(user_id):  # Await the check
        luck += 0.5
        
# ❌ WRONG: Missing await causes RuntimeWarning
async def check_buff(self, user_id: int) -> bool:
    buffs = await get_user_buffs(user_id)
    return "lucky_buff" in buffs
async def fish_action(self):
    if self.check_buff(user_id):  # FATAL: Missing await!
        luck += 0.5
Rules:

Never block the event loop: No time.sleep(), use asyncio.sleep()
Heavy tasks in executor: Image processing (Pillow) must use loop.run_in_executor(None, sync_func, args)
Cascade async: If A calls B and B is async, A must be async too
Database I/O: Always async (aiosqlite, custom 
DatabaseManager
)
4. Database Best Practices
# ✅ CORRECT: Atomic transaction for multi-step operations
operations = [
    ("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?", (qty, uid, item)),
    ("UPDATE users SET seeds = seeds + ? WHERE user_id = ?", (price, uid))
]
await db_manager.batch_modify(operations)  # All-or-nothing
db_manager.clear_cache_by_prefix(f"inventory_{uid}")
# ❌ WRONG: Race condition risk (no transaction)
await remove_item(user_id, "fish", 5)
await add_seeds(user_id, 100)  # If this fails, fish already removed!
Rules:

Use Transactions: 
batch_modify()
 for money/item exchanges
Cache Invalidation: Clear cache after modifying data
Foreign Keys: Enable PRAGMA foreign_keys=ON
Lazy Deletion: Clean expired data on read, not background loops
Connection Pooling: Use singleton 
DatabaseManager
, not ad-hoc connections
5. State Management Philosophy
# ✅ CORRECT: Critical state in DB, cache in RAM
class EmotionalStateManager:
    def __init__(self):
        # No self.emotional_states = {} (RAM)
        pass  # Stateless, queries DB
        
    async def check_emotional_state(self, user_id: int, state_type: str) -> bool:
        buffs = await get_user_buffs(user_id)  # From DB
        return state_type in buffs
# ❌ WRONG: Everything in RAM (lost on restart)
class EmotionalStateManager:
    def __init__(self):
        self.emotional_states = {}  # BAD: Lost on restart
Hierarchy:

Database (SQLite): Source of truth for critical state (Buffs, Inventory, Balance)
RAM Cache: Performance only (60s TTL, auto-invalidate)
Session Data: Non-critical UI state (Pending interactions, View states)
II. WORKFLOW & PROBLEM-SOLVING APPROACH
Phase 1: PLANNING (Understand & Design)
Steps:

Analyze Requirements:

Identify the core problem (e.g., "Buffs lost on restart")
List affected systems (e.g., EmotionalStateManager, FishingCog, Sell command)
Design Schema Changes:

-- Plan DB structure BEFORE coding
CREATE TABLE user_buffs (
    user_id INTEGER,
    buff_type TEXT,
    duration_type TEXT,  -- 'time' or 'counter'
    end_time REAL,
    remaining_count INTEGER,
    PRIMARY KEY (user_id, buff_type),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
Create Implementation Plan (
implementation_plan.md
):

List all files to modify
Group by component (Database, Core Logic, UI)
Define verification steps
Artifact Example:

## Proposed Changes
### Database (`setup_data.py`, `database_manager.py`)
- Add `user_buffs` table
- Add `save_user_buff()`, `get_user_buffs()`, `remove_user_buff()`
### Logic (`cogs/fishing/mechanics/buffs.py`)
- Refactor `EmotionalStateManager` to be async
- Replace `self.emotional_states` with DB calls
Phase 2: EXECUTION (Implement & Refactor)
Best Practices:

Incremental Changes:

Fix one module at a time (Database → Core → Cog → UI)
Test compilation after each major change
Refactoring Ceremony:

# Step 1: Add new async method
async def check_emotional_state(self, user_id, state_type):
    return await self.manager.check_emotional_state(user_id, state_type)
# Step 2: Find all calls (grep_search)
# Step 3: Update callers to await
if await self.check_emotional_state(user_id, "suy"):  # Add await
# Step 4: Remove old sync method
Common Pitfalls & Solutions:

Issue	Cause	Solution
RuntimeWarning: coroutine never awaited	Missing await	Grep for all calls, add await
AttributeError: no attribute 'X'	Init code after return or in wrong scope	Move to 
init
FOREIGN KEY constraint failed	Test user not in DB	Call 
get_or_create_user()
 first
AttributeError: no attribute 'fetchall'	Wrong method name	Check API (use 
execute
 not fetchall)
Phase 3: VERIFICATION (Test & Validate)
Methodology:

Write Verification Script (Before deploying):

# test_buff_persistence.py
async def test_persistence():
    # 1. Apply buff
    await manager.apply_emotional_state(TEST_USER, "lucky_buff", 1)
    
    # 2. Verify DB
    rows = await db_manager.execute("SELECT * FROM user_buffs WHERE user_id = ?", (TEST_USER,))
    assert len(rows) > 0, "Buff not saved!"
    
    # 3. Simulate restart (new instance)
    manager2 = EmotionalStateManager()
    is_active = await manager2.check_emotional_state(TEST_USER, "lucky_buff")
    assert is_active, "Buff lost on restart!"
    
    # 4. Test expiry
    await asyncio.sleep(6)
    is_active = await manager2.check_emotional_state(TEST_USER, "keo_ly")
    assert not is_active, "Expired buff still active!"
Test Checklist (In 
walkthrough.md
):

## Manual Verification
1. Get "Lucky Buff" from NPC event
2. Restart bot (`sudo systemctl restart discordbot`)
3. Use `/cauca` → Should still show "✨(BUFF MAY MẮN!)"
4. Get "Keo Ly" buff
5. Restart bot
6. Use `/ban` → Should show "x2" multiplier
Logging Strategy:

logger.info(f"[BUFF] Applied {state_type} to user {user_id} (counter={remaining})")
logger.info(f"[BUFF] {state_type} expired for user {user_id}")
logger.error(f"[BUFF] Failed to save: {e}")
III. ARCHITECTURE PATTERNS
1. Module Organization (Separation of Concerns)
cogs/fishing/
├── cog.py              # Main command handlers (thin layer)
├── mechanics/
│   ├── buffs.py        # Buff logic (EmotionalStateManager)
│   ├── events.py       # Event triggers (returns dicts, no state)
│   └── legendary_quest_helper.py  # Quest persistence
├── utils/
│   └── helpers.py      # Pure functions (formatting, calculations)
├── commands/
│   └── sell.py         # Sell command logic
└── constants.py        # Data (FISH_DATA, ROD_LEVELS)
Principles:

Cog: Thin controller, delegates to mechanics
Mechanics: Business logic, stateless services
Utils: Pure functions, no side effects
Constants: Data-driven, no hardcoded values
2. Error Recovery Pattern
async def apply_buff(user_id, buff_type, duration):
    try:
        await save_user_buff(user_id, buff_type, duration_type, end_time, remaining)
        logger.info(f"[BUFF] Applied {buff_type} to user {user_id}")
    except sqlite3.IntegrityError as e:
        if "FOREIGN KEY" in str(e):
            # Auto-fix: Create user if missing
            await get_or_create_user(user_id, "Unknown")
            await save_user_buff(user_id, buff_type, duration_type, end_time, remaining)
        else:
            raise
    except Exception as e:
        logger.error(f"[BUFF] Failed to apply {buff_type}: {e}")
        raise
IV. CRITICAL LESSONS FROM THIS SESSION
1. The Reentrant Lock Deadlock (Previous Session Review)
Symptom: !cauca hung on "Waiting..." indefinitely.
Root Cause: Nested asyncio.Lock acquisition within same context.
Solution: Remove redundant inner locks. One lock per user transaction scope.

2. Code After Return Statement
Symptom: AttributeError: 'FishingCog' object has no attribute 'disaster_fine_amount'
Root Cause: Init code placed AFTER return in a function.
Lesson: Always validate function structure. Code after return is unreachable.

3. Cascade Async Refactoring
Symptom: RuntimeWarning: coroutine 'check_emotional_state' was never awaited
Root Cause: Made method async but forgot to update ALL callers.
Solution:

grep_search for all usages
Update each caller to await
Make caller async if needed (cascade)
4. Test User Foreign Key Violation
Symptom: sqlite3.IntegrityError: FOREIGN KEY constraint failed
Root Cause: Test script used TEST_USER_ID=999999 which doesn't exist in users table.
Solution: Always call 
get_or_create_user()
 in test setup.

V. QUICK REFERENCE CHECKLIST
Before Coding:
 Create 
implementation_plan.md
 with file-by-file changes
 Design DB schema changes (if needed)
 Identify all affected modules (grep for related code)
During Coding:
 Use Google Style docstrings for all functions
 Ensure async/await discipline (no missing awaits)
 Use transactions for multi-step DB operations
 Clear cache after modifying data
 Add comprehensive logging (logger.info, logger.error)
After Coding:
 Write verification script (test_*.py)
 Create 
walkthrough.md
 with test results
 Run verification script successfully
 Manual test via Discord commands
 Check logs for warnings/errors
Deployment:
 Restart bot (sudo systemctl restart discordbot)
 Monitor logs (sudo journalctl -u discordbot -f)
 Verify no RuntimeWarnings or AttributeErrors
VI. COMMUNICATION STYLE WITH USER
Language: Vietnamese for explanations, English for code/technical terms
Tone: Direct, honest about mistakes, proactive
Format:

Use emoji for status (✅ ❌ 🎉 ⚠️)
Bold for emphasis
Code blocks for examples
Lists for multiple items
Example:

Ối, có 2 lỗi nghiêm trọng mình bỏ sót:
## Lỗi 1: Missing `await` trong sell.py
**RuntimeWarning: coroutine never awaited**
- Đã fix: Thêm `await` vào line 38
## Lỗi 2: Missing attribute `disaster_fine_amount`  
**AttributeError**
- Nguyên nhân: Init code đặt SAU `return` statement
- Đã fix: Di chuyển vào `__init__` method
END OF STANDARDS DOCUMENT