# Aquarium Set System Redesign - Work Plan v2

## Context

### Original Request
Thiết kế lại hệ thống Set Trang Trí Aquarium với:
- Loadouts + Activity Binding
- Single source of truth (fix 3 duplicate data sources)
- Tên Hán-Việt cho sets/items
- Mở rộng 18 sets, 72 items

### System Audit Findings

#### 3 Duplicate Data Sources (PROBLEM)
| Source | Location | Used By |
|--------|----------|---------|
| `constants.py` | `cogs/aquarium/constants.py` | HousingEngine, UI |
| `decor_items.json` | `data/items/decor_items.json` | **UNUSED** |
| `feng_shui_sets.json` | `data/sets/feng_shui_sets.json` | EffectManager |

#### Critical Issues
1. **EffectManager.get_total_bonus() UNUSED** - exists but never called
2. **tuong_lai passive NOT IMPLEMENTED** - only defined, no consumer
3. **Charm parsed from description string** - fragile pattern `(+X Charm)`
4. **Inconsistent bonus checks** - tree uses `is_set_active()`, sell uses `get_active_sets()`
5. **UserDecor table UNUSED** - model exists but never populated

#### Current Bonus Status
| Set | Effect | Status | File |
|-----|--------|--------|------|
| `dai_duong` | +5% harvest | ✅ WORKS | `tree_manager.py:613-620` |
| `hoang_gia` | +10% sell | ✅ WORKS | `sell.py:223-230` |
| `tuong_lai` | +200/day | ❌ NOT IMPLEMENTED | - |

### Selected Approach: Full Restructure
- JSON as single source of truth
- Deprecate constants.py data
- Rewrite EffectManager + HousingEngine
- Fix all identified issues

---

## Work Objectives

### Core Objective
Tạo hệ thống Set hoàn chỉnh với single source of truth, 18 sets, 72 items, loadouts, và tích hợp đầy đủ với gameplay cogs.

### Concrete Deliverables
- [ ] `data/aquarium/sets.json` - Single source (sets + items)
- [ ] Rewritten `EffectManager` - Load from JSON, consistent API
- [ ] Updated `HousingEngine` - Use JSON, not constants
- [ ] `LoadoutService` - Activity-bound loadouts
- [ ] Fix all 6 identified issues

### Definition of Done
- [ ] Only 1 data source for sets/items
- [ ] All effects implemented and working
- [ ] Loadouts auto-apply per activity
- [ ] constants.py DECOR_ITEMS/FENG_SHUI_SETS removed
- [ ] All tests pass

### Must NOT Have (Guardrails)
- `name_han` field (unnecessary, chữ Hán không ai đọc)
- Duplicate data sources
- Hardcoded bonuses in cog files
- Charm parsed from description strings

---

## JSON Schema Design

### File: `data/aquarium/sets.json`

```json
{
  "version": "2.0",
  "sets": {
    "hai_duong_cung": {
      "id": "hai_duong_cung",
      "name": "Hải Dương Cung",
      "description": "Cung điện đại dương - nơi Long Vương ngự trị",
      "tier": 1,
      "activity": "fishing",
      "required_pieces": 2,
      "effects": {
        "catch_rate_bonus": 0.05
      },
      "items": ["san_ho_do", "rong_bien_xanh", "den_su_sang", "vo_so_khong_lo"]
    }
  },
  "items": {
    "san_ho_do": {
      "id": "san_ho_do",
      "name": "San Hô Đỏ",
      "description": "San hô đỏ rực từ đáy đại dương",
      "icon": "🪸",
      "set_id": "hai_duong_cung",
      "tier": 1,
      "charm": 2,
      "price_seeds": 3000,
      "price_leaf": 50
    }
  }
}
```

**Key Design Decisions:**
- `charm` is direct integer (not parsed from desc)
- `price_seeds` and `price_leaf` separate fields
- `effects` is dict of effect_key → value
- No `name_han` - chỉ cần `name` tiếng Việt

---

## 18 Sets Definition

### Tier 1: Sơ Cấp (Bonuses 5-8%)

| # | ID | Tên | Theme | 2pc Effect | Activity |
|---|-----|-----|-------|------------|----------|
| 1 | `hai_duong_cung` | Hải Dương Cung | Ocean | `catch_rate_bonus: 0.05` | fishing |
| 2 | `lam_tien_vien` | Lâm Tiên Viên | Forest | `seed_bonus: 0.05` | harvest |
| 3 | `kim_ngan_kho` | Kim Ngân Khố | Treasure | `sell_price_bonus: 0.05` | sell |
| 4 | `bach_van_trai` | Bạch Vân Trại | Clouds | `passive_income: 50` | passive |
| 5 | `thuy_tinh_cac` | Thủy Tinh Các | Crystal | `global_xp_bonus: 0.03` | global |
| 6 | `hong_lien_tri` | Hồng Liên Trì | Lotus | `quest_reward_bonus: 0.05` | quest |

### Tier 2: Trung Cấp (Bonuses 8-12%)

| # | ID | Tên | Theme | 2pc Effect | Activity |
|---|-----|-----|-------|------------|----------|
| 7 | `long_cung_dien` | Long Cung Điện | Dragon | `rare_chance_bonus: 0.10` | fishing |
| 8 | `hoang_kim_dai` | Hoàng Kim Đài | Royal | `sell_price_bonus: 0.10` | sell |
| 9 | `xuan_hoa_duong` | Xuân Hoa Đường | Spring | `seed_bonus: 0.08` | harvest |
| 10 | `huyen_bang_cung` | Huyền Băng Cung | Ice | `passive_income: 100` | passive |
| 11 | `ha_long_loan` | Hạ Long Loan | Vietnam | `global_xp_bonus: 0.05` | global |
| 12 | `trung_thu_cac` | Trung Thu Các | Festival | `gift_value_bonus: 0.10` | relationship |

### Tier 3: Cao Cấp (Bonuses 12-15%+)

| # | ID | Tên | Theme | 2pc Effect | Activity |
|---|-----|-----|-------|------------|----------|
| 13 | `cuu_long_giang` | Cửu Long Giang | Mekong | `legendary_chance_bonus: 0.15` | fishing |
| 14 | `phuong_hoang_dai` | Phượng Hoàng Đài | Phoenix | `sell_price_bonus: 0.12` | sell |
| 15 | `van_mong_lau` | Vân Mộng Lâu | Dreamy | `passive_income: 200` | passive |
| 16 | `hoa_son_cung` | Hỏa Sơn Cung | Volcanic | `global_xp_bonus: 0.08` | global |
| 17 | `au_lac_thanh` | Âu Lạc Thành | Ancient | `all_bonus: 0.05` | global |
| 18 | `thien_ha_dao` | Thiên Hà Đảo | Galaxy | `gambling_luck: 0.10` | gambling |

---

## 72 Items (4 per set)

### Tier 1 Items

**1. Hải Dương Cung**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `san_ho_do` | San Hô Đỏ | 🪸 | 2 | 3000 | 50 |
| `rong_bien_xanh` | Rong Biển Xanh | 🌿 | 2 | 2500 | 40 |
| `den_su_sang` | Đèn Sứ Sáng | 🏮 | 3 | 4000 | 60 |
| `vo_so_khong_lo` | Vỏ Sò Khổng Lồ | 🐚 | 2 | 3500 | 55 |

**2. Lâm Tiên Viên**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `cay_bon_sai` | Cây Bonsai | 🌳 | 3 | 4000 | 60 |
| `nam_linh_chi` | Nấm Linh Chi | 🍄 | 2 | 3000 | 50 |
| `buom_xanh` | Bướm Xanh | 🦋 | 2 | 2500 | 40 |
| `hoa_lan_rung` | Hoa Lan Rừng | 🌸 | 3 | 4500 | 70 |

**3. Kim Ngân Khố**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `ruong_vang` | Rương Vàng | 📦 | 4 | 5000 | 80 |
| `dong_tien_co` | Đồng Tiền Cổ | 🪙 | 2 | 2000 | 30 |
| `kiem_bau` | Kiếm Báu | ⚔️ | 3 | 4000 | 60 |
| `chan_dung_vua` | Chân Dung Vua | 🖼️ | 3 | 4500 | 70 |

**4. Bạch Vân Trại**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `may_trang` | Mây Trắng | ☁️ | 2 | 2500 | 40 |
| `chim_hac` | Chim Hạc | 🦢 | 3 | 4000 | 60 |
| `diem_trang` | Điểm Trang | ✨ | 2 | 2000 | 30 |
| `cau_vong_nho` | Cầu Vồng Nhỏ | 🌈 | 3 | 4500 | 70 |

**5. Thủy Tinh Các**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `pha_le_xanh` | Pha Lê Xanh | 💎 | 4 | 5000 | 80 |
| `guong_than` | Gương Thần | 🪞 | 3 | 4000 | 60 |
| `cau_thuy_tinh` | Cầu Thủy Tinh | 🔮 | 3 | 4500 | 70 |
| `ngoc_sao` | Ngọc Sao | ⭐ | 2 | 3000 | 50 |

**6. Hồng Liên Trì**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `hoa_sen_hong` | Hoa Sen Hồng | 🪷 | 3 | 4000 | 60 |
| `la_sen` | Lá Sen | 🍃 | 2 | 2000 | 30 |
| `ca_chep_vang` | Cá Chép Vàng | 🐟 | 3 | 4500 | 70 |
| `thuyen_nan` | Thuyền Nan | ⛵ | 2 | 3000 | 50 |

### Tier 2 Items

**7. Long Cung Điện**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `tuong_rong` | Tượng Rồng | 🐉 | 5 | 8000 | 120 |
| `ngoc_rong` | Ngọc Rồng | 🔵 | 4 | 7000 | 100 |
| `cot_vang` | Cột Vàng | 🏛️ | 4 | 7500 | 110 |
| `man_lua` | Màn Lụa | 🎭 | 3 | 6000 | 90 |

**8. Hoàng Kim Đài**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `ngai_vang` | Ngai Vàng | 👑 | 6 | 10000 | 150 |
| `vuong_mien` | Vương Miện | 💍 | 5 | 9000 | 130 |
| `quyen_truong` | Quyền Trượng | 🏆 | 4 | 8000 | 120 |
| `ao_bao` | Áo Bào | 👘 | 4 | 7500 | 110 |

**9. Xuân Hoa Đường**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `hoa_dao` | Hoa Đào | 🌸 | 4 | 7000 | 100 |
| `cay_mai` | Cây Mai | 🌼 | 4 | 7500 | 110 |
| `con_en` | Con Én | 🐦 | 3 | 6000 | 90 |
| `long_den` | Lồng Đèn | 🏮 | 3 | 5500 | 85 |

**10. Huyền Băng Cung**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `bang_tuyet` | Băng Tuyết | ❄️ | 4 | 7000 | 100 |
| `tuong_bang` | Tượng Băng | 🧊 | 4 | 7500 | 110 |
| `hoa_tuyet` | Hoa Tuyết | ❆ | 3 | 6000 | 90 |
| `guom_bang` | Gươm Băng | 🗡️ | 5 | 8500 | 125 |

**11. Hạ Long Loan**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `dao_da` | Đảo Đá | 🏝️ | 4 | 7000 | 100 |
| `hang_dong` | Hang Động | 🕳️ | 3 | 6000 | 90 |
| `thuyen_buom` | Thuyền Buồm | ⛵ | 4 | 7500 | 110 |
| `song_xanh` | Sóng Xanh | 🌊 | 3 | 5500 | 85 |

**12. Trung Thu Các**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `banh_trung_thu` | Bánh Trung Thu | 🥮 | 3 | 6000 | 90 |
| `den_ong_sao` | Đèn Ông Sao | ⭐ | 4 | 7000 | 100 |
| `trang_ram` | Trăng Rằm | 🌕 | 5 | 8000 | 120 |
| `chu_cuoi` | Chú Cuội | 🌳 | 4 | 7500 | 110 |

