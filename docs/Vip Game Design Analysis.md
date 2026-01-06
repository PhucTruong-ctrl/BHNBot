# 🎮 BHNBot VIP System - Unified Game Design (v3.0 - Unified Shop & Tournaments)
> **Design Principle**: VIP = **Convenience** + **Aesthetics** + **Prestige**, NOT Pay-to-Win
> **Latest Update**: Jan 2026 - Unified Shop & Tournament System Implemented
---
## 📊 CURRENT STATE ANALYSIS
### Tier Structure
| Tier | Name | Price | Duration | Color | Status |
|------|------|-------|----------|-------|--------|
| 0 | Member | Free | ∞ | Blue | Default |
| 1 | Bạc (Silver) | 50k Hạt | 30d | `#BDC3C7` | Entry Luxury |
| 2 | Vàng (Gold) | 150k Hạt | 30d | `#F1C40F` | Premium |
| 3 | Kim Cương (Diamond) | 500k Hạt | 30d | `#3498DB` | Ultimate |
### Active Perks (Fishing Only)
- ✅ Custom colors, prefixes, footer quotes
- ✅ Merchant themes (Sạp Cá → Tập Đoàn)
- ✅ Tier 3: Auto-recycle trash → Leaf Coin
- ✅ Tier 2+: Auto-sell when full bucket
- ✅ **Unified Shop**: Buy Rod Upgrades, Decor, Consumables in one place
- ✅ **Tournaments**: Host/Join VIP tournaments with real-time scoring
### Critical Gaps
| Module | Current VIP Support | Missing |
|--------|---------------------|---------|
| 🎣 Fishing | **COMPLETE** | None (Polished) |
| 🛍️ Shop | **COMPLETE** | None (Unified) |
| 🎲 Bầu Cua | Partial (Visuals) | Cashback, Cosmetics |
| 🌳 Cây Server | Partial (Visuals) | Gardener perks, Auto-water |
| 🐠 Aquarium | Partial (Decor) | Themes, Animated backgrounds |
| 💬 Nói Tứ | ❌ None | Hints, streak protection |
---
## 🎯 DESIGN PHILOSOPHY (REVISED)
### 1. Robustness First (New)
- **Self-Healing Caches**: If the bot loses track of a state (e.g. tournament participant), it MUST check the database automatically.
- **ACID Transactions**: Every exchange of value (Hạt/Fish/Decor) MUST be atomic.
- **Persistence**: All active states (Tournaments, Giveaways) MUST survive bot restarts.
### 2. Simplicity Over Complexity
- **Unified Shop**: 1 command (`/shop`) replaces scattered buy commands.
- **Smart Context**: `!banca` automatically detects tournament status and updates score. No separate `!tournament_sell`.
- **Public Announcements**: Feature upgrades like "Winner Announcement" happen automatically in the correct channel.
---
## 💎 COMPLETED MODULES (Jan 2026)
### 🛍️ A. UNIFIED SHOP SYSTEM
**Location**: `cogs/unified_shop`
**Architect**: `ShopManager` (Singleton)
#### Features:
- **Centralized UI**: `/shop` opens a category view (Items, Tools, Decor, VIP).
- **Dynamic Rod Upgrades**: "Upgrade Cần" item appears dynamically based on user's current rod level.
- **Multi-Currency**: Supports **Hạt** (Seeds) and **Xu Lá** (Leaf Coins) seamlessly.
- **Set Grouping**: Decor items are sorted by Sets (e.g., "Bộ Rạn San Hô") for cleaner UI.
- **Transaction Logs**: Every purchase is logged to `transaction_logs` for audit.
#### Architecture:
```python
class ShopController:
    async def process_purchase(user, item, quantity):
        # 1. Validation (Balance, Inventory limits)
        # 2. ACID Transaction (Deduct Currency -> Add Item -> Log)
        # 3. Webhook/Event dispatch
🏆 B. VIP TOURNAMENT SYSTEM
Location: cogs/fishing/tournament.py Architect: TournamentManager (Singleton + Self-Healing)

Features:
Creation: /giaidau create [fee] (Host pays fee, sets prize pool).
Joining: /giaidau join [id] (Players pay fee, prize pool increases).
Ranking: /giaidau rank (Live leaderboard with Discord Relative Timestamps <t:timestamp:R>).
Real-Time Scoring: !banca updates score instantly.
Auto-End: Watchdog checks expired tournaments every minute.
Public Announcement: Winner announced with Embed in the hosting channel.
Robustness Mechanisms:
State Restoration: On bot load, queries DB for status='active' and rebuilds memory cache.
Self-Healing Cache: If update_score is called for a user NOT in cache, it double-checks DB. If found, it RESTORES the user to cache and proceeds. (Fixes "Ghost Player" bug).
Channel Persistence: Stores channel_id to ensure announcements find their home even after restarts.
📋 IMPLEMENTATION PRIORITY
Phase 1: Cosmetic Unification (COMPLETED)
 Apply VIP embed styling
Phase 2: Fishing Expansion (COMPLETED)
 VIP-Only Fish Pool
 Premium Consumables
Phase 3: Tournaments & Content (COMPLETED ✅)
 VIP Tournament System (Robust, Persisted)
 Unified Shop (Multi-currency, Decor, Rods)
 Decor Implementation (Sets, Effects)
Phase 4: Social Features (NEXT)
 Prestige Badges (Tree)
 Friend/Neighbor System
 Gifting System (/gift)
Phase 5: Cross-Module Synergies
 Link Tree → Aquarium (Magic Fruit)
 Link Bầu Cua → Fishing (Lucky Bait)
🛠️ TECHNICAL DEBT RESOLVED
1. Singleton Initialization Bug
Issue: TournamentManager.__init__ returned a value (forbidden).
Fix: Implemented proper get_instance() classmethod and removed return from __init__.
2. Timezone/Timestamp Confusion
Issue: Python datetime.timestamp() on naive objects used Local Time, causing "7 hours ago" errors.
Fix: Forced tzinfo=timezone.utc before timestamp conversion.
3. Silent Failures
Issue: Tournament ended silently in background.
Fix: Added channel_id persistence and bot injection to enable public channel.send() announcements.
🎯 UPDATED SUCCESS METRICS
Conversion KPIs
Metric	Status
Shop Usage	High (Primary interaction point)
Tournament Engagement	Testing Phase (Self-Healing verified)
Economy Stability	Stable (Transaction Logs enforce auditability)
Signed: Antigravity (Lead Architect) Status: Phase 3 COMPLETE. Ready for Phase 4.

Batch processing with rate limiting
async def process_vip_auto_actions(): vip_users = await get_all_active_vips()

# Process in batches of 50
for batch in chunks(vip_users, 50):
    await asyncio.gather(*[
        auto_visit_neighbors(user) for user in batch
    ])
    await asyncio.sleep(1)  # Rate limit between batches
**Verdict**: ✅ FEASIBLE - Use `apscheduler` with batch limits (50 users/batch, 1s delay)
---
## 🚀 PRE-IMPLEMENTATION Q&A
### Q1: Cashback Retroactivity
**Question**: User loses 100k today, buys VIP tomorrow. Do they get cashback for yesterday's losses?
**Answer**: ❌ **NO - Cashback only applies to losses during active VIP period**
**Rationale**:
- Prevents "loss farming" exploits (intentionally lose big, then buy VIP)
- Simpler implementation (no historical tracking)
- Clear UX: "VIP benefits start NOW"
**Implementation**:
```python
# Reset cashback tracker on VIP purchase
if newly_subscribed:
    await set_stat(user_id, "vip", "daily_losses", 0)
    
