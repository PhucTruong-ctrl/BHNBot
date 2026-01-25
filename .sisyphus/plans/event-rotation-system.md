# Event Content Rotation System - Complete Work Plan (v4)

## Context

### Original Request
User muốn seasonal events cảm thấy **mới mẻ mỗi năm** mà không cần viết lại code/content thủ công.

**Approach đã chọn:** Hybrid: Pool + Yearly Exclusives

### Key Clarifications (v4 Update)

1. **Seasonal fish max tier = EPIC** (không có Legendary trong seasonal events)
2. **Legendary fish = hệ thống riêng** trong fishing core, quest-triggered, KHÔNG rotate
3. **8 events** cần support, không chỉ Halloween
4. **Yearly exclusive = 1 Epic fish + 1 cosmetic + 1 title** (không phải Legendary)
5. **Assets cần year-based naming** để không overwrite mỗi năm (v4 NEW)

---

## All 8 Events Overview

### Event Inventory

| Event | Type | Current Fish | Minigames | Pool Needed |
|-------|------|--------------|-----------|-------------|
| **Spring** (Lễ Hội Hoa Xuân) | major | 7 (3c/3r/1e) | lixi_auto, lixi_manual |  |
| **Summer** (Lễ Hội Biển) | major | 7 (3c/3r/1e) | treasure_hunt, boat_race |  |
| **Autumn** (Thu Hoạch Mùa Thu) | major | 7 (3c/3r/1e) | thank_letter, leaf_collect, tea_brewing |  |
| **Winter** (Đông Ấm Áp) | major | 7 (3c/3r/1e) | secret_santa, snowman, countdown |  |
| **Halloween** | mini | 5 (2c/2r/1e) | ghost_hunt, trick_treat |  |
| **Mid-Autumn** (Trung Thu) | mini | 4 (2c/2r/0e) | lantern_parade, quiz |  |
| **Earth Day** | mini | 4 (2c/1r/1e) | trash_sort, beach_cleanup |  |
| **Birthday** | mini | 0 fish | wishes, balloon_pop | Shop only |

### Tier Distribution per Event Type

| Event Type | Common | Rare | Epic | Yearly Exclusive |
|------------|--------|------|------|------------------|
| **Major** (4 events) | 3-4 | 2-3 | 1 | +1 Epic |
| **Mini** (3 fish events) | 2 | 1-2 | 0-1 | +1 Epic |
| **Birthday** | 0 | 0 | 0 | Shop only |

---

## Legendary Fish System (SEPARATE - DO NOT ROTATE)

### Current Legendary Fish (cogs/fishing/mechanics/)

| Fish | Condition | Quest Trigger | Spawn % |
|------|-----------|---------------|---------|
| **Thuồng Luồng** | river_storm | /hiente sacrifice 3 fish | 1% |
| **Cá Ngân Hà** | clear_night (0-4h) | Galaxy minigame + bait | 0.8% |
| **Cá Phượng Hoàng** | noon_sun (12-14h) | Egg-hatching prep | 0.8% |
| **Cthulhu Non** | deep_sea | 4 map pieces + 10 casts | 100% (guaranteed) |
| **Cá Voi 52Hz** | silence | /dosong + item | 0.05% |
| **Cá Isekai** | null | UNOBTAINABLE | 0% |

### Mechanics
- Quest-triggered encounters (không random pool)
- Interactive boss fight (60s) với 3 choices
- Tracked trong `legendary_quests` table
- Multiplied by `legendary_chance_bonus` từ Aquarium

### Policy
- **KHÔNG rotate** legendary fish
- Có thể **thêm mới** legendary fish mỗi năm (với quest mới)
- Legendary fish là **permanent content**, không liên quan seasonal events

---

## Assets Management (v4 NEW)

### Current Asset Structure (PROBLEMS)

```
assets/
├── frames/
│   ├── frame_autumn.png      ← NO year suffix = overwritten each year
│   ├── frame_birthday.png
│   ├── frame_earthday.png
│   ├── frame_halloween.png
│   ├── frame_midautumn.png
│   ├── frame_spring.png
│   ├── frame_summer.png
│   └── frame_winter.png
│
└── profile/
    ├── bg_autumn.png         ← NO year suffix
    ├── bg_birthday.png
    ├── bg_earthday.png
    ├── bg_halloween.png
    ├── bg_midatumn.png       ← TYPO: should be bg_midautumn.png
    ├── bg_spring.png
    ├── bg_summer.png
    ├── bg_winter.png
    │
    ├── bg_cabin.png          ← STATIC (keep as-is)
    ├── bg_forest.png
    ├── bg_ocean.png
    ├── bg_starry.png
    └── bg_sunrise.png
```

### CRITICAL ISSUES FOUND

| Issue | Impact | Priority |
|-------|--------|----------|
| **No year suffix on assets** | New assets overwrite old |  CRITICAL |
| **Frame rendering NOT IMPLEMENTED** | Users buy but can't see |  CRITICAL |
| **Seasonal bg NOT in THEMES dict** | Defaults to 'forest' |  HIGH |
| **Typo: bg_midatumn.png** | Inconsistent naming |  LOW |

### Target Asset Structure (YEAR-BASED)

```
assets/
├── frames/
│   ├── frame_halloween_2025.png    # Renamed from current
│   ├── frame_halloween_2026.png    # NEW yearly exclusive
│   ├── frame_spring_2025.png
│   ├── frame_spring_2026.png
│   └── ... (per event, per year)
│
└── profile/
    ├── bg_halloween_2025.png       # Renamed from current
    ├── bg_halloween_2026.png       # NEW yearly exclusive
    ├── bg_spring_2025.png
    ├── bg_spring_2026.png
    │
    ├── bg_cabin.png                # STATIC - unchanged
    ├── bg_forest.png
    ├── bg_ocean.png
    ├── bg_starry.png
    └── bg_sunrise.png
```

### Asset Migration Checklist (ONE-TIME)

**Step 1: Rename existing assets to 2025 (assumed first year)**

| Current File | Rename To |
|--------------|-----------|
| `frames/frame_halloween.png` | `frames/frame_halloween_2025.png` |
| `frames/frame_spring.png` | `frames/frame_spring_2025.png` |
| `frames/frame_summer.png` | `frames/frame_summer_2025.png` |
| `frames/frame_autumn.png` | `frames/frame_autumn_2025.png` |
| `frames/frame_winter.png` | `frames/frame_winter_2025.png` |
| `frames/frame_midautumn.png` | `frames/frame_midautumn_2025.png` |
| `frames/frame_earthday.png` | `frames/frame_earthday_2025.png` |
| `frames/frame_birthday.png` | `frames/frame_birthday_2025.png` |
| `profile/bg_halloween.png` | `profile/bg_halloween_2025.png` |
| `profile/bg_spring.png` | `profile/bg_spring_2025.png` |
| `profile/bg_summer.png` | `profile/bg_summer_2025.png` |
| `profile/bg_autumn.png` | `profile/bg_autumn_2025.png` |
| `profile/bg_winter.png` | `profile/bg_winter_2025.png` |
| `profile/bg_midatumn.png` | `profile/bg_midautumn_2025.png` (fix typo!) |
| `profile/bg_earthday.png` | `profile/bg_earthday_2025.png` |
| `profile/bg_birthday.png` | `profile/bg_birthday_2025.png` |

**Step 2: Update JSON configs to use year-based keys**

| Current Key | New Key |
|-------------|---------|
| `bg_halloween` | `bg_halloween_2025` |
| `frame_halloween` | `frame_halloween_2025` |
| ... | ... |

**Step 3: Database migration for existing purchases**

```sql
UPDATE event_shop_purchases 
SET item_key = item_key || '_2025' 
WHERE item_key IN ('bg_halloween', 'frame_halloween', ...);
```

### Yearly Asset Creation Checklist

**For each event, each year, you need:**

```markdown
## [Event] [Year] Assets Needed

### Frame (1 required)
- [ ] `assets/frames/frame_{event}_{year}.png`
- Dimensions: 800x1000 (match existing frames)
- Format: PNG with transparency
- Style: Match event theme

### Background (1 required)  
- [ ] `assets/profile/bg_{event}_{year}.png`
- Dimensions: 800x600 (match existing backgrounds)
- Format: PNG or JPG
- Style: Match event theme

### Shop Item Config (in exclusives/{year}.json)
```json
{
  "exclusive_cosmetic": {
    "key": "frame_{event}_{year}",  // or bg_{event}_{year}
    "name": "Khung [Event Name] {year}",
    "type": "frame",  // or "background"
    "price": 500,
    "limit_per_user": 1,
    "asset_path": "frames/frame_{event}_{year}.png"
  }
}
```
```

### 2026 Assets Needed (User Action Required)

**Frames to create:**

| Event | Asset Path | Status |
|-------|------------|--------|
| Halloween | `frames/frame_halloween_2026.png` | ❌ NEEDED |
| Spring | `frames/frame_spring_2026.png` | ❌ NEEDED |
| Summer | `frames/frame_summer_2026.png` | ❌ NEEDED |
| Autumn | `frames/frame_autumn_2026.png` | ❌ NEEDED |
| Winter | `frames/frame_winter_2026.png` | ❌ NEEDED |
| Mid-Autumn | `frames/frame_midautumn_2026.png` | ❌ NEEDED |
| Earth Day | `frames/frame_earthday_2026.png` | ❌ NEEDED |
| Birthday | `frames/frame_birthday_2026.png` | ❌ NEEDED |

**Backgrounds to create:**

| Event | Asset Path | Status |
|-------|------------|--------|
| Halloween | `profile/bg_halloween_2026.png` | ❌ NEEDED |
| Spring | `profile/bg_spring_2026.png` | ❌ NEEDED |
| Summer | `profile/bg_summer_2026.png` | ❌ NEEDED |
| Autumn | `profile/bg_autumn_2026.png` | ❌ NEEDED |
| Winter | `profile/bg_winter_2026.png` | ❌ NEEDED |
| Mid-Autumn | `profile/bg_midautumn_2026.png` | ❌ NEEDED |
| Earth Day | `profile/bg_earthday_2026.png` | ❌ NEEDED |
| Birthday | `profile/bg_birthday_2026.png` | ❌ NEEDED |

---

## Work Objectives

### Core Objective
Implement hệ thống content rotation cho **tất cả 8 seasonal events** với:
- Pool-based selection (max tier = Epic)
- Anti-duplicate logic (2-year cooldown)
- Yearly exclusive items (1 Epic fish + 1 cosmetic + 1 title)
- History tracking for reproducibility
- **Year-based asset naming** (v4 NEW)

### Concrete Deliverables
1. ✅ Fixed drop_rate bug in event_fish_hook.py
2. ✅ `event_content_history` database table
3. Pool JSON files cho **8 events** (không chỉ Halloween)
4. `ContentRotationService` class
5. Updated `EventManager` to use rotation
6. Yearly exclusive loading mechanism
7. CLI tool for generating yearly configs
8. **Asset migration script** (v4 NEW)
9. **Frame renderer implementation** (v4 NEW)

### Definition of Done
- [ ] `pytest tests/seasonal/test_rotation*.py -v` → ALL PASS
- [ ] Mỗi event có pool.json với đủ items
- [ ] Yearly exclusive (Epic tier) appears với badge
- [ ] **Assets have year suffix** (v4 NEW)
- [ ] **Frames render correctly on profiles** (v4 NEW)

### Must Have
- Seed-based RNG cho reproducibility
- **Tier balance: 1 epic, 2 rare, 2-4 common** (NO legendary)
- History tracking to prevent recent repeats
- Fallback to static config when no pool exists
- **Year-based asset paths** (v4 NEW)

### Must NOT Have (Guardrails)
- KHÔNG thêm legendary fish vào seasonal events
- KHÔNG modify legendary quest system
- KHÔNG break existing events without pools
- KHÔNG change user-facing commands
- **KHÔNG overwrite existing assets without year suffix** (v4 NEW)

---

## Per-Event Pool Strategy

### Major Events (4 events)

| Component | Strategy | Pool Size | Per Year | Cooldown |
|-----------|----------|-----------|----------|----------|
| **Fish (Epic)** | Rotating Pool | 6-8 | 1 | 2 years |
| **Fish (Rare)** | Rotating Pool | 10-12 | 2-3 | 2 years |
| **Fish (Common)** | Rotating Pool | 12-15 | 3-4 | 1 year |
| **Yearly Exclusive (Epic)** | Manual Creation | 1/year | 1 | Forever |
| **Shop (Cosmetics)** | Yearly Exclusive | 1-2/year | 1-2 | Forever |
| **Shop (Consumables)** | Rotating Pool | 8-10 | 3-4 | 1 year |
| **Daily Quests** | Rotating Pool | 12-15 | 2-3/day | 3 days |

### Mini Events (3 fish events)

| Component | Strategy | Pool Size | Per Year | Cooldown |
|-----------|----------|-----------|----------|----------|
| **Fish (Epic)** | Optional | 3-4 | 0-1 | 2 years |
| **Fish (Rare)** | Rotating Pool | 6-8 | 1-2 | 2 years |
| **Fish (Common)** | Rotating Pool | 6-8 | 2 | 1 year |
| **Yearly Exclusive (Epic)** | Manual Creation | 1/year | 1 | Forever |
| **Shop** | Same as major | - | - | - |

### Birthday Event (no fish)

| Component | Strategy | Pool Size | Per Year |
|-----------|----------|-----------|----------|
| **Shop (Cosmetics)** | Yearly Exclusive | 1/year | 1 |
| **Shop (Consumables)** | Rotating Pool | 5-8 | 3-4 |
| **Minigame Rewards** | Rotating | 3-5 | 2-3 |

---

## Directory Structure (All 8 Events)

```
data/events/
├── registry.json              # Event registry (existing)
├── halloween.json             # Static config (existing, fallback)
├── spring.json
├── summer.json
├── autumn.json
├── winter.json
├── mid_autumn.json
├── earth_day.json
├── birthday.json
│
└── pools/                     # NEW - Pool system
    ├── _template/             # Template for new events
    │   ├── pool.json
    │   └── exclusives/
    │       └── YYYY.json
    │
    ├── halloween/
    │   ├── pool.json          # All rotatable content
    │   └── exclusives/
    │       ├── 2025.json      # Past exclusive (for reference)
    │       └── 2026.json      # Current year exclusive
    │
    ├── spring/
    │   ├── pool.json
    │   └── exclusives/
    │       └── 2026.json
    │
    ├── summer/
    │   ├── pool.json
    │   └── exclusives/
    │       └── 2026.json
    │
    ├── autumn/
    │   ├── pool.json
    │   └── exclusives/
    │       └── 2026.json
    │
    ├── winter/
    │   ├── pool.json
    │   └── exclusives/
    │       └── 2026.json
    │
    ├── mid_autumn/
    │   ├── pool.json
    │   └── exclusives/
    │       └── 2026.json
    │
    ├── earth_day/
    │   ├── pool.json
    │   └── exclusives/
    │       └── 2026.json
    │
    └── birthday/
        ├── pool.json          # Shop items only
        └── exclusives/
            └── 2026.json      # Shop exclusive only
```

---

## Yearly Asset Checklist (Per Event)

### For Events WITH Fish (7 events)

```markdown
## [Event Name] [Year] Asset Checklist

### Required ASSETS (Before Event Start)
- [ ] `assets/frames/frame_{event}_{year}.png` (800x1000, PNG with transparency)
- [ ] `assets/profile/bg_{event}_{year}.png` (800x600, PNG/JPG)

### Required CONFIG (exclusives/{year}.json)
- [ ] 1 Exclusive Epic Fish
  - key: `{event}_exclusive_{year}` (e.g., halloween_exclusive_2027)
  - name: Vietnamese name
  - emoji: Custom or Unicode
  - tier: "epic"  ← NOT legendary!
  - drop_rate: 0.02-0.05
  - currency_reward: [80, 150]
  - is_exclusive: true
   
- [ ] 1 Exclusive Cosmetic
  - key: `frame_{event}_{year}` OR `bg_{event}_{year}`
  - asset_path: path to the PNG file
  - price: 400-600 event currency
  - limit_per_user: 1

- [ ] 1 Exclusive Title
  - key: `title_{event}_{year}`
  - name: "[Emoji] Tên Title [Year]"

- [ ] Fixed Quest for Exclusive
  - "Bắt được [Tên Cá Exclusive] 1 lần"
  - reward: Exclusive title

### Auto-Selected from Pools
- Common/Rare/Epic fish (from pool, 2-year cooldown)
- Daily quests (from pool, 3-day cooldown)
- Consumable shop items (from pool)
- Minigame difficulty preset (easy/normal/hard rotation)
```

### For Birthday Event (No Fish)

```markdown
## Birthday [Year] Asset Checklist

### Required ASSETS
- [ ] `assets/frames/frame_birthday_{year}.png`
- [ ] `assets/profile/bg_birthday_{year}.png`

### Required CONFIG
- [ ] 1 Exclusive Cosmetic (frame or background)
- [ ] 1 Exclusive Title

### Auto-Selected from Pools
- Consumable shop items
- Minigame reward values
```

---

## Technical Specifications

### 1. Pool JSON Schema (Updated for All Events)

**File:** `data/events/pools/{event_type}/pool.json`

```json
{
  "event_type": "halloween",
  "pool_version": 1,
  "last_updated": "2026-01-25",
  
  "fish_pool": [
    {
      "key": "ghost_fish",
      "name": "Cá Ma",
      "emoji": "👻",
      "tier": "common",
      "base_drop_rate": 0.35,
      "currency_reward": [5, 15],
      "introduced_year": 2024,
      "is_exclusive": false
    },
    {
      "key": "vampire_carp",
      "name": "Cá Chép Ma Cà Rồng", 
      "emoji": "🧛",
      "tier": "rare",
      "base_drop_rate": 0.12,
      "currency_reward": [15, 30],
      "introduced_year": 2024,
      "is_exclusive": false
    },
    {
      "key": "pumpkin_king",
      "name": "Cá Bí Ngô Vương",
      "emoji": "🎃",
      "tier": "epic",
      "base_drop_rate": 0.03,
      "currency_reward": [40, 70],
      "introduced_year": 2025,
      "is_exclusive": false
    }
  ],
  
  "shop_pool": [
    {
      "key": "spooky_bait",
      "name": "Mồi Ma Quái",
      "type": "consumable",
      "price": 50,
      "limit_per_user": 10,
      "effect": {"catch_rate_bonus": 0.1, "duration_hours": 1}
    }
  ],
  
  "quest_pool": [
    {
      "id": "catch_ghost_fish_5",
      "type": "catch_event_fish",
      "target": 5,
      "reward_value": 30,
      "description": "Bắt 5 con cá sự kiện",
      "icon": "🎣"
    }
  ],
  
  "tier_requirements": {
    "fish": {"epic": 1, "rare": 2, "common": 2},
    "shop": {"consumable": 3}
  },
  
  "difficulty_presets": {
    "easy": {
      "minigame_times_per_day": [8, 12],
      "minigame_reward_multiplier": 0.8,
      "minigame_timeout_seconds": 45
    },
    "normal": {
      "minigame_times_per_day": [5, 8],
      "minigame_reward_multiplier": 1.0,
      "minigame_timeout_seconds": 30
    },
    "hard": {
      "minigame_times_per_day": [3, 5],
      "minigame_reward_multiplier": 1.3,
      "minigame_timeout_seconds": 20
    }
  }
}
```

### 2. Exclusive JSON Schema (Epic, NOT Legendary)

**File:** `data/events/pools/{event_type}/exclusives/{year}.json`

```json
{
  "year": 2027,
  "event_type": "halloween",
  "created_at": "2027-09-01",
  
  "exclusive_fish": {
    "key": "halloween_exclusive_2027",
    "name": "Cá Bóng Ma Huyền Bí",
    "emoji": "💀🐟",
    "tier": "epic",
    "drop_rate": 0.02,
    "currency_reward": [100, 180],
    "is_exclusive": true,
    "lore": "Chỉ xuất hiện trong Halloween 2027. Người sở hữu được tôn vinh là Thợ Săn Ma chân chính."
  },
  
  "exclusive_cosmetic": {
    "key": "frame_halloween_2027",
    "name": "Khung Ma Quái 2027",
    "type": "frame",
    "asset_path": "frames/frame_halloween_2027.png",
    "price": 500,
    "limit_per_user": 1,
    "is_exclusive": true
  },
  
  "exclusive_title": {
    "key": "title_ghost_hunter_2027",
    "name": "👻 Thợ Săn Ma 2027"
  },
  
  "fixed_quests": [
    {
      "id": "catch_exclusive_2027",
      "type": "catch_specific_fish",
      "target_fish": "halloween_exclusive_2027",
      "target": 1,
      "reward_type": "title",
      "reward_value": "title_ghost_hunter_2027",
      "description": "Bắt được Cá Bóng Ma Huyền Bí"
    },
    {
      "id": "collect_all_fish_2027",
      "type": "collect_all_event_fish",
      "reward_type": "currency",
      "reward_value": 200,
      "description": "Sưu tập tất cả cá Halloween 2027"
    }
  ],
  
  "difficulty_preset": "normal"
}
```

### 3. Database Schema

**Table:** `event_content_history` ( Already added)

```sql
CREATE TABLE IF NOT EXISTS event_content_history (
    event_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    content_type TEXT NOT NULL,  -- 'fish', 'shop', 'quest'
    content_key TEXT NOT NULL,
    tier TEXT,                   -- 'common', 'rare', 'epic' (NO 'legendary')
    is_exclusive BOOLEAN DEFAULT FALSE,
    seed_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_type, year, content_type, content_key)
);

CREATE INDEX IF NOT EXISTS idx_ech_lookup 
ON event_content_history(event_type, content_type, content_key);
```

### 4. Selection Algorithm

```python
def select_content_for_year(
    pool: list[PoolItem],
    history: list[HistoryRecord],
    event_type: str,
    year: int,
    tier_requirements: dict[str, int],  # {"epic": 1, "rare": 2, "common": 2}
    cooldown_years: int = 2
) -> list[PoolItem]:
    """
    Select content with:
    - Seed-based RNG for reproducibility
    - Tier balance enforcement
    - 2-year cooldown for non-exclusive items
    - Fallback when pool exhausted
    """
    seed = f"{event_type}_{year}_fish"
    rng = random.Random(seed)
    
    # Get recently used keys
    recent_keys = {h.content_key for h in history 
                   if year - h.year < cooldown_years}
    
    selected = []
    for tier, count in tier_requirements.items():
        if tier == "legendary":
            continue  # SKIP - no legendary in seasonal
            
        tier_pool = [p for p in pool if p.tier == tier and not p.is_exclusive]
        available = [p for p in tier_pool if p.key not in recent_keys]
        
        if len(available) < count:
            available = tier_pool  # Fallback to allow repeats
        
        chosen = rng.sample(available, min(count, len(available)))
        selected.extend(chosen)
    
    return selected
```

---

## Task Flow (Updated v4)

```
TODO 0 (drop_rate bug) ✅ DONE
    ↓
TODO 1 (history table) ✅ DONE
    ↓
TODO 2 (Pool Files for ALL 8 EVENTS) ← PENDING
    ↓
TODO 3 (RotationService) ← PENDING
    ↓
TODO 4 (EventManager Integration) ← PENDING
    ↓
TODO 5 (Exclusive Loading) ← PENDING
    ↓
TODO 6 (CLI Tool) ← PENDING
    ↓
TODO 7 (Asset Migration) ← NEW in v4
    ↓
TODO 8 (Frame Renderer) ← NEW in v4
```

---

## TODOs

### TODO 0: Fix drop_rate Bug  DONE
- Fixed `cogs/seasonal/event_fish_hook.py` to use actual `drop_rate`

### TODO 1: Create event_content_history Table  DONE
- Added to `database.py` SEASONAL_TABLES_SQL

---

### TODO 2: Create Pool JSON Files (ALL 8 EVENTS)

**What to do**:
- Create pool.json for each of 8 events
- Create 2026.json exclusive for each event
- Populate with existing fish from current configs
- Add buffer items for future rotation