### Tier 3 Items

**13. Cửu Long Giang**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `rong_thieng` | Rồng Thiêng | 🐲 | 7 | 15000 | 220 |
| `ngoc_linh` | Ngọc Linh | 💠 | 6 | 12000 | 180 |
| `song_me` | Sông Mẹ | 🌊 | 5 | 10000 | 150 |
| `lua_vang` | Lúa Vàng | 🌾 | 5 | 11000 | 160 |

**14. Phượng Hoàng Đài**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `phuong_hoang` | Phượng Hoàng | 🦅 | 8 | 18000 | 260 |
| `long_chau` | Lông Châu | 🪶 | 6 | 13000 | 190 |
| `lua_phuong` | Lửa Phượng | 🔥 | 6 | 14000 | 200 |
| `to_phuong` | Tổ Phượng | 🪹 | 5 | 11000 | 160 |

**15. Vân Mộng Lâu**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `lau_may` | Lầu Mây | 🏯 | 7 | 16000 | 230 |
| `giuong_tien` | Giường Tiên | 🛏️ | 6 | 13000 | 190 |
| `giac_mo` | Giấc Mơ | 💭 | 5 | 10000 | 150 |
| `sao_dem` | Sao Đêm | ✨ | 5 | 11000 | 160 |

**16. Hỏa Sơn Cung**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `nui_lua` | Núi Lửa | 🌋 | 7 | 15000 | 220 |
| `da_nham` | Đá Nham | 🪨 | 5 | 10000 | 150 |
| `lua_thieng` | Lửa Thiêng | 🔥 | 6 | 12000 | 180 |
| `kim_cuong_do` | Kim Cương Đỏ | 💎 | 6 | 14000 | 200 |

**17. Âu Lạc Thành**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `no_than` | Nỏ Thần | 🏹 | 8 | 20000 | 280 |
| `trong_dong` | Trống Đồng | 🥁 | 7 | 16000 | 230 |
| `lac_long` | Lạc Long | 🐉 | 6 | 14000 | 200 |
| `au_co` | Âu Cơ | 🧚 | 6 | 14000 | 200 |

**18. Thiên Hà Đảo**
| ID | Tên | Icon | Charm | Seeds | Leaf |
|----|-----|------|-------|-------|------|
| `thien_ha` | Thiên Hà | 🌌 | 8 | 18000 | 260 |
| `hanh_tinh` | Hành Tinh | 🪐 | 6 | 13000 | 190 |
| `sao_bang` | Sao Băng | ☄️ | 6 | 14000 | 200 |
| `lo_den` | Lỗ Đen | 🌑 | 7 | 16000 | 230 |

---

## Effect Types

```python
class EffectType(str, Enum):
    # Multipliers (percentage)
    CATCH_RATE_BONUS = "catch_rate_bonus"
    RARE_CHANCE_BONUS = "rare_chance_bonus"
    LEGENDARY_CHANCE_BONUS = "legendary_chance_bonus"
    SEED_BONUS = "seed_bonus"
    SELL_PRICE_BONUS = "sell_price_bonus"
    GLOBAL_XP_BONUS = "global_xp_bonus"
    QUEST_REWARD_BONUS = "quest_reward_bonus"
    GIFT_VALUE_BONUS = "gift_value_bonus"
    GAMBLING_LUCK = "gambling_luck"
    ALL_BONUS = "all_bonus"  # Applies to all multipliers
    
    # Flat values
    PASSIVE_INCOME = "passive_income"  # Per day
```

---

## Effect → Cog Integration

