# TECHNICAL DESIGN DOCUMENT: PROJECT AQUARIUM (SYMBIOSIS)

**Version:** 1.0.0
**Status:** Implemented (Audit Phase)
**Author:** Lead System Architect (Antigravity)

---

## 1. RECAP & AUDIT

### 1.1 Context
We are shifting from a purely "Extract & Gamble" economy (Fishing -> Seeds -> Bầu Cua) to a closed-loop "Symbiosis" economy.
*   **Problem:** Trash items (`rac`, `chai_nhua`, etc.) accumulate with zero value. Inflation is high due to lack of sinks.
*   **Solution:** Convert Trash into **Decor** (Sink for Seeds + Trash). Decor generates **Charm**. Charm generates **Status**.

### 1.2 Resource Audit
*   **Source (Trash):**
    *   `misc.json` contains generic trash. 
    *   **Current Sink:** None (User typically accidentally sells or hoards).
    *   **New Sink:** Recycling Center (`/taiche`) -> Converts 1 Trash to 1 Leaf Coin.
*   **Currency (Leaf Coins):**
    *   Secondary currency stored in `users` table.
    *   **Constraint:** Cannot be transferred (Soulbound) to prevent alt-farming.

### 1.3 Tech Stack Status
*   ✅ **Database:** SQLite (aiosqlite) in `setup_data.py`. Tables `user_house`, `home_slots` created.
*   ✅ **Engine:** `HousingManager` (`cogs/aquarium/core/housing.py`) handles logic.
*   ✅ **Render:** ASCII Grid System (`cogs/aquarium/ui/render.py`) implemented.
*   ✅ **UI:** `discord.ui.View` for Shop and Placement implemented.

---

## 2. DATABASE SCHEMA DESIGN

This schema is designed for **High Performance** (indexed lookups) and **Data Integrity** (Foreign Keys).

### 2.1 Core Tables

#### `users` (Extension)
Added columns to the core user table to track broad stats.
```sql
ALTER TABLE users ADD COLUMN leaf_coin INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN charm_point INTEGER DEFAULT 0; -- Social Score
ALTER TABLE users ADD COLUMN home_thread_id INTEGER DEFAULT NULL; -- Discord Thread ID
```

#### `user_house` (Housing State)
Stores the meta-data of the house itself.
```sql
CREATE TABLE IF NOT EXISTS user_house (
    user_id INTEGER PRIMARY KEY,
    thread_id INTEGER, -- The Forum Thread ID
    house_level INTEGER DEFAULT 1, -- For future expansion (more slots)
    cleanliness INTEGER DEFAULT 100, -- Potential for "Cleaning" mechanic
    dashboard_message_id INTEGER, -- To support Smart Bump (Edit instead of Resend)
    slots_unlocked INTEGER DEFAULT 5
);
```

#### `home_slots` (Placement)
Relational structure (Normalized) preferred over JSON for easier querying of "Who has item X?".
```sql
CREATE TABLE IF NOT EXISTS home_slots (
    user_id INTEGER,
    slot_index INTEGER, -- 0 to 4
    item_id TEXT, -- Key from DECOR_ITEMS
    PRIMARY KEY (user_id, slot_index)
);
```

#### `user_decor` (Inventory)
Separate from main fishing inventory to avoid clutter.
```sql
CREATE TABLE IF NOT EXISTS user_decor (
    user_id INTEGER,
    item_id TEXT,
    quantity INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, item_id)
);
```

#### `home_visits` (Anti-Abuse)
Tracks daily visits to limit rewards.
```sql
CREATE TABLE IF NOT EXISTS home_visits (
    visitor_id INTEGER,
    host_id INTEGER,
    visited_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Index for fast "Count today's visits"
CREATE INDEX idx_visit_date ON home_visits(visitor_id, date(visited_at));
```

---

## 3. LOGIC MECHANICS

### 3.1 Recycling (`AquariumEconomy.process_checklist_recycle`)
*   **Formula:** `Total Leaf Coins = (Trash Count * 1) * (1 + Streak Bonus)`
*   **Streak Bonus:** +10% if user recycled yesterday.
*   **Input:** Check specific Trash IDs defined in `constants.TRASH_ITEM_IDS`.
*   **Anti-Inflation:** Leaf Coins are only generated from active fishing (Trash), not passive income.

### 3.2 Charm Calculation (`HousingManager.calculate_home_stats`)
*   **Base Charm:** Sum of `charm` value of all placed items.
*   **Set Bonus (`FENG_SHUI_SETS`):**
    *   If user has `{A, B, C, D}` in *any* slot -> Active Bonus.
    *   **Implementation:** `set(placed_items).issubset(required_items)`.