**Files to create**:
```
data/events/pools/
├── _template/pool.json
├── _template/exclusives/YYYY.json
├── halloween/pool.json + exclusives/2026.json
├── spring/pool.json + exclusives/2026.json
├── summer/pool.json + exclusives/2026.json
├── autumn/pool.json + exclusives/2026.json
├── winter/pool.json + exclusives/2026.json
├── mid_autumn/pool.json + exclusives/2026.json
├── earth_day/pool.json + exclusives/2026.json
└── birthday/pool.json + exclusives/2026.json
```

**Per-event pool requirements**:

| Event | Common | Rare | Epic | Pool Total |
|-------|--------|------|------|------------|
| Halloween | 6 | 6 | 4 | 16 |
| Spring | 10 | 8 | 5 | 23 |
| Summer | 10 | 8 | 5 | 23 |
| Autumn | 10 | 8 | 5 | 23 |
| Winter | 10 | 8 | 5 | 23 |
| Mid-Autumn | 6 | 6 | 3 | 15 |
| Earth Day | 6 | 5 | 3 | 14 |
| Birthday | 0 | 0 | 0 | Shop only |

**Acceptance Criteria**:
- [ ] All 8 events have pool.json
- [ ] All pools have tier_requirements
- [ ] All 2026.json exclusives created (Epic tier)
- [ ] `python -c "import json; json.load(open('data/events/pools/halloween/pool.json'))"` works for all

**Commit**: `feat(seasonal): add pool structure for all 8 events`

---

### TODO 3: Implement ContentRotationService

**What to do**:
- Create `cogs/seasonal/services/rotation_service.py`
- Support all 8 event types
- Enforce Epic as max tier (no legendary)

**Core Methods**:
```python
class ContentRotationService:
    SUPPORTED_EVENTS = [
        "halloween", "spring", "summer", "autumn", 
        "winter", "mid_autumn", "earth_day", "birthday"
    ]
    
    async def get_pool(self, event_type: str) -> dict | None
    async def get_exclusive(self, event_type: str, year: int) -> dict | None
    async def select_fish_for_year(self, event_type: str, year: int) -> list[dict]
    async def select_shop_for_year(self, event_type: str, year: int) -> list[dict]
    async def get_history(self, event_type: str, years: list[int]) -> set[str]
    async def save_selection(self, event_type: str, year: int, ...) -> None
```

**Acceptance Criteria**:
- [ ] All 8 events supported
- [ ] Tier balance enforced (no legendary)
- [ ] Seed produces same result
- [ ] History exclusion works

**Commit**: `feat(seasonal): add ContentRotationService for all events`

---

### TODO 4: Integrate Rotation into EventManager

**What to do**:
- Modify `EventManager.load_event_config()` to check for pool
- Merge rotated content with static config
- Fallback gracefully when no pool

**Acceptance Criteria**:
- [ ] Events without pools still work
- [ ] Events with pools use rotated content
- [ ] `/sukien info` shows correct fish list

**Commit**: `feat(seasonal): integrate rotation into EventManager`

---

### TODO 5: Yearly Exclusive Loading

**What to do**:
- Load exclusive from `exclusives/{year}.json`
- Merge exclusive fish into event config (as Epic)
- Add `is_exclusive: true` flag for UI display
- Include fixed quests for exclusive
- **Use asset_path for cosmetics** (v4 NEW)

**Acceptance Criteria**:
- [ ] Exclusive fish appears first in list
- [ ] `is_exclusive: true` flag present
- [ ] Fixed quest for exclusive included
- [ ] UI shows exclusive badge/marker
- [ ] **Cosmetic asset_path resolves correctly** (v4 NEW)

**Commit**: `feat(seasonal): add yearly exclusive loading`

---

### TODO 6: CLI Tool for Config Generation

**What to do**:
- Create `tools/generate_event.py`
- Support all 8 event types
- Generate reproducible configs from pools

**Usage**:
```bash
# Generate for specific event and year
python -m tools.generate_event --type halloween --year 2027

# Generate for all events
python -m tools.generate_event --all --year 2027

# Preview without saving
python -m tools.generate_event --type spring --year 2027 --dry-run
```

