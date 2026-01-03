# ESTIMATION: 4 PHASES (2-3 Days)

This plan outlines the migration of Project Aquarium from Legacy (SQLite) to Main (Postgres/MVC).

---

## phase_0_infrastructure.md (PostgreSQL Setup)

**Objective:** Install and configure PostgreSQL, prepare Python environment.
**Status:** **✅ COMPLETE**

### Tasks:
1.  [ ] **Install PostgreSQL**:
    *   Command: `sudo apt install postgresql postgresql-contrib`
    *   Service: Ensure active (`systemctl status postgresql`).
2.  [ ] **Database Setup**:
    *   Create User: `bhnbot_user`
    *   Create DB: `bhnbot_db`
    *   Grant Permissions.
3.  [ ] **Python Dependencies**:
    *   Install `asyncpg` (Async Driver).
    *   Install `tortoise-orm` (Optional, if using ORM approach).
4.  [ ] **Configuration**:
    *   Create `.env` file with `DATABASE_URL=postgres://user:pass@localhost/bhnbot_db`.

---

## phase_1_foundation.md (Database Schema)

**Objective:** design the Postgres schema using Tortoise ORM (or raw asyncpg if project standard).
**Legacy Files:** `setup_data.py` (Lines 9907-10005 in diff).

### New Files to Create:
1.  **`cogs/aquarium/models.py`**
    *   Define `UserAquarium` (extends User or OneToOne).
        *   `leaf_coin` (BigInt).
        *   `charm_point` (Int).
        *   `home_thread_id` (BigInt, Nullable).
    *   Define `HomeSlot` model.
        *   `user_id` (FK).
        *   `slot_index` (Int, 0-4).
        *   `item_id` (String).
        *   `placed_at` (Datetime).
        *   *Constraint:* Unique(user_id, slot_index).
    *   Define `UserDecor` model.
        *   `user_id` (FK).
        *   `item_id` (String).
        *   `quantity` (Int).
    *   Define `HomeVisit` model.
        *   `visitor_id` (FK).
        *   `host_id` (FK).
        *   `visited_at` (Datetime).
    *   Define `VIPSubscription` model.
        *   `user_id` (PK).
        *   `tier_level` (Int).
        *   `expiry_date` (Datetime).
        *   `auto_renew` await (Boolean).

### Tasks:
*   [ ] Create `models.py`.
*   [ ] Create migration script (or `aerich` init).
*   [ ] Verify Relationship integrity (Foreign Keys).

---

## phase_2_core_logic.md (Pure Python)

**Objective:** Port business logic, decoupling it from `discord.Context`.
**Legacy Files:** `cogs/aquarium/core/housing.py`, `cogs/aquarium/core/economy.py`, `cogs/aquarium/core/vip.py`, `cogs/aquarium/core/shop.py`.

### New Files to Create:
1.  **`cogs/aquarium/logic/housing.py`**
    *   `HousingEngine` class.
    *   Methods: `get_slots(user_id)`, `update_slot(...)`, `calculate_charm(...)`.
2.  **`cogs/aquarium/logic/market.py`**
    *   `MarketEngine` class.
    *   Methods: `buy_decor(...)`, `recycle_trash(...)`.
3.  **`cogs/aquarium/logic/vip.py`**
    *   `VIPEngine` class.
    *   Methods: `check_subscription(...)`, `apply_perks(...)`.
4.  **`cogs/aquarium/logic/render.py`**
    *   Port the ASCII rendering logic from `ui/render.py`.
    *   *Optimization:* Cache render results?

### Tasks:
*   [ ] Port Logic functions.
*   [ ] Replace `sqlite3` calls with ORM/asyncpg calls.
*   [ ] Add Type Hinting (Strict).

---

## phase_3_user_interface.md (Views & Embeds)

**Objective:** Modernize UI using `discord.ui`.
**Legacy Files:** `cogs/aquarium/ui/views.py`, `cogs/aquarium/ui/embeds.py`.

### New Files to Create:
1.  **`cogs/aquarium/ui/menus.py`**
    *   `DecorShopView(Paginator)`.
    *   `DecorPlacementView`.
    *   `VIPSubscriptionView`.
2.  **`cogs/aquarium/ui/display.py`**
    *   `create_dashboard_embed(...)`.
    *   `create_shop_embed(...)`.

### Tasks:
*   [ ] Implement View classes.
*   [ ] Fix Button callbacks (connect to Logic from Phase 2).
*   [ ] Ensure "Chill Vibe" texts (Vietnamese).

---

## phase_4_controllers.md (Wiring)

**Objective:** Wire everything into the Bot.
**Legacy Files:** `cogs/aquarium/cog.py`.

### New Files to Create:
1.  **`cogs/aquarium/cog.py`**
    *   Register Slash Commands: `/nha`, `/trangtri`, `/thamnha`, `/thuongluu`.
    *   Register Prefix Commands (optional/legacy support).
2.  **`cogs/aquarium/__init__.py`**
    *   Setup function.

### Tasks:
*   [ ] Inject Dependencies (Logic Engines).
*   [ ] Error Handling Wrappers.
*   [ ] Permission Checks.