| Effect | Cog | File | Current Status |
|--------|-----|------|----------------|
| `catch_rate_bonus` | fishing | `fishing_engine.py` | NOT IMPLEMENTED |
| `rare_chance_bonus` | fishing | `fishing_engine.py` | NOT IMPLEMENTED |
| `legendary_chance_bonus` | fishing | `fishing_engine.py` | NOT IMPLEMENTED |
| `seed_bonus` | tree | `tree_manager.py:613` | IMPLEMENTED (dai_duong) |
| `sell_price_bonus` | fishing | `sell.py:223` | IMPLEMENTED (hoang_gia) |
| `global_xp_bonus` | core | TBD | NOT IMPLEMENTED |
| `quest_reward_bonus` | quest | `quest_service.py` | NOT IMPLEMENTED |
| `gift_value_bonus` | relationship | TBD | NOT IMPLEMENTED |
| `gambling_luck` | baucua/xidach | TBD | NOT IMPLEMENTED |
| `passive_income` | aquarium | `effect_manager.py` | DEFINED, NOT CONSUMED |

---

## Task Flow

```
Phase 1: Data Layer        Phase 2: Logic Layer       Phase 3: Integration
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│ T1: Create JSON    │────▶│ T3: EffectManager  │────▶│ T5: Tree cog       │
│ T2: DB Migration   │     │ T4: HousingEngine  │     │ T6: Sell cog       │
└────────────────────┘     │ T4b: LoadoutService│     │ T7: Fishing cog    │
                           └────────────────────┘     │ T8: Passive income │
                                                      └────────────────────┘
                                                              │
Phase 5: Cleanup           Phase 4: UI                        │
┌────────────────────┐     ┌────────────────────┐             │
│ T11: Remove old    │◀────│ T9: Loadout cmds   │◀────────────┘
│ T12: Tests         │     │ T10: Set display   │
└────────────────────┘     └────────────────────┘
```

---

## TODOs

### Phase 1: Data Layer

- [ ] **T1. Create Single JSON Data Source**
  
  **What to do:**
  - Create `data/aquarium/sets.json` with schema above
  - Include all 18 sets and 72 items
  - Charm as direct integer, not parsed from desc
  
  **Must NOT do:**
  - Add `name_han` field
  - Duplicate any data
  
  **Parallelizable:** YES (with T2)
  
  **References:**
  - Schema in this document
  - Current data: `cogs/aquarium/constants.py` DECOR_ITEMS
  
  **Acceptance Criteria:**
  - [ ] JSON validates: `python -c "import json; d=json.load(open('data/aquarium/sets.json')); print(len(d['sets']), len(d['items']))"`
  - [ ] Output: `18 72`

  **Commit:** YES
  - Message: `feat(aquarium): create single source JSON with 18 sets, 72 items`

---

- [ ] **T2. Add Loadout Database Model**
  
  **What to do:**
  - Add Loadout model to `cogs/aquarium/models.py`
  - Fields: id, user_id, name, activity, slot_0-4, is_active, created_at
  - Create Alembic migration
  
  **Parallelizable:** YES (with T1)
  
  **References:**
  - `cogs/aquarium/models.py` patterns
  
  **Acceptance Criteria:**
  - [ ] Model added
  - [ ] Migration created
  - [ ] `alembic upgrade head` succeeds

  **Commit:** YES (group with T1)

---

### Phase 2: Logic Layer

- [ ] **T3. Rewrite EffectManager**
  
  **What to do:**
  - Load from `data/aquarium/sets.json` (not feng_shui_sets.json)
  - Remove singleton pattern (use dependency injection)
  - Implement `get_active_effects(user_id, activity)` 
  - Implement `get_multiplier(user_id, effect_key)` - returns `1 + bonus`
  - Implement `get_flat_bonus(user_id, effect_key)` - returns flat value
  - Support `all_bonus` (adds to all multipliers)
  
  **Must NOT do:**
  - Use hardcoded set names
  - Import from constants.py
  
  **Parallelizable:** NO (depends on T1)
  
  **References:**
  - Current: `cogs/aquarium/logic/effect_manager.py`
  - New JSON schema
  
  **Acceptance Criteria:**
  - [ ] Loads from new JSON
  - [ ] `get_multiplier()` returns correct value
  - [ ] `all_bonus` applies to all multipliers
  - [ ] Unit test passes

  **Commit:** YES
  - Message: `refactor(aquarium): rewrite EffectManager with new JSON source`