**Acceptance Criteria**:
- [ ] Generates valid JSON for any event
- [ ] Saves history to database
- [ ] Same year + event = same output
- [ ] Supports --all flag

**Commit**: `feat(seasonal): add CLI for yearly config generation`

---

### TODO 7: Asset Migration Script (v4 NEW)

**What to do**:
- Create `scripts/migrate_assets.py`
- Rename existing assets to include `_2025` suffix
- Update JSON configs with new keys
- Migrate database records

**Script Logic**:
```python
ASSETS_TO_MIGRATE = {
    "frames/frame_halloween.png": "frames/frame_halloween_2025.png",
    "profile/bg_halloween.png": "profile/bg_halloween_2025.png",
    # ... all 16 seasonal assets
}

KEYS_TO_MIGRATE = {
    "bg_halloween": "bg_halloween_2025",
    "frame_halloween": "frame_halloween_2025",
    # ... all keys
}
```

**Acceptance Criteria**:
- [ ] All 16 seasonal assets renamed
- [ ] All JSON configs updated
- [ ] Database records migrated
- [ ] Typo `bg_midatumn` fixed to `bg_midautumn`
- [ ] Script is idempotent (can run twice safely)

**Commit**: `chore(assets): migrate seasonal assets to year-based naming`

---

### TODO 8: Frame Renderer Implementation (v4 NEW)

**What to do**:
- Modify `cogs/profile/utils/renderer.py`
- Implement frame overlay on profile images
- Support dynamic frame loading from asset_path

**Changes Needed**:
```python
def render_profile(user_data: dict, frame_key: str | None = None):
    # ... existing background rendering ...
    
    if frame_key:
        frame_path = get_frame_path(frame_key)  # e.g., "frames/frame_halloween_2025.png"
        frame_img = Image.open(frame_path)
        profile_img.paste(frame_img, (0, 0), frame_img)  # With alpha
    
    return profile_img
```

**Acceptance Criteria**:
- [ ] Frames render correctly over profile background
- [ ] Year-based frame paths resolve correctly
- [ ] Graceful fallback when frame not found
- [ ] No performance regression

**Commit**: `feat(profile): implement frame overlay rendering`

---

## Commit Strategy

| Task | Message | Files |
|------|---------|-------|
| 0 |  `fix(seasonal): use actual drop_rate for fish selection` | event_fish_hook.py |
| 1 |  `feat(seasonal): add event_content_history table` | database.py |
| 2 | `feat(seasonal): add pool structure for all 8 events` | pools/**/*.json |
| 3 | `feat(seasonal): add ContentRotationService for all events` | rotation_service.py |
| 4 | `feat(seasonal): integrate rotation into EventManager` | event_manager.py |
| 5 | `feat(seasonal): add yearly exclusive loading` | rotation_service.py |
| 6 | `feat(seasonal): add CLI for yearly config generation` | tools/generate_event.py |
| 7 | `chore(assets): migrate seasonal assets to year-based naming` | assets/, data/events/*.json |
| 8 | `feat(profile): implement frame overlay rendering` | cogs/profile/utils/renderer.py |

---

## Success Criteria

### Verification Commands
```bash
# All pools valid JSON
python -c "import json, glob; [json.load(open(f)) for f in glob.glob('data/events/pools/**/*.json', recursive=True)]"

# Service loads
python -c "from cogs.seasonal.services.rotation_service import ContentRotationService; print('OK')"

# CLI works for all events
for event in halloween spring summer autumn winter mid_autumn earth_day birthday; do
  python -m tools.generate_event --type $event --year 2027 --dry-run
done

# Assets migrated correctly
ls assets/frames/frame_*_2025.png | wc -l  # Should be 8
ls assets/profile/bg_*_2025.png | wc -l    # Should be 8
```

### Final Checklist
- [ ] All 8 events have pools
- [ ] All pools enforce Epic as max tier
- [ ] Yearly exclusives are Epic (not Legendary)
- [ ] Legendary fish system unchanged
- [ ] No regression in existing events
- [ ] **All assets have year suffix** (v4 NEW)
- [ ] **Frames render on profiles** (v4 NEW)
- [ ] **Typo bg_midatumn fixed** (v4 NEW)
