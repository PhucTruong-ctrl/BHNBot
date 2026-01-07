# BHNBot - GitHub Issues Template

Tạo các issues sau trên GitHub để track tiến độ:

---

## 🔴 CRITICAL SECURITY ISSUES

### Issue #1: Race Condition - Xi Dách Double-Spend

**Priority:** P0 - Critical  
**Labels:** bug, security, economy  
**Affected:** `cogs/xi_dach/commands/multi.py`

**Description:**
Users can spam bet button to bet multiple times with same balance, resulting in negative seeds.

**Exploit Scenario:**
```python
# User has 100 seeds
# Rapidly clicks "Bet 100" 5 times
# Result: -400 seeds (bet 500 total)
```

**Impact:**  
- Complete economy break
- Users can generate infinite negative money
- Affects all gambling features

**Fix Status:** ✅ FIXED in latest commit  
**Fix Details:** Wrapped balance check and deduction in atomic transaction with `FOR UPDATE` lock.

**Testing:**
- [x] Spam bet button 10 times  
- [x] Verify balance stays positive
- [x] Test with concurrent users

**File Changed:** `cogs/xi_dach/commands/multi.py` (lines 178-238)

---

### Issue #2: SQL Injection Risk - Server Config

**Priority:** P0 - Critical  
**Labels:** security, vulnerability  
**Affected:** `database_manager.py`

**Description:**
Functions `get_server_config` and `set_server_config` use f-strings to inject column names directly into SQL queries.

**Exploit Scenario:**
```python
# If any future feature allows user input:
/config get "seeds FROM users --"
# Would leak all user balances
```

**Impact:**
- Potential data leak
- Database manipulation
- Requires user input to field parameter (currently only admin-callable)

**Fix Status:** ✅ FIXED in latest commit  
**Fix Details:** Added `ALLOWED_CONFIG_FIELDS` whitelist, raises `ValueError` for invalid fields.

**Testing:**
- [x] Test with valid field names
- [x] Test with malicious input (should raise ValueError)

**File Changed:** `database_manager.py` (lines 151-194)

---

### Issue #3: Transaction Deadlock - Fishing Module

**Priority:** P0 - Critical  
**Labels:** performance, bug, database  
**Affected:** `cogs/fishing/cog.py`

**Description:**
The main fishing function holds a database transaction open for 1-60 seconds (includes `asyncio.sleep` and boss fight views), causing "database is locked" errors for all other users.

**Current Code Issue:**
```python
async with db_manager.transaction():
    # Deduct bait
    await asyncio.sleep(5)  # ← LOCK HELD FOR 5s!
    # Boss fight view
    await view.wait()  # ← LOCK HELD FOR 60s!
    # Add rewards
```

**Impact:**
- Bot becomes unresponsive during fishing
- Multiple concurrent fishers = cascading deadlocks
- All economy/shop operations blocked

**Fix Strategy:**
Break transaction into 3 atomic parts:
1. Deduct resources (short transaction)
2. Wait / UI interaction (NO transaction)
3. Add rewards (short transaction)

**Affected Line:** `cogs/fishing/cog.py:632-834`

**Status:** ⏳ DOCUMENTED (requires careful refactoring)  
**Estimated Effort:** 3-4 hours  
**Complexity:** High (1700-line function)

**References:**
- See `/docs/QUICK_FIXES.md` for detailed refactoring guide
- See `/docs/AUDIT_REPORT_2026.md` Section "Performance Bottlenecks"

---

## 🟡 HIGH PRIORITY BUGS

### Issue #4: Daily Window Inconsistency

**Priority:** P1 - High  
**Labels:** bug, ux  
**Affected:** `cogs/economy.py`

**Description:**
Code allows daily claim until 12 PM but error message says "5h-10h only"

**Fix Status:** ✅ FIXED  
**Fix Details:** Changed `DAILY_WINDOW_END = 10` to match message.

**File Changed:** `cogs/economy.py` (line 22)

---

### Issue #5: Silent View Timeouts

**Priority:** P1 - High  
**Labels:** ux, bug  
**Affected:** `cogs/fishing/views.py`, `cogs/fishing/mechanics/*.py`

