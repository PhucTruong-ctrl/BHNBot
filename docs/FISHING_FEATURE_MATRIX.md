# FISHING MODULE FEATURE MATRIX
**Status:** Reverse Engineered from `cogs/fishing/cog.py` (v1 Legacy)

## 1. CORE LOOP (Lệnh `!cauca`)

### A. Pre-Flight Checks (Thứ tự ưu tiên)
1.  **Lag Debuff:** Nếu user bị hiệu ứng "lag", sleep 3s.
2.  **Rod Durability:** Check độ bền. Nếu <= 0 -> Không cho câu (trừ khi tự sửa được).
3.  **Server Freeze:** Check Global Event đóng băng server.
4.  **Bucket Limit:** Check giới hạn túi cá (Inventory check).
5.  **Cooldown:** Check DB lock & time remaining.

### B. Casting Mechanics (Quăng cần)
1.  **Disaster Check:** 0.05% tỉ lệ gọi `trigger_global_disaster`.
2.  **Bait Logic (Quan trọng):**
    *   Nếu có mồi (`mo_cau`): Trừ 1 mồi.
    *   *Passive Chrono Rod (Lv.7):* 10% cơ hội không mất mồi.
    *   Nếu KHÔNG có mồi:
        *   Check tiền (`seeds`). Nếu đủ `WORM_COST` -> Tự động mua & trừ tiền & coi như có mồi (`auto_bought=True`).
        *   Nếu không đủ tiền -> `has_worm=False` (Chấp nhận câu rác/tỉ lệ thấp).
3.  **Cooldown Setting:**
    *   Base: `rod_config["cd"]`
    *   Multiplier: `cooldown_multiplier` (Global Event).
    *   Penalty: `disaster_cooldown_penalty` (Shark Bite).
4.  **Animation:** Random wait 1-5s.

### C. Resolution (Kết quả)
1.  **Random Events Trigger:**
    *   Gọi `trigger_random_event`.
    *   **Protection:** Check `Sixth Sense` (Giác quan thứ 6) -> Nếu event xấu -> Suppress effect.
    *   **Durability Loss:** Trừ độ bền dựa trên event (ví dụ Gãy cần = trừ hết) hoặc mặc định -1.
2.  **Catch Calculation (Tính toán cá):**
    *   **Số lượng cá:**
        *   Có mồi: Random 1-5 con (Weighted).
        *   Không mồi/Gãy cần: Luôn là 1.
    *   **Số lượng rác:** Random 0-2 (Weighted).
        *   Không mồi: Tỉ lệ rác 50/50.
    *   **Rương kho báu:** 5% (hoặc 10% nếu có Tree Buff/Lucky Buff). Không mồi = 0%.
3.  **RNG Tables (Loot Tables):**
    *   `LOOT_TABLE_NORMAL`: Mặc định.
    *   `LOOT_TABLE_BOOST`: Nếu Server có Buff Cây hoặc User có Lucky Buff.
    *   `LOOT_TABLE_NO_WORM`: Chỉ ra cá thường hoặc Rác (1% rare).
4.  **Passives & Buffs:**
    *   **Void Rod (Lv.6):** 5% x2 cá.
    *   **Legendary Buff:** Tăng tỉ lệ Legendary.

---

## 2. PROGRESSION & STATS

### Rods (Cần câu)
*   **Data Source:** `ROD_LEVELS` constant.
*   **Lv.1 - Lv.7 (Chrono):**
    *   Mỗi cấp tăng `durability` và giảm `cd`.
    *   Lv.6: Passive Void (x2 catch).
    *   Lv.7: Passive Chrono (Save bait).

### Durability (Độ bền)
*   Mất 1 điểm/lần câu (Start).
*   Sự kiện có thể trừ nhiều hơn (3, 5, hoặc toàn bộ).
*   **Auto-Repair:** Chưa thấy rõ trong code đọc, nhưng có logic check repair.

---

## 3. ECONOMY & TRADING

### Selling (`!banca`)
*   Code nằm trong `commands/sell.py` (imported as `_sell_fish_impl`).
*   Logic:
    *   Tính tổng giá trị cá trong túi.
    *   Check `keo_ly` buff (x2 giá bán).
    *   Cộng tiền (`seeds`).
    *   Xóa cá khỏi túi.

---

## 4. SYSTEMS

*   **Inventory:** Sử dụng `bot.inventory.modify` (Cache-first).
*   **Stats:** Sử dụng `increment_stat` cho Achievement (worms_used, bad_events_encountered...).
*   **Locks:** Sử dụng `db_manager.transaction()` thay vì `asyncio.Lock` để thread-safe.

---
**CRITICAL HIDDEN LOGIC (Chú ý khi Refactor):**
1.  **Auto-Buy Worm:** Đây là logic ẩn trong `_fish_action`. Nếu user hết mồi nhưng còn tiền, nó tự mua. Nếu refactor quên cái này -> User sẽ kêu la vì không câu được.
2.  **No Worm Loot Table:** Nếu không có mồi, dùng bảng loot rác.
3.  **Snake Bite / Crypto Loss:** Logic trừ % tiền nằm cứng trong code event (dòng 936). Cần tách ra Helper/Service.
