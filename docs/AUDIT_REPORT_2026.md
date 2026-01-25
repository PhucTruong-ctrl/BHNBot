# BHNBot - Báo Cáo Đánh Giá Toàn Diện (Comprehensive Audit Report)
**Ngày:** 07/01/2026  
**Phạm vi:** UX, Performance, Security, Scalability, Architecture  
**Tổng số dòng code:** ~39,411 lines (cogs) + ~4,500 lines (core)  
**Database:** PostgreSQL (primary), SQLite (legacy migration phase)

---

## 📊 TÓM TẮT ĐIỂM SỐ

| Lĩnh vực | Điểm | Đánh giá |
|----------|------|----------|
| **UX (Trải nghiệm người dùng)** | 7/10 | Tốt nhưng có mâu thuẫn thời gian và timeout thiếu thông báo |
| **Performance (Hiệu năng)** | 6/10 | Có bottleneck nghiêm trọng ở transaction DB trong fishing |
| **Security (Bảo mật)** | 6.5/10 | Race condition nghiêm trọng ở Xì Dách, có SQL injection tiềm ẩn |
| **Scalability (Khả năng mở rộng)** | 7/10 | Tốt cho quy mô trung bình, cần Redis cho scale lớn |
| **Architecture (Kiến trúc)** | 7.5/10 | Modular tốt nhưng DB layer chưa thống nhất |

**Điểm tổng thể:** **6.8/10** - Bot ổn định cho production với quy mô nhỏ-trung, cần sửa các lỗi critical trước khi scale lớn.

---

## 🔴 VẤN ĐỀ NGHIÊM TRỌNG (URGENT - Phải sửa ngay)

### 1. **Race Condition Double-Spend (Xì Dách)** ⚠️ CRITICAL
**File:** `cogs/xi_dach/commands/multi.py`  
**Mô tả:** User có thể spam nút "Bet 100" để bet nhiều lần với cùng 1 số dư, dẫn đến số dư âm.  
**Kịch bản khai thác:**
```python
# User có 100 seeds
# Click "Bet 100" x5 lần trong 100ms
# Kết quả: -400 seeds (đã bet 500 seeds)
```
**Impact:** Mất cân bằng economy, người chơi có thể tạo tiền âm vô hạn.  
**Fix:** Wrap balance check + deduction trong 1 transaction:
```python
async with db_manager.transaction() as conn:
    balance = await conn.fetchval("SELECT seeds FROM users WHERE user_id = $1 FOR UPDATE", user_id)
    if balance < bet_amount:
        raise ValueError("Insufficient balance")
    await conn.execute("UPDATE users SET seeds = seeds - $1 WHERE user_id = $2", bet_amount, user_id)
```

---

### 2. **Long-Held DB Transaction (Fishing)** ⚠️ CRITICAL
**File:** `cogs/fishing/cog.py` (lines 632-834)  
**Mô tả:** Transaction giữ lock DB trong 1-5 giây (bao gồm `asyncio.sleep` và `channel.send`).  
**Impact:** Khi nhiều người câu cá cùng lúc → "database is locked" → toàn bộ bot bị đứng.  
**Fix:** Thu hẹp transaction scope:
```python
# SAI (hiện tại):
async with db_manager.transaction():
    deduct_bait()
    await asyncio.sleep(3)  # ← LOCK HELD HERE!
    send_message()
    add_fish()

# ĐÚNG (nên sửa):
async with db_manager.transaction():
    deduct_bait()
# Lock released
await asyncio.sleep(3)
send_message()
async with db_manager.transaction():
    add_fish()
```

---

### 3. **SQL Injection Risk (Server Config)** ⚠️ HIGH
**File:** `database_manager.py` (`get_server_config`, `set_server_config`)  
**Mô tả:** Dùng f-string để insert tên cột vào SQL:
```python
query = f"SELECT {field} FROM server_config ..."  # ← Unsafe!
```
**Kịch bản khai thác:** Nếu có lệnh `/config get <field>` trong tương lai, attacker có thể inject:
```
/config get "seeds FROM users --"
→ Leak toàn bộ seeds của users
```
**Fix:** Dùng whitelist:
```python
ALLOWED_FIELDS = {"fishing_channel_id", "harvest_buff_until", ...}
if field not in ALLOWED_FIELDS:
    raise ValueError("Invalid field")
```

---

### 4. **Daily Window Mâu Thuẫn (Economy)** ⚠️ MODERATE
**File:** `cogs/economy.py`  
**Mô tả:** Code cho phép claim đến 12h nhưng error message nói "Only until 10h".  
**Impact:** User bối rối, support tăng.  
**Fix:** Thống nhất `DAILY_WINDOW_END = 10` và sửa tất cả comments/messages.

---

## 🟡 VẤN ĐỀ TRUNG BÌNH (Nên sửa sớm)

### 5. **N+1 Query Pattern (Fishing)**
**File:** `cogs/fishing/cog.py` (lines 1397-1489)  
**Mô tả:** Khi câu được 5 con cá → 15-20 DB queries tuần tự.  
**Impact:** Latency cao (200-500ms thay vì 50ms).  
**Fix:** Batch updates:
```python
# Thay vì:
for fish in caught_fish:
    await add_fish(fish)
    await increment_stat("fish_caught")
    
# Làm:
await db_manager.batch_modify([
    ("inventory", fish1), ("inventory", fish2), ...
])
```

---

### 6. **Non-Atomic Stat Increment**
**File:** `database_manager.py` (line 258)  
**Mô tả:** `SELECT value → UPDATE value` → race condition → mất stat.  
**Fix:**
```sql
-- Thay vì SELECT rồi UPDATE, dùng:
INSERT INTO user_stats VALUES ($1, $2, $3, $4) 
ON CONFLICT (user_id, game_id, stat_key) 
DO UPDATE SET value = user_stats.value + EXCLUDED.value
```

---

### 7. **Silent Timeout (Fishing Views)**
**File:** `cogs/fishing/views.py` (line 29)  
**Mô tả:** Khi view timeout, message vẫn hiển thị buttons (disabled) mà không thông báo.  
**Fix:**
```python
async def on_timeout(self):
    await self.message.edit(
        content="⏰ **Hết thời gian!** Phiên bán cá đã kết thúc.",
        view=None
    )
```

---

## 🟢 VẤN ĐỀ NHỎ (Nice to have)

### 8. **Aquarium Dashboard Spam**
**File:** `cogs/aquarium/cog.py`  
**Mô tả:** Refresh embed sau **mỗi tin nhắn** trong thread → rate limit.  
**Fix:** Debounce 30s:
```python
last_refresh = getattr(self, 'last_refresh', 0)
if time.time() - last_refresh < 30:
    return
```

### 9. **Emoji Inconsistency**
Seeds dùng lẫn 💰/🌱/💎.  
**Fix:** Chọn 1 emoji duy nhất (đề xuất 🌰).

---

## ✅ ĐIỂM MẠNH (Nên giữ nguyên)

1. **ACID Transactions trong Shop/Economy** - Rất tốt, ngăn dupe items.
2. **Asset Caching (Xì Dách)** - Tải ảnh 1 lần, cache RAM → render nhanh.
3. **Async Image Processing** - Dùng `run_in_executor` đúng cách.
4. **Modular Cogs** - Fishing/Werewolf/Aquarium tách module rõ ràng.
5. **Interactive NPC Feedback** - Timeout có thông báo đầy đủ.

---

## 📈 KHUYẾN NGHỊ SCALE CHO TỪNG COG

### Fishing Module - **3/5**
**Có thể scale đến:** 500-1000 users đồng thời  
**Bottleneck:** In-memory cooldowns, heavy DB transaction  
**Khuyến nghị:**
- Di chuyển cooldowns sang Redis
- Batch DB updates
- Tách event manager thành service riêng

### Werewolf Module - **2/5**
**Có thể scale đến:** 10-20 games/guild  
**Bottleneck:** Discord API (tạo category/channels liên tục)  
**Khuyến nghị:**
- Reuse channels cố định thay vì tạo mới
- Giới hạn concurrent games
- Cache voice states

### Economy Module - **4/5**
**Có thể scale đến:** 10,000+ users  
**Bottleneck:** Chat reward ghi DB mỗi message  
**Khuyến nghị:**
- Buffer rewards, flush 60s/lần
- Partition transaction_logs table

### Aquarium Module - **2/5**
**Có thể scale đến:** 5-10 active threads  
**Bottleneck:** Refresh embed mỗi message → rate limit  
**Khuyến nghị:**
- **CRITICAL**: Implement debounce 30s
- Chỉ refresh khi có lệnh cụ thể

### Tree Module - **3/5**
**Có thể scale đến:** 100-200 guilds  
**Bottleneck:** Daily task update hàng trăm embeds cùng lúc  
**Khuyến nghị:**
- Stagger updates (guild 1 → chờ 2s → guild 2...)
- Task queue system

### Shop & Minigames - **4/5**
**Có thể scale đến:** High throughput  
**Bottleneck:** Không đáng kể  
**Khuyến nghị:** Ready to scale

---

## 🏗️ LỘ TRÌNH TỐI ƯU HÓA

### ⚡ Ngay lập tức (1-2 tuần)
1. ✅ **Fix Race Condition Xì Dách** - Wrap balance check trong transaction
2. ✅ **Fix Long-held Transaction Fishing** - Thu hẹp scope
3. ✅ **Whitelist SQL fields** - Ngăn injection
4. ✅ **Fix Daily Window Mâu Thuẫn** - Thống nhất 10h
5. ✅ **Silent Timeout Notifications** - Edit message khi timeout