---

- [ ] **T4. Update HousingEngine**
  
  **What to do:**
  - Load items from JSON (not constants.py DECOR_ITEMS)
  - `get_item(item_id)` returns item from JSON
  - `calculate_home_stats()` uses `item.charm` directly (not parsed from desc)
  - `get_active_sets()` uses JSON set definitions
  - Remove `is_set_active()` - use EffectManager instead
  
  **Must NOT do:**
  - Parse charm from description string
  - Import DECOR_ITEMS from constants
  
  **Parallelizable:** NO (depends on T1, T3)
  
  **References:**
  - Current: `cogs/aquarium/logic/housing.py`
  
  **Acceptance Criteria:**
  - [ ] Charm calculated from JSON field
  - [ ] No imports from constants.py
  - [ ] Unit test passes

  **Commit:** YES (group with T3)

---

- [ ] **T4b. Create LoadoutService**
  
  **What to do:**
  - Create `cogs/aquarium/logic/loadout_service.py`
  - `create_loadout(user_id, name, activity, slots)`
  - `apply_loadout(user_id, loadout_id)` - updates HomeSlot
  - `get_loadout_for_activity(user_id, activity)` - for auto-apply
  - `list_loadouts(user_id)`
  - `delete_loadout(user_id, loadout_id)`
  
  **Parallelizable:** NO (depends on T2, T4)
  
  **References:**
  - `cogs/aquarium/models.py` Loadout model
  
  **Acceptance Criteria:**
  - [ ] CRUD operations work
  - [ ] `apply_loadout` updates HomeSlot correctly
  - [ ] Unit test passes

  **Commit:** YES
  - Message: `feat(aquarium): add LoadoutService for activity-bound loadouts`

---

### Phase 3: Cog Integration

- [ ] **T5. Update Tree Cog (seed_bonus)**
  
  **What to do:**
  - Replace hardcoded `is_set_active(uid, 'dai_duong')` with `EffectManager.get_multiplier(uid, 'seed_bonus')`
  - Auto-apply harvest loadout before calculation
  
  **Current code (tree_manager.py:613-620):**
  ```python
  # OLD - hardcoded
  if await HousingEngine(session).is_set_active(uid, 'dai_duong'):
      bonus = int(seed_rewards[uid] * 0.05)
  ```
  
  **New code:**
  ```python
  # NEW - from EffectManager
  multiplier = await effect_manager.get_multiplier(uid, 'seed_bonus')
  seed_rewards[uid] = int(seed_rewards[uid] * multiplier)
  ```
  
  **Parallelizable:** YES (with T6, T7, T8)
  
  **Acceptance Criteria:**
  - [ ] No hardcoded set names
  - [ ] Bonus applies correctly
  - [ ] Integration test passes

  **Commit:** YES
  - Message: `refactor(tree): use EffectManager for harvest bonus`

---

- [ ] **T6. Update Sell Command (sell_price_bonus)**
  
  **What to do:**
  - Replace tier check with `EffectManager.get_multiplier(uid, 'sell_price_bonus')`
  - Auto-apply sell loadout
  
  **Current code (sell.py:223-230):**
  ```python
  # OLD - checks tier==2
  for s in active_sets:
      if s.get('tier') == 2:
          bonus_percent = s['effects'].get('sell_bonus_percent', 0)
  ```
  
  **New code:**
  ```python
  # NEW - from EffectManager
  multiplier = await effect_manager.get_multiplier(uid, 'sell_price_bonus')
  final_total = int(total * multiplier)
  ```
  
  **Parallelizable:** YES (with T5, T7, T8)
  
  **Acceptance Criteria:**
  - [ ] No hardcoded tier checks
  - [ ] Bonus applies correctly

  **Commit:** YES
  - Message: `refactor(sell): use EffectManager for sell bonus`

---