# Only track losses while VIP active
if await is_vip_active(user_id):
    await increment_stat(user_id, "vip", "daily_losses", bet_amount)
Q2: Hint Mechanism (Nói Tứ)
Question: Where does /nthint get word suggestions from? AI or dictionary?

Answer: ✅ Dictionary-based random selection (NO AI)

Rationale:

AI is slow (200-500ms latency)
AI costs tokens (unnecessary expense)
Dictionary is instant and deterministic
Implementation:

async def generate_hint(current_syllable: str) -> str:
    # Load pre-indexed dictionary
    valid_words = WORD_DICT.get(current_syllable, [])
    
    if not valid_words:
        return "Không tìm thấy gợi ý!"
    
    # Return random word
    import random
    return random.choice(valid_words)
Example:

Current word ends with "ng"
User types /nthint
Bot responds (ephemeral): "Gợi ý: ngọc" (or "nga", "nghệ", etc.)
Q3: Tier Downgrade Slot Handling
Question: User has Tier 3 (3 decor slots), downgrades to Tier 1 (1 slot). What happens to Slot 2 & 3 items?

Answer: ✅ Soft Lock - Items visible but uneditable

Behavior:

Action	Allowed?	Result
View house	✅ Yes	All 3 slots visible with decorations
Remove Slot 2/3 decor	❌ No	Error: "Cần VIP Tier 2+ để chỉnh sửa"
Add new to Slot 2/3	❌ No	Same error
Replace Slot 2/3	❌ No	Same error
Edit Slot 1	✅ Yes	Works normally
Rationale:

No data loss (user doesn't lose decorations)
Visual reminder of what they had (incentivizes re-subscribing)
Fair: They paid for those items, shouldn't be deleted
Implementation:

async def can_edit_slot(user_id: int, slot_number: int) -> bool:
    vip_tier = await get_vip_tier(user_id)
    
    # Slot 1: Everyone
    # Slot 2: Tier 2+
    # Slot 3: Tier 3
    required_tier = min(slot_number, 3)
    
    return vip_tier >= required_tier
UI Feedback:

/trangtri
🏠 NHÀ CỦA BẠN
Slot 1: 🪸 San Hô [Chỉnh sửa]
Slot 2: 👑 Vương Miện [🔒 Cần VIP Tier 2+]
Slot 3: 💎 Pha Lê [🔒 Cần VIP Tier 3]
💬 FINAL RECOMMENDATIONS
Top 5 Must-Haves (Month 1)
Cosmetic Unification: All modules get VIP embeds
Cashback System: Makes gambling less punishing
Auto-Actions: Auto-sell, Auto-visit, Auto-water
VIP-Only Fish: Creates FOMO without P2W
Total VIP Days Tracker: Drives renewals
Nice-to-Haves (Month 2-3)
Animated themes (Aquarium)
VIP tournaments (Fishing)
Cross-module synergies (Tree → Aquarium)
Deep Cuts (Month 4+)
Machine learning for personalized VIP offers
Seasonal exclusive content rotations
VIP-only world events
📐 DESIGN VERDICT
Original System: C+ (6/10)
Good foundation (tier structure, fishing visuals)
Major gaps (no other modules, thin perks)
Redesigned System: A (9.5/10)
✅ Unified across all modules
✅ Anti-P2W compliant
✅ Convenience + Aesthetics focused
✅ Cross-module synergies
✅ Sustainable economy
TL;DR: VIP giờ không chỉ "ngon mắt" mà còn "ngon tay" ở MỌI module. Không P2W, chỉ flex + tiện lợi. Balance giữa Whales (Tier 3 all-in) và Casuals (Tier 1 affordable).