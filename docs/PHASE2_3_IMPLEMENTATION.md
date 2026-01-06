# Phase 2 & 3 Implementation Plan - BHNBot VIP Enhancements

## PHASE 1 COMPLETED ✅

### Bugs Fixed:
1. **vip_commands.py** line 190 - SQL placeholder corrected to `$1`

### Features Verified:
- ✅ VIP Purchase (`/thuongluu b/t/s`)
- ✅ VIP Status & Leaderboard
- ✅ Bầu Cua Instant Cashback + Daily Cashback
- ✅ Tree Auto-Water (daily cron at 7AM)
- ✅ `/nthint` - VIP-only word hints
- ✅ VIP Fish Pool (tier-based access)
- ✅ Aquarium Themes (VIP 2+)

---

## PHASE 2: SOCIAL FEATURES (Partially Implemented)

### 1. Prestige Badges for Tree ✅ (Code Added)

**Files Modified:**
- `cogs/tree/constants.py` - Added `PRESTIGE_TIERS` and `PRESTIGE_BADGES`
- `cogs/tree/helpers.py` - Added helper functions:
  - `get_prestige_tier(total_exp)`
  - `get_prestige_badge(total_exp)`
  - `format_contributor_with_badge()`
  - Updated `format_all_time_contributors()` to show badges

**Implementation:**
```python
PRESTIGE_TIERS = {
    1: {"name": "🌱 Người Trồng Cây", "min_exp": 1000, "color": 0x95C77D},
    2: {"name": "🌿 Người Làm Vườn", "min_exp": 5000, "color": 0x6AB04C},
    3: {"name": "🌳 Người Bảo Vệ Rừng", "min_exp": 25000, "color": 0x4A7C59},
    4: {"name": "🌸 Thần Nông", "min_exp": 100000, "color": 0xF8B400},
    5: {"name": "🍎 Tiên Nhân", "min_exp": 500000, "color": 0xFF6B6B}
}
```

**New Command (Draft - Needs Testing):**
`/huyhieu` - View personal prestige badge and progress

**Status:** Code added but needs bot restart + testing

---

### 2. Friend/Neighbor System 🔴 (NOT IMPLEMENTED)

**Recommended Implementation:**

#### Database Schema (PostgreSQL):
```sql
CREATE TABLE friendships (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    friend_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, accepted, blocked
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, friend_id)
);

CREATE INDEX idx_friendships_user ON friendships(user_id);
CREATE INDEX idx_friendships_friend ON friendships(friend_id);
```

#### Commands:
- `/banbe add @user` - Send friend request
- `/banbe accept @user` - Accept request
- `/banbe list` - Show friend list
- `/banbe remove @user` - Unfriend

#### Aquarium Integration:
- `/thamnha @friend` - Visit friend's aquarium (faster than searching)
- Friend visits give +10% XP bonus
- Notification DM when friend visits

---

### 3. Enhanced Gifting (/tangqua → /gift) 🟡 (PARTIALLY DONE)

**Current State:**
- `/tangqua` exists with basic gifting
- Supports: cafe, flower, ring, gift, chocolate, card
- Has anonymous mode
- Uses random messages from `GIFT_MESSAGES`

**Enhancements Needed:**

#### A. Gift History Tracking
```sql
CREATE TABLE gift_history (
    id SERIAL PRIMARY KEY,
    sender_id BIGINT NOT NULL,
    receiver_id BIGINT NOT NULL,
    item_key VARCHAR(50) NOT NULL,
    quantity INT DEFAULT 1,
    message TEXT,
    anonymous BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### B. New Features:
1. **Gift Leaderboard** - `/gift top`
   - Most generous sender
   - Most popular receiver
  
2. **Gift Streaks** - Daily gift gives bonus
   - 7-day streak → Special badge
   - 30-day streak → Unique item

3. **Gift Bundles** - Pre-made combos
   - "Romance Pack": flower + chocolate + card
   - "Best Friend Pack": 3x gift + 1x ring
   - VIP-only premium bundles

4. **Return Gift System** - Quick thank you
   - Receiver gets "Send Thank You" button
   - Auto-sends a small gift back

---

## PHASE 3: UX IMPROVEMENTS

### 1. VIP Purchase Confirmation Modal ✅ (DESIGN READY)

**Implementation:**
```python
class VIPPurchaseModal(discord.ui.Modal):
    def __init__(self, tier, cost):
        super().__init__(title=f"Xác nhận mua VIP {VIP_NAMES[tier]}")
        
        self.add_item(discord.ui.TextInput(
            label=f"Gõ 'XAC NHAN' để mua gói {cost:,} Hạt",
            placeholder="XAC NHAN",
            required=True,
            max_length=10
        ))
    
    async def on_submit(self, interaction):
        if self.children[0].value.upper() != "XAC NHAN":
            return await interaction.response.send_message(
                "❌ Nhập sai! Vui lòng thử lại.",
                ephemeral=True
            )
        # Proceed with purchase...
```

**Change Location:** `cogs/vip_commands.py` - Add modal before `_process_purchase()`

---

### 2. VIP Expiry Reminder (3 Days Before) ✅ (DESIGN READY)

**Implementation:**

#### Task (runs daily at midnight):
```python
@tasks.loop(time=datetime.time(hour=0, minute=0))
async def check_vip_expiry_task(self):
    now = datetime.now(timezone.utc)
    three_days = now + timedelta(days=3)
    
    rows = await db_manager.fetchall(
        "SELECT user_id, tier_level, expiry_date "
        "FROM vip_subscriptions "
        "WHERE expiry_date BETWEEN $1 AND $2",
        (now, three_days)
    )
    
    for user_id, tier, expiry in rows:
        try:
            user = await self.bot.fetch_user(user_id)
            days_left = (expiry - now).days
            
            embed = discord.Embed(
                title="⚠️ VIP Sắp Hết Hạn",
                description=f"VIP {VIP_NAMES[tier]} của bạn còn **{days_left} ngày**!",
                color=0xFF6B6B
            )
            embed.add_field(
                name="Gia hạn ngay",
                value="Dùng `/thuongluu b` để gia hạn VIP.",
                inline=False
            )
            
            await user.send(embed=embed)
            logger.info(f"[VIP_REMINDER] Sent to user {user_id}")
        except Exception as e:
            logger.error(f"[VIP_REMINDER] Failed for {user_id}: {e}")
```

**Add to:** `cogs/vip_commands.py`

---

### 3. Prorated Tier Upgrade Pricing 🟡 (COMPLEX)

**Current Behavior:**
- User buys Bạc (50k/30 days)
- 15 days later, buys Vàng (150k/30 days)
- Result: Tier upgraded, +30 days added (total 45 days)

**Problem:** User paid 200k for 45 days, but should get credit for unused Bạc time.

**Solution - Prorated Upgrade:**
```python
async def _calculate_prorated_price(user_id, new_tier):
    existing = await db_manager.fetchrow(
        "SELECT tier_level, expiry_date FROM vip_subscriptions WHERE user_id = $1",
        (user_id,)
    )
    
    if not existing:
        return VIP_PRICES[new_tier]  # No discount for new users
    
    old_tier, expiry = existing
    
    if old_tier >= new_tier:
        return VIP_PRICES[new_tier]  # Downgrade/same tier = full price
    
    # Calculate remaining value
    now = datetime.now(timezone.utc)
    days_left = (expiry - now).days
    
    if days_left <= 0:
        return VIP_PRICES[new_tier]  # Expired = full price
    
    # Credit = (old price / 30) * days_left
    daily_value = VIP_PRICES[old_tier] / 30
    credit = int(daily_value * days_left)
    
    # New price = full price - credit
    new_price = VIP_PRICES[new_tier] - credit
    
    return max(1, new_price)  # Minimum 1 seed