- [ ] **T7. Add Fishing Effects**
  
  **What to do:**
  - Integrate `catch_rate_bonus`, `rare_chance_bonus`, `legendary_chance_bonus`
  - Find integration points in `cogs/fishing/logic/fishing_engine.py`
  - Auto-apply fishing loadout
  
  **Parallelizable:** YES (with T5, T6, T8)
  
  **Acceptance Criteria:**
  - [ ] All 3 fishing effects work
  - [ ] Integration test passes

  **Commit:** YES
  - Message: `feat(fishing): integrate aquarium set bonuses`

---

- [ ] **T8. Implement Passive Income**
  
  **What to do:**
  - Create daily task or hook to apply `passive_income` effect
  - Sum all active passive_income values
  - Add to user's economy balance
  
  **Note:** tuong_lai was DEFINED but NEVER IMPLEMENTED. This task fixes that.
  
  **Parallelizable:** YES (with T5, T6, T7)
  
  **Acceptance Criteria:**
  - [ ] Passive income applies daily
  - [ ] Multiple sets stack correctly

  **Commit:** YES
  - Message: `feat(aquarium): implement passive_income effect`

---

### Phase 4: UI

- [ ] **T9. Add Loadout Commands**
  
  **What to do:**
  - `/loadout tao <name> <activity>` - create
  - `/loadout xem` - list all
  - `/loadout xoa <name>` - delete
  - `/loadout ap-dung <name>` - manual apply
  
  **Parallelizable:** YES (with T10)
  
  **Acceptance Criteria:**
  - [ ] All commands work
  - [ ] Vietnamese command names

  **Commit:** YES
  - Message: `feat(aquarium): add loadout management commands`

---

- [ ] **T10. Update Set Display**
  
  **What to do:**
  - Update `/nha` to show sets with Vietnamese names from JSON
  - Show active effects and values
  - Show current loadout for each activity
  
  **Parallelizable:** YES (with T9)
  
  **Acceptance Criteria:**
  - [ ] Names display correctly
  - [ ] Effects show values

  **Commit:** YES (group with T9)

---

### Phase 5: Cleanup

- [ ] **T11. Remove Old Data Sources**
  
  **What to do:**
  - Remove `DECOR_ITEMS` and `FENG_SHUI_SETS` from constants.py
  - Delete `data/items/decor_items.json` (was unused)
  - Delete `data/sets/feng_shui_sets.json` (replaced by new JSON)
  - Update any remaining imports
  
  **Parallelizable:** NO (depends on all previous)
  
  **Acceptance Criteria:**
  - [ ] No references to old data sources
  - [ ] All tests pass
  - [ ] Bot runs correctly

  **Commit:** YES
  - Message: `refactor(aquarium): remove deprecated data sources`

---

- [ ] **T12. Add Tests**
  
  **What to do:**
  - Unit tests for EffectManager
  - Unit tests for HousingEngine
  - Unit tests for LoadoutService
  - Integration tests for cog hooks
  
  **Parallelizable:** NO (depends on all)
  
  **Acceptance Criteria:**
  - [ ] 80%+ coverage on new code
  - [ ] All tests pass

  **Commit:** YES
  - Message: `test(aquarium): add comprehensive test suite`

---

## Statistics

| Metric | Value |
|--------|-------|
| Sets | 18 |
| Items | 72 |
| Effect Types | 11 |
| Tasks | 12 |
| Files to Create | 2 (JSON, loadout_service.py) |
| Files to Modify | 6 |
| Files to Delete | 2 |

---

## Commit Strategy

| After | Message |
|-------|---------|
| T1-T2 | `feat(aquarium): add sets JSON and Loadout model` |
| T3-T4b | `refactor(aquarium): rewrite EffectManager, HousingEngine, add LoadoutService` |
| T5-T8 | `feat(aquarium): integrate effects with fishing, tree, sell, passive` |
| T9-T10 | `feat(aquarium): add loadout commands and UI` |
| T11-T12 | `refactor(aquarium): cleanup and tests` |