**Description:**
Interactive views (sell fish, NPC events) timeout without notifying user. Message remains with disabled buttons but no "Timed Out" message.

**Impact:**  
Users think bot is broken when interactions stop responding.

**Fix Required:**
```python
async def on_timeout(self):
    try:
        await self.message.edit(
            content="⏰ **Hết thời gian!** Phiên giao dịch đã kết thúc.",
            view=None
        )
    except:
        pass
    # Existing cleanup...
```

**Affected Files:**
- `cogs/fishing/views.py` (FishSellView)
- `cogs/fishing/mechanics/event_views.py` (all views)
- Other interactive views

**Status:** ⏳ TODO  
**Effort:** 1-2 hours

---

## 🟢 MEDIUM PRIORITY OPTIMIZATIONS

### Issue #6: Aquarium Dashboard Rate Limit

**Priority:** P2 - Medium  
**Labels:** performance, optimization  
**Affected:** `cogs/aquarium/cog.py`

**Description:**
Dashboard refreshes on EVERY message in thread → hits Discord rate limits with active chatters.

**Fix Required:**
```python
self.last_dashboard_refresh = {}

async def refresh_dashboard(self, thread_id):
    now = time.time()
    if now - self.last_dashboard_refresh.get(thread_id, 0) < 30:
        return  # Debounce 30s
    self.last_dashboard_refresh[thread_id] = now
    # ... refresh logic
```

**Status:** ⏳ TODO  
**Effort:** 30 minutes

---

### Issue #7: N+1 Query Pattern - Fishing Stats

**Priority:** P2 - Medium  
**Labels:** performance, database  
**Affected:** `cogs/fishing/cog.py`, `database_manager.py`

**Description:**
Catching 5 fish → 15-20 sequential DB queries for stats/achievements.

**Fix Strategy:**
Implement `batch_increment_stats` helper:
```python
await batch_increment_stats(user_id, "fishing", {
    "worms_used": 1,
    "fish_caught": 5,
    "events": 1
})
```

**Status:** ⏳ TODO  
**Effort:** 2-3 hours

---

### Issue #8: Non-Atomic Stat Increment

**Priority:** P2 - Medium  
**Labels:** bug, race-condition  
**Affected:** `database_manager.py` (line 258)

**Description:**
`increment_stat` uses SELECT-then-UPDATE pattern → race conditions → lost stat updates.

**Fix Required:**
```sql
INSERT INTO user_stats VALUES ($1, $2, $3, $4)
ON CONFLICT (user_id, game_id, stat_key) 
DO UPDATE SET value = user_stats.value + EXCLUDED.value
```

**Status:** ⏳ TODO  
**Effort:** 1 hour

---

## 📋 TECHNICAL DEBT

### Issue #9: Database Migration Strategy

**Priority:** P3 - Low  
**Labels:** architecture, refactoring  

**Description:**
Current migration system uses ad-hoc `ensure_*_tables()` calls. Need versioned migration framework.

**Proposal:**
- Create `migrations/` directory
- Implement migration runner with version tracking
- Add rollback support

**References:** `/docs/DB_MIGRATION_PLAN.md` (to be created)

**Status:** ⏳ PLANNING  
**Effort:** 1-2 weeks

---

## ✅ COMPLETED

### ~~Issue #10: Xi Dách Race Condition~~ ✅
**Status:** FIXED  
**Commit:** [latest]

### ~~Issue #11: SQL Injection Whitelist~~ ✅
**Status:** FIXED  
**Commit:** [latest]

### ~~Issue #12: Daily Window Fix~~ ✅
**Status:** FIXED  
**Commit:** [latest]

---

## 📊 ISSUE STATS

- **Total Issues:** 12
- **Critical:** 3 (1 fixed, 1 needs refactoring)
- **High:** 2 (1 fixed, 1 todo)
- **Medium:** 3 (all todo)
- **Tech Debt:** 1 (planning)
- **Completed:** 3

**Estimated Total Effort:** 10-15 hours for all pending issues

---

## 🔗 RELATED DOCUMENTS

- `/docs/AUDIT_REPORT_2026.md` - Full analysis
- `/docs/QUICK_FIXES.md` - Code examples
- `/docs/COGS_REFERENCE.md` - Module reference

**Last Updated:** 2026-01-07