### 3.3 ASCII Render Engine (`render_engine.generate_view`)
Mapping abstract Slot IDs to a visual grid string.

**Grid Layout (3x5):**
```text
[0][1][2][3][4] -> Top (Surface/Sky)
[5][6][7][8][9] -> Mid (Water Column)
[A][B][C][D][E] -> Bot (Floor/Sand)
```

**Slot Mapping Strategy:**
*   **Slot 1 (Left):** Mid-Water or Floor? -> Assigned to `(2, 1)` (Floor Left).
*   **Slot 2 (Top):** Surface -> Assigned to `(1, 2)` (Mid Floating).
*   **Slot 3 (Center):** The Centerpiece -> Assigned to `(2, 2)` (Floor Center).
*   **Slot 4 (Right):** Mid-Water -> Assigned to `(2, 3)` (Floor Right).
*   **Slot 5 (Far):** Corner -> Assigned to `(2, 4)` (Floor Far Right).

**Pseudo-Code:**
```python
def render(slots):
    grid = create_empty_grid(3, 5, "🟦") # Blue Background
    
    for slot_idx, item_id in enumerate(slots):
        item = get_item_data(item_id)
        # Determine strict position based on item type (floor vs float)
        # OR hardcode slot positions for simplicity (Current Approach)
        x, y = SLOT_COORDINATES[slot_idx] 
        grid[y][x] = item.icon
        
    return stringify(grid)
```

---

## 4. UI/UX FLOW

### 4.1 Creating Home (`/nha khoitao`)
1.  **Check DB:** `HousingManager.has_house(user_id)`.
2.  **Verify:** If exists -> Error "Nhà đã có rồi".
3.  **Action:**
    *   Create Discord Thread in Forum Channel.
    *   Insert `user_house`, `users.home_thread_id`.
    *   Initialize `home_slots` with NULL.
4.  **Feedback:** Reply with Link to Thread.

### 4.2 Decorating (`/trangtri sapxep`)
1.  **View:** `DecorPlacementView`.
2.  **Components:**
    *   **Dropdown 1 (Slot):** Select Slot 1-5.
    *   **Dropdown 2 (Inventory):** Show available items in `user_decor` + Option "Empty Slot".
    *   **Button (Save):** Commit changes to Forum Thread.
3.  **Interaction:**
    *   Select Slot -> Update View State.
    *   Select Item -> Call `HousingManager.update_slot` (Swap old item back to inventory, take new item).
    *   Click Save -> `HousingManager.refresh_dashboard` (Edit Thread Message).

### 4.3 Social Visit (`/thamnha`)
1.  **Check Limit:** Count `home_visits` for visitor today. Max 5.
2.  **RNG:** 20% Chance.
    *   **Reward:** 1 Leaf Coin (1%) or 1 Trash Item (19%).
3.  **Host Benefit:** `UPDATE users SET charm_point = charm_point + 1`.
4.  **Display:** Show Host's Dashboard Embed to Visitor.

---

## 5. IMPLEMENTATION STRUCTURE (Modular Architecture)

### Directory: `cogs/aquarium/`
*   `cog.py`: **Controller**. Registers `/nha`, `/trangtri`, `/thamnha`. Check permissions/inputs.
*   `constants.py`: **Config**. Definitions of `DECOR_ITEMS`, `FENG_SHUI_SETS`, `TRASH_ITEM_IDS`.
*   `core/`: **Business Logic (Model)**
    *   `housing.py`: `HousingManager` class (DB operations, Stats calc).
    *   `economy.py`: `AquariumEconomy` class (Recycle logic).
    *   `shop.py`: `AquariumShop` class (Buying logic).
*   `ui/`: **Presentation (View)**
    *   `views.py`: `DecorShopView`, `DecorPlacementView`.
    *   `embeds.py`: `create_aquarium_dashboard` factory.
    *   `render.py`: ASCII Grid Engine.

### 6. ROADMAP (Status)
1.  **Database & Schema**: ✅ Done.
2.  **Core Logic (Housing/Econ/Shop)**: ✅ Done.
3.  **Commands & UI**: ✅ Done (`/nha`, `/trangtri`, `/thamnha`).
4.  **Next Step**: **VIP System** (Phase 2.4).
    *   `cogs/aquarium/core/vip.py` (Subscription Logic).
    *   `cogs/config.py` (Middleware for Chat Color).