```

**Add to:** `cogs/vip_commands.py` - Call before `_process_purchase()`

**UI Update:** Show discount in purchase confirmation
```
Mua Vàng (150k/30 ngày)
Giảm giá: -45k (15 ngày Bạc còn lại)
Tổng thanh toán: 105k
```

---

## TESTING CHECKLIST

### Phase 2:
- [ ] `/huyhieu` - Check badge tiers show correctly
- [ ] Top contributors display prestige badges
- [ ] `/cay` leaderboard shows badges next to names

### Phase 3:
- [ ] VIP purchase shows confirmation modal
- [ ] Modal rejects wrong input
- [ ] Modal accepts "XAC NHAN" and proceeds
- [ ] VIP expiry reminder sends DM 3 days before
- [ ] Prorated upgrade calculates discount correctly
- [ ] Upgrade from Bạc→Vàng after 15 days = 105k (not 150k)

---

## FINAL RECOMMENDATIONS

### Critical Bugs Fixed:
1. ✅ SQL placeholder mismatch (`?` vs `$1`)

### High-Priority Features (Implement Next):
1. **VIP Purchase Confirmation Modal** - Prevents accidental purchases
2. **VIP Expiry Reminder** - Improves retention
3. **Prestige Badges Testing** - Already coded, needs validation

### Medium-Priority Features:
1. **Prorated Upgrade** - Fairness + UX improvement
2. **Friend System** - Social engagement boost

### Low-Priority Features:
1. **Gift Enhancements** - Nice-to-have, not critical

---

## IMPLEMENTATION TIME ESTIMATES

| Feature | Complexity | Time | Priority |
|---------|------------|------|----------|
| Confirmation Modal | Low | 30 min | High |
| Expiry Reminder | Medium | 1 hour | High |
| Prestige Testing | Low | 30 min | High |
| Prorated Upgrade | High | 2-3 hours | Medium |
| Friend System | Very High | 6-8 hours | Medium |
| Gift Enhancements | Medium | 2-3 hours | Low |

**Total High-Priority:** ~2 hours
**Total Medium-Priority:** ~12 hours
**Total Low-Priority:** ~3 hours

---

## CODE QUALITY ISSUES FOUND

### 1. Hybrid Database Architecture
- **SQLite**: Legacy tables (`users`, `server_config`)
- **PostgreSQL**: New tables (`vip_subscriptions`, `baucua_daily_stats`)
- **Issue**: `db_manager` auto-converts `?` to `$n` but inconsistent usage
- **Fix**: Standardize on PostgreSQL placeholders (`$1`, `$2`)

### 2. Transaction Patterns
- ✅ **Good**: `cogs/vip_commands.py` uses `FOR UPDATE` lock
- ✅ **Good**: Bầu Cua cashback uses separate task
- ⚠️ **Warning**: Tree auto-water runs for ALL guilds (could be slow for multi-guild bots)

### 3. Performance Optimizations Needed
- User caching in Tree contributors (DONE - uses `tree_manager.get_user_cached()`)
- VIP data caching (DONE - 5-minute TTL in `VIPEngine`)

---

## DEPLOYMENT PLAN

1. **Immediate (Today):**
   - Test prestige badges (`/huyhieu`)
   - Fix any runtime errors in tree helpers

2. **This Week:**
   - Add confirmation modal
   - Add expiry reminder task
   - Test prorated upgrades

3. **Next Week:**
   - Implement friend system (if time permits)
   - Add gift tracking

4. **Future:**
   - VIP-only chat channels
   - Custom Discord roles for prestige tiers
   - Seasonal VIP events

---

**Status:** Phase 1 COMPLETE, Phase 2 PARTIAL, Phase 3 PLANNED
**Next Action:** Restart bot, test `/huyhieu` command, then implement UX improvements
