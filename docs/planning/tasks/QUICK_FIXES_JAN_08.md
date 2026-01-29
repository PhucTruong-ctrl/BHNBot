# BHNBot - Quick Fixes Checklist

**Mục đích:** Danh sách các sửa chữa nhanh có impact lớn, sắp xếp theo độ ưu tiên.

---

## 🔴 CRITICAL (Phải sửa ngay - 2-3 giờ)

### 1. Fix Xi Dach Race Condition
**File:** `cogs/xi_dach/commands/multi.py` (`process_bet`)

**Before:**
```python
balance = await get_user_balance(user_id)
if balance < bet:
    return
await add_seeds(user_id, -bet)
```

**After:**
```python
async with db_manager.transaction() as conn:
    balance = await conn.fetchval(
        "SELECT seeds FROM users WHERE user_id = $1 FOR UPDATE", user_id
    )
    if balance < bet:
        raise ValueError("Insufficient balance")
    await conn.execute(
        "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
        bet, user_id
    )
```

**Testing:**
```python
# Spam bet button 10 lần nhanh
# Before: seeds = -500
# After: "Insufficient balance" error
```

---

### 2. Fix Fishing Transaction Scope
**File:** `cogs/fishing/cog.py` (function `_fish_action`)

**Problem:** Transaction bao gồm `asyncio.sleep(3)` → lock DB 3 giây

**Before:**
```python
async with db_manager.transaction():
    # Deduct bait
    ...
    await asyncio.sleep(wait_time)  # ← LOCK HELD!
    await channel.send("...")
    # Add fish
    ...
```

**After:**
```python
# Transaction 1: Deduct resources
async with db_manager.transaction():
    # Deduct bait/seeds
    ...

# Release lock
await asyncio.sleep(wait_time)
await channel.send("...")

# Transaction 2: Add rewards
async with db_manager.transaction():
    # Add fish
    ...
```

---

### 3. SQL Injection Whitelist
**File:** `database_manager.py` (functions `get_server_config`, `set_server_config`)

**Before:**
```python
def get_server_config(field):
    query = f"SELECT {field} FROM server_config ..."  # Unsafe!
```

**After:**
```python
ALLOWED_CONFIG_FIELDS = {
    "fishing_channel_id",
    "harvest_buff_until",
    "exclude_chat_channels",
    # ... add all valid fields
}

def get_server_config(field):
    if field not in ALLOWED_CONFIG_FIELDS:
        raise ValueError(f"Invalid config field: {field}")
    query = f"SELECT {field} FROM server_config ..."
```

---

## 🟡 HIGH PRIORITY (1-2 ngày)

### 4. Fix Daily Window Inconsistency
**File:** `cogs/economy.py`

```python
# Line ~30: Change to
DAILY_WINDOW_END = 10  # Not 12

# Line ~191: Update message to match
"Lệnh này chỉ khả dụng từ 5h-10h sáng."
```

---

### 5. Silent Timeout Notifications
**File:** `cogs/fishing/views.py` (all View classes)

**Before:**
```python
async def on_timeout(self):
    del self.cog.caught_items[self.user_id]
```

**After:**
```python
async def on_timeout(self):
    try:
        await self.message.edit(
            content="⏰ **Hết thời gian!** Phiên giao dịch đã kết thúc.",
            view=None
        )
    except:
        pass
    if self.user_id in self.cog.caught_items:
        del self.cog.caught_items[self.user_id]
```

---

### 6. Atomic Stat Increment
**File:** `database_manager.py` (function `increment_stat`)

**Before:**
```python
async def increment_stat(user_id, game_id, stat_key, amount=1):
    current = await fetchone("SELECT value FROM user_stats ...")
    new_value = (current or 0) + amount
    await execute("UPDATE user_stats SET value = $1 ...", new_value)
```

**After:**
```python
async def increment_stat(user_id, game_id, stat_key, amount=1):
    await db_manager.execute("""
        INSERT INTO user_stats (user_id, game_id, stat_key, value)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id, game_id, stat_key)
        DO UPDATE SET value = user_stats.value + EXCLUDED.value
    """, user_id, game_id, stat_key, amount)
```

---

## 🟢 MEDIUM PRIORITY (1 tuần)

### 7. Aquarium Dashboard Debounce
**File:** `cogs/aquarium/cog.py` (refresh function)

```python
# Add class-level dict
self.last_dashboard_refresh = {}

async def refresh_dashboard(self, thread_id):
    now = time.time()
    last = self.last_dashboard_refresh.get(thread_id, 0)
    
    if now - last < 30:  # Debounce 30s
        return
    
    self.last_dashboard_refresh[thread_id] = now
    # ... existing refresh logic
```

---

### 8. Batch Fishing DB Updates
**File:** `cogs/fishing/cog.py` (after catching fish)

**Concept:**
```python
# Instead of:
for fish in caught:
    await add_fish(user_id, fish)
    await increment_stat(user_id, "fish_caught")

# Do:
updates = [(user_id, fish) for fish in caught]
await db_manager.batch_modify(updates)
await increment_stat(user_id, "fish_caught", amount=len(caught))
```

---

## 📊 IMPACT ESTIMATE

| Fix | Effort | Impact | Users Affected |
|-----|--------|--------|----------------|
| Xi Dach Race | 1h | 🔴 Critical | All gamblers |
| Fishing Transaction | 2h | 🔴 Critical | All fishers |
| SQL Injection | 30m | 🟡 High | Future risk |
| Daily Window | 15m | 🟡 High | Daily users |
| Timeout Notify | 1h | 🟡 High | All interactive |
| Atomic Stats | 1h | 🟡 High | Leaderboards |
| Aquarium Debounce | 30m | 🟢 Medium | Aquarium users |
| Batch Updates | 3h | 🟢 Medium | Performance |

**Total effort cho Priority 1-2:** ~8 giờ coding + 2 giờ testing = **1-2 ngày làm việc**

---

## ✅ TESTING CHECKLIST

### After Xi Dach Fix:
- [ ] Spam bet button 10 lần → Should reject after first bet
- [ ] Check balance stays positive
- [ ] Test with multiple users simultaneously

### After Fishing Fix:
- [ ] 5 users fish at same time → No "database locked" errors
- [ ] Bot responds to other commands during fishing sleep
- [ ] Fish still added to inventory correctly

### After SQL Fix:
- [ ] Try `/config get fishing_channel_id` → Works
- [ ] Try `/config get "seeds FROM users"` → Rejects (if command exists)

### After Timeout Fix:
- [ ] Start fishing → Wait 3 minutes → Message should show "Hết thời gian"
- [ ] Start NPC event → Timeout → Should see notification

---

**Sau khi hoàn thành tất cả:** Chạy full regression test (câu cá, bán cá, mua shop, chơi minigames).