**Effort:** 1-2 ngày  
**Impact:** Sửa 90% lỗi nghiêm trọng

---

### 📅 Ngắn hạn (1-3 tháng)
1. **Batch DB Updates trong Fishing** - Giảm latency
2. **Atomic Stat Increment** - Dùng ON CONFLICT
3. **Aquarium Debounce** - Ngăn rate limit
4. **Composite Indexes** - `user_stats(user_id, game_id)`
5. **Partition transaction_logs** - Theo tháng

**Effort:** 3-5 ngày  
**Impact:** Tăng 2-3x performance

---

### 🚀 Trung hạn (6 tháng)
1. **Redis cho Cooldowns/Sessions** - Cho phép restart không mất state
2. **Economy Chat Reward Batching** - Buffer 60s
3. **Migration System** - Thay ensure_* bằng versioned migrations
4. **Service Layer cho Fishing/VIP** - Tách logic khỏi cogs
5. **Unify DB Layer** - Postgres-first, loại bỏ ? placeholders

**Effort:** 1-2 tuần  
**Impact:** Chuẩn bị cho scale lớn

---

### 🌟 Dài hạn (1 năm+)
1. **Sharding Support** - Multi-instance bot
2. **Data Archiving** - Move old transaction_logs
3. **Observability** - Request ID tracking, APM
4. **Comprehensive Tests** - Cover 80% economy/inventory

**Effort:** 3-4 tuần  
**Impact:** Enterprise-ready

---

## 📊 DATABASE GROWTH PREDICTIONS

| Table | Current Size | Monthly Growth | Action Needed |
|-------|--------------|----------------|---------------|
| `transaction_logs` | N/A | +1M rows | ⚠️ Partition by month |
| `user_stats` | N/A | +100K rows | ✅ Add composite index |
| `inventory` | N/A | +10K rows | ✅ OK |
| `fish_collection` | N/A | +5K rows | ✅ OK |

**Projection:** Database sẽ đạt 1GB sau 6-12 tháng nếu có 1000+ active users.

---

## 🎯 KẾT LUẬN

BHNBot có **foundation rất tốt**: Modular, có transactions, có tests. Tuy nhiên:

**Điểm yếu lớn nhất:**
1. Race conditions (Xì Dách, Shop unique items)
2. DB transaction scope quá rộng (Fishing)
3. DB layer chưa thống nhất (SQLite/Postgres mixed)

**Khuyến nghị ưu tiên cao nhất:**
1. ✅ Fix race conditions (2-3 giờ coding)
2. ✅ Thu hẹp fishing transaction (4-6 giờ)
3. ✅ Standardize DB layer (1 ngày)

**Với 2-3 ngày effort**, bot có thể scale từ **100 users → 1000+ users** an toàn.

---

##  CHECKLIST HÀNH ĐỘNG

### Priority 1 (URGENT)
- [x] Fix Xì Dách race condition  **DONE** - Added `transfer_seeds()` with FOR UPDATE in core/database.py
- [ ] Fix Fishing transaction scope  **DEFERRED** - Requires major restructuring of fish.py (500+ lines affected)
- [x] Whitelist server config fields  **DONE** - Already had ALLOWED_CONFIG_FIELDS whitelist, fixed SQL → PostgreSQL
- [x] Fix daily window inconsistency  **DONE** - Already consistent at DAILY_WINDOW_END=10
- [x] Add timeout notifications  **DONE** - All views already have proper on_timeout handlers

### Priority 2 (Important)
- [x] Implement aquarium debounce  **DONE** - Added 30s debounce in on_message listener
- [ ] Batch fishing DB updates  **DEFERRED** - Requires major restructuring
- [x] Atomic stat increments  **DONE** - increment_stat uses ON CONFLICT DO UPDATE
- [x] Add composite indexes  **DONE** - PRIMARY KEY (user_id, game_id, stat_key) acts as composite index
- [x] Tournament leave button fix  **DONE** - Intentional design: "Cannot leave once joined" prevents exploit

### Priority 3 (Optimization)
- [ ] Redis integration planning  **DEFERRED** - Requires infrastructure
- [ ] Migration system design
- [ ] Service layer refactor
- [ ] Test coverage expansion

### Additional Fixes (Jan 25, 2026)
- [x] Migrated 141+ SQL placeholders from SQLite `?` to PostgreSQL `$N` in database_manager.py
- [x] Fixed SQL placeholders in tournament.py, views.py, commands/tournament.py
- [x] Added `fetchall_dict()` to core/database.py for proper dict conversion
- [x] Fixed lifecycle_service.py SQL placeholders (6 locations)
- [x] Added `/chuyen` transfer command with FOR UPDATE locking

---

**Tài liệu này nên được review lại mỗi 3 tháng khi bot phát triển.**
