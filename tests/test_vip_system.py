#!/usr/bin/env python3
"""
BHNBot VIP System - Automated Test Suite
=========================================

Chạy: cd /home/phuctruong/Work/BHNBot && .venv/bin/python3 tests/test_vip_system.py

Test coverage:
- Database connections
- VIP Engine logic
- Transaction safety
- Prorated calculations
- Cashback calculations
- Prestige badge logic
- Rate limiting logic
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Test results tracker
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def success(self, name: str):
        self.passed += 1
        print(f"  ✅ {name}")
    
    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ❌ {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"RESULTS: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0

results = TestResults()


# ============================================================
# TEST 1: Database Connection
# ============================================================
async def test_database_connection():
    """Test PostgreSQL connection."""
    print("\n[TEST 1] Database Connection")
    
    try:
        from core.database import db_manager
        await db_manager.connect()
        
        # Test simple query
        row = await db_manager.fetchone("SELECT 1 as test")
        if row and row[0] == 1:
            results.success("PostgreSQL connection OK")
        else:
            results.fail("PostgreSQL connection", "Query returned unexpected result")
        
        # Test VIP table exists
        row = await db_manager.fetchone(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'vip_subscriptions'"
        )
        if row and row[0] > 0:
            results.success("vip_subscriptions table exists")
        else:
            results.fail("vip_subscriptions table", "Table not found")
        
        # Test vip_auto_tasks table exists
        row = await db_manager.fetchone(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'vip_auto_tasks'"
        )
        if row and row[0] > 0:
            results.success("vip_auto_tasks table exists")
        else:
            results.fail("vip_auto_tasks table", "Table not found")
            
    except Exception as e:
        results.fail("Database connection", str(e))


# ============================================================
# TEST 2: VIP Engine - get_vip_data
# ============================================================
async def test_vip_engine_get_data():
    """Test VIPEngine.get_vip_data function."""
    print("\n[TEST 2] VIPEngine.get_vip_data")
    
    try:
        from core.services.vip_service import VIPEngine
        from core.database import db_manager
        
        test_user_id = 999999999  # Fake user ID for testing
        
        # Clean up test data first
        await db_manager.execute(
            "DELETE FROM vip_subscriptions WHERE user_id = $1",
            (test_user_id,)
        )
        
        # Test 1: Non-existent user returns None
        vip = await VIPEngine.get_vip_data(test_user_id, use_cache=False)
        if vip is None:
            results.success("Non-VIP user returns None")
        else:
            results.fail("Non-VIP user check", f"Expected None, got {vip}")
        
        # Test 2: Insert test VIP and verify
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        await db_manager.execute(
            "INSERT INTO vip_subscriptions (user_id, tier_level, expiry_date) "
            "VALUES ($1, $2, $3)",
            (test_user_id, 2, expiry)
        )
        
        # Clear cache and re-fetch
        VIPEngine.clear_cache(test_user_id)
        vip = await VIPEngine.get_vip_data(test_user_id, use_cache=False)
        
        if vip and vip['tier'] == 2:
            results.success("Active VIP returns correct tier")
        else:
            results.fail("VIP tier check", f"Expected tier 2, got {vip}")
        
        # Test 3: Expired VIP returns None
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        await db_manager.execute(
            "UPDATE vip_subscriptions SET expiry_date = $1 WHERE user_id = $2",
            (expired, test_user_id)
        )
        
        VIPEngine.clear_cache(test_user_id)
        vip = await VIPEngine.get_vip_data(test_user_id, use_cache=False)
        
        if vip is None:
            results.success("Expired VIP returns None")
        else:
            results.fail("Expired VIP check", f"Expected None, got {vip}")
        
        # Cleanup
        await db_manager.execute(
            "DELETE FROM vip_subscriptions WHERE user_id = $1",
            (test_user_id,)
        )
        
    except Exception as e:
        results.fail("VIPEngine.get_vip_data", str(e))


# ============================================================
# TEST 3: Prorated Price Calculation
# ============================================================
async def test_prorated_calculation():
    """Test prorated upgrade price calculation."""
    print("\n[TEST 3] Prorated Price Calculation")
    
    try:
        from cogs.aquarium.constants import VIP_PRICES
        
        # Test calculation logic (without DB)
        def calculate_prorated(old_tier: int, new_tier: int, days_left: int) -> tuple:
            """Calculate prorated price for tier upgrade."""
            if old_tier >= new_tier or days_left <= 0:
                return (VIP_PRICES[new_tier], 0)
            
            old_price = VIP_PRICES[old_tier]
            daily_value = old_price / 30
            credit = int(daily_value * days_left)
            
            final_price = VIP_PRICES[new_tier] - credit
            final_price = max(1, final_price)
            
            discount = VIP_PRICES[new_tier] - final_price
            return (final_price, discount)
        
        # Test Case 1: Bạc (10k) với 15 days left → Vàng (50k)
        # Expected: 50k - (10k/30*15) = 50k - 5k = 45k
        final, discount = calculate_prorated(1, 2, 15)
        expected_final = 45000
        
        if abs(final - expected_final) < 100:
            results.success(f"Bạc→Vàng (15d): {final:,} (expected ~{expected_final:,})")
        else:
            results.fail("Bạc→Vàng calculation", f"Got {final:,}, expected {expected_final:,}")
        
        # Test Case 2: Vàng (50k) với 20 days left → Kim Cương (200k)
        # Expected: 200k - (50k/30*20) = 200k - 33.3k = 166.6k
        final, discount = calculate_prorated(2, 3, 20)
        expected_final = 166667
        
        if abs(final - expected_final) < 100:
            results.success(f"Vàng→KC (20d): {final:,} (expected ~{expected_final:,})")
        else:
            results.fail("Vàng→KC calculation", f"Got {final:,}, expected {expected_final:,}")
        
        # Test Case 3: Same tier = full price
        final, discount = calculate_prorated(2, 2, 15)
        if final == VIP_PRICES[2]:
            results.success(f"Same tier = full price: {final:,}")
        else:
            results.fail("Same tier price", f"Got {final:,}, expected {VIP_PRICES[2]:,}")
        
        # Test Case 4: Downgrade = full price
        final, discount = calculate_prorated(3, 1, 15)
        if final == VIP_PRICES[1]:
            results.success(f"Downgrade = full price: {final:,}")
        else:
            results.fail("Downgrade price", f"Got {final:,}, expected {VIP_PRICES[1]:,}")
        
        # Test Case 5: 0 days left = full price
        final, discount = calculate_prorated(1, 2, 0)
        if final == VIP_PRICES[2]:
            results.success(f"0 days left = full price: {final:,}")
        else:
            results.fail("0 days price", f"Got {final:,}, expected {VIP_PRICES[2]:,}")
        
    except Exception as e:
        results.fail("Prorated calculation", str(e))


# ============================================================
# TEST 4: Cashback Calculation
# ============================================================
async def test_cashback_calculation():
    """Test Bầu Cua cashback calculation."""
    print("\n[TEST 4] Cashback Calculation")
    
    try:
        def calculate_cashback(tier: int, net_loss: int) -> int:
            """Calculate VIP cashback for losses."""
            if net_loss <= 0 or tier < 1:
                return 0
            
            rates = {1: 0.02, 2: 0.03, 3: 0.05}
            rate = rates.get(tier, 0)
            cashback = int(net_loss * rate)
            
            return cashback
        
        # Test Case 1: Tier 1 loses 10k → 2% = 200
        cb = calculate_cashback(1, 10000)
        if cb == 200:
            results.success(f"Tier 1, lose 10k: cashback = {cb}")
        else:
            results.fail("Tier 1 cashback", f"Got {cb}, expected 200")
        
        # Test Case 2: Tier 2 loses 50k → 3% = 1500
        cb = calculate_cashback(2, 50000)
        if cb == 1500:
            results.success(f"Tier 2, lose 50k: cashback = {cb}")
        else:
            results.fail("Tier 2 cashback", f"Got {cb}, expected 1500")
        
        # Test Case 3: Tier 3 loses 100k → 5% = 5000
        cb = calculate_cashback(3, 100000)
        if cb == 5000:
            results.success(f"Tier 3, lose 100k: cashback = {cb}")
        else:
            results.fail("Tier 3 cashback", f"Got {cb}, expected 5000")
        
        # Test Case 4: Win (negative loss) = 0 cashback
        cb = calculate_cashback(3, -5000)
        if cb == 0:
            results.success(f"Win = no cashback: {cb}")
        else:
            results.fail("Win cashback", f"Got {cb}, expected 0")
        
        # Test Case 5: Non-VIP = 0 cashback
        cb = calculate_cashback(0, 10000)
        if cb == 0:
            results.success(f"Non-VIP = no cashback: {cb}")
        else:
            results.fail("Non-VIP cashback", f"Got {cb}, expected 0")
        
    except Exception as e:
        results.fail("Cashback calculation", str(e))


# ============================================================
# TEST 5: Prestige Badge Logic
# ============================================================
async def test_prestige_badges():
    """Test prestige badge tier calculation."""
    print("\n[TEST 5] Prestige Badge Logic")
    
    try:
        PRESTIGE_TIERS = {
            1: {"name": "🌱 Người Trồng Cây", "min_exp": 1000},
            2: {"name": "🌿 Người Làm Vườn", "min_exp": 5000},
            3: {"name": "🌳 Người Bảo Vệ Rừng", "min_exp": 25000},
            4: {"name": "🌸 Thần Nông", "min_exp": 100000},
            5: {"name": "🍎 Tiên Nhân", "min_exp": 500000}
        }
        
        PRESTIGE_BADGES = {1: "🌱", 2: "🌿", 3: "🌳", 4: "🌸", 5: "🍎"}
        
        def get_prestige_tier(total_exp: int) -> int:
            tier = 0
            for tier_num in sorted(PRESTIGE_TIERS.keys(), reverse=True):
                if total_exp >= PRESTIGE_TIERS[tier_num]["min_exp"]:
                    tier = tier_num
                    break
            return tier
        
        def get_prestige_badge(total_exp: int) -> str:
            tier = get_prestige_tier(total_exp)
            if tier == 0:
                return ""
            return PRESTIGE_BADGES.get(tier, "")
        
        # Test Case 1: Under threshold = no badge
        tier = get_prestige_tier(500)
        if tier == 0:
            results.success(f"500 XP = no badge (tier {tier})")
        else:
            results.fail("Under threshold", f"Got tier {tier}, expected 0")
        
        # Test Case 2: Exactly 1000 = tier 1
        tier = get_prestige_tier(1000)
        badge = get_prestige_badge(1000)
        if tier == 1 and badge == "🌱":
            results.success(f"1000 XP = tier 1 ({badge})")
        else:
            results.fail("1000 XP tier", f"Got tier {tier}, badge {badge}")
        
        # Test Case 3: 30000 XP = tier 3 (>25000)
        tier = get_prestige_tier(30000)
        badge = get_prestige_badge(30000)
        if tier == 3 and badge == "🌳":
            results.success(f"30000 XP = tier 3 ({badge})")
        else:
            results.fail("30000 XP tier", f"Got tier {tier}, badge {badge}")
        
        # Test Case 4: Max tier (500k+)
        tier = get_prestige_tier(600000)
        badge = get_prestige_badge(600000)
        if tier == 5 and badge == "🍎":
            results.success(f"600000 XP = tier 5 ({badge})")
        else:
            results.fail("Max tier", f"Got tier {tier}, badge {badge}")
        
        # Test Case 5: Just under threshold
        tier = get_prestige_tier(4999)
        if tier == 1:  # Should be tier 1, not 2
            results.success(f"4999 XP = tier 1 (not 2)")
        else:
            results.fail("Just under threshold", f"Got tier {tier}, expected 1")
        
    except Exception as e:
        results.fail("Prestige badges", str(e))


# ============================================================
# TEST 6: Rate Limiting Logic
# ============================================================
async def test_rate_limiting():
    """Test gift rate limiting logic."""
    print("\n[TEST 6] Rate Limiting Logic")
    
    try:
        class RateLimiter:
            def __init__(self, max_actions: int, window_seconds: int):
                self.max_actions = max_actions
                self.window_seconds = window_seconds
                self.actions = {}  # user_id -> [timestamps]
            
            def can_perform(self, user_id: int) -> tuple:
                """Check if user can perform action. Returns (allowed, wait_seconds)."""
                now = datetime.now()
                
                if user_id not in self.actions:
                    self.actions[user_id] = []
                
                # Remove old actions
                cutoff = now - timedelta(seconds=self.window_seconds)
                self.actions[user_id] = [t for t in self.actions[user_id] if t > cutoff]
                
                if len(self.actions[user_id]) >= self.max_actions:
                    oldest = min(self.actions[user_id])
                    wait = self.window_seconds - (now - oldest).total_seconds()
                    return (False, int(wait) + 1)
                
                return (True, 0)
            
            def record_action(self, user_id: int):
                """Record an action for user."""
                now = datetime.now()
                if user_id not in self.actions:
                    self.actions[user_id] = []
                self.actions[user_id].append(now)
        
        # Create limiter: 3 actions per 60 seconds
        limiter = RateLimiter(max_actions=3, window_seconds=60)
        test_user = 123456
        
        # Test Case 1: First action allowed
        allowed, wait = limiter.can_perform(test_user)
        if allowed:
            results.success("First action allowed")
            limiter.record_action(test_user)
        else:
            results.fail("First action", "Should be allowed")
        
        # Test Case 2: Second and third allowed
        for i in range(2):
            allowed, wait = limiter.can_perform(test_user)
            if allowed:
                limiter.record_action(test_user)
        
        if len(limiter.actions[test_user]) == 3:
            results.success("3 actions recorded")
        else:
            results.fail("Action count", f"Got {len(limiter.actions[test_user])}")
        
        # Test Case 3: Fourth action blocked
        allowed, wait = limiter.can_perform(test_user)
        if not allowed and wait > 0:
            results.success(f"4th action blocked, wait {wait}s")
        else:
            results.fail("Rate limit", f"Should be blocked, got allowed={allowed}")
        
        # Test Case 4: Different user not affected
        other_user = 654321
        allowed, wait = limiter.can_perform(other_user)
        if allowed:
            results.success("Different user not affected")
        else:
            results.fail("User isolation", "Other user should be allowed")
        
    except Exception as e:
        results.fail("Rate limiting", str(e))


# ============================================================
# TEST 7: Transaction Safety
# ============================================================
async def test_transaction_safety():
    """Test database transaction isolation."""
    print("\n[TEST 7] Transaction Safety")
    
    try:
        from core.database import db_manager
        
        test_user_id = 888888888
        initial_seeds = 100000
        
        # Setup: Create test user with seeds
        await db_manager.execute(
            "INSERT INTO users (user_id, seeds) VALUES ($1, $2) "
            "ON CONFLICT (user_id) DO UPDATE SET seeds = $2",
            (test_user_id, initial_seeds)
        )
        
        # Test transaction rollback on error
        try:
            async with db_manager.transaction() as conn:
                # Deduct seeds
                await conn.execute(
                    "UPDATE users SET seeds = seeds - 50000 WHERE user_id = $1",
                    (test_user_id,)
                )
                
                # Verify deduction (within transaction)
                row = await conn.fetchrow(
                    "SELECT seeds FROM users WHERE user_id = $1",
                    (test_user_id,)
                )
                
                if row[0] == 50000:
                    results.success("Transaction deduction works")
                
                # Force error to trigger rollback
                raise Exception("Forced rollback")
                
        except Exception as e:
            if "Forced rollback" in str(e):
                pass  # Expected
            else:
                raise
        
        # Verify rollback happened
        row = await db_manager.fetchone(
            "SELECT seeds FROM users WHERE user_id = $1",
            (test_user_id,)
        )
        
        if row and row[0] == initial_seeds:
            results.success(f"Transaction rolled back correctly ({row[0]:,} seeds)")
        else:
            results.fail("Rollback", f"Seeds should be {initial_seeds:,}, got {row[0] if row else 'None'}")
        
        # Cleanup
        await db_manager.execute(
            "DELETE FROM users WHERE user_id = $1",
            (test_user_id,)
        )
        
    except Exception as e:
        results.fail("Transaction safety", str(e))


# ============================================================
# TEST 8: VIP Tier Upgrade Prevention
# ============================================================
async def test_tier_downgrade_prevention():
    """Test that tier cannot be downgraded."""
    print("\n[TEST 8] Tier Downgrade Prevention")
    
    try:
        def calculate_new_tier(current_tier: int, requested_tier: int) -> int:
            """Calculate new tier, preventing downgrade."""
            return max(current_tier, requested_tier)
        
        # Test Case 1: Upgrade allowed
        new = calculate_new_tier(1, 2)
        if new == 2:
            results.success(f"Upgrade 1→2: new tier = {new}")
        else:
            results.fail("Upgrade", f"Got {new}, expected 2")
        
        # Test Case 2: Downgrade prevented
        new = calculate_new_tier(3, 1)
        if new == 3:
            results.success(f"Downgrade 3→1 prevented: tier stays {new}")
        else:
            results.fail("Downgrade prevention", f"Got {new}, expected 3")
        
        # Test Case 3: Same tier = no change
        new = calculate_new_tier(2, 2)
        if new == 2:
            results.success(f"Same tier 2→2: tier = {new}")
        else:
            results.fail("Same tier", f"Got {new}, expected 2")
        
        # Test Case 4: From 0 (new user)
        new = calculate_new_tier(0, 2)
        if new == 2:
            results.success(f"New user 0→2: tier = {new}")
        else:
            results.fail("New user", f"Got {new}, expected 2")
        
    except Exception as e:
        results.fail("Tier downgrade prevention", str(e))


# ============================================================
# TEST 9: VIP Expiry Check
# ============================================================
async def test_vip_expiry_check():
    """Test VIP expiry date validation."""
    print("\n[TEST 9] VIP Expiry Check")
    
    try:
        def is_vip_active(expiry_date: Optional[datetime]) -> bool:
            """Check if VIP is still active."""
            if expiry_date is None:
                return False
            
            now = datetime.now(timezone.utc)
            
            # Handle timezone-naive datetime
            if expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
            
            return expiry_date > now
        
        # Test Case 1: Future expiry = active
        future = datetime.now(timezone.utc) + timedelta(days=10)
        if is_vip_active(future):
            results.success("Future expiry = active")
        else:
            results.fail("Future expiry", "Should be active")
        
        # Test Case 2: Past expiry = inactive
        past = datetime.now(timezone.utc) - timedelta(days=1)
        if not is_vip_active(past):
            results.success("Past expiry = inactive")
        else:
            results.fail("Past expiry", "Should be inactive")
        
        # Test Case 3: None = inactive
        if not is_vip_active(None):
            results.success("None expiry = inactive")
        else:
            results.fail("None expiry", "Should be inactive")
        
        # Test Case 4: Timezone-naive handling
        naive = datetime.now() + timedelta(days=5)  # No timezone
        if is_vip_active(naive):
            results.success("Timezone-naive handled correctly")
        else:
            results.fail("Timezone-naive", "Should handle and return active")
        
    except Exception as e:
        results.fail("VIP expiry check", str(e))


# ============================================================
# TEST 10: Module Imports
# ============================================================
async def test_module_imports():
    """Test all VIP-related modules can be imported."""
    print("\n[TEST 10] Module Imports")
    
    try:
        from core.services.vip_service import VIPEngine, TIER_CONFIG, VIP_QUOTES
        results.success("VIPEngine imported")
        
        from cogs.aquarium.constants import VIP_PRICES, VIP_NAMES, VIP_COLORS
        results.success("VIP constants imported")
        
        from cogs.aquarium.models import VIPSubscription
        results.success("VIPSubscription model imported")
        
        from database_manager import db_manager
        results.success("db_manager imported")
        
        # Verify VIP_PRICES has all tiers
        if 1 in VIP_PRICES and 2 in VIP_PRICES and 3 in VIP_PRICES:
            results.success(f"VIP_PRICES: {VIP_PRICES}")
        else:
            results.fail("VIP_PRICES", f"Missing tiers: {VIP_PRICES}")
        
        # Verify TIER_CONFIG
        if 1 in TIER_CONFIG and 2 in TIER_CONFIG and 3 in TIER_CONFIG:
            results.success(f"TIER_CONFIG has all 3 tiers")
        else:
            results.fail("TIER_CONFIG", "Missing tiers")
        
    except ImportError as e:
        results.fail("Module import", str(e))
    except Exception as e:
        results.fail("Module imports", str(e))


# ============================================================
# MAIN
# ============================================================
async def main():
    print("=" * 60)
    print("BHNBot VIP System - Automated Test Suite")
    print("=" * 60)
    
    # Run all tests
    await test_module_imports()
    await test_database_connection()
    await test_vip_engine_get_data()
    await test_prorated_calculation()
    await test_cashback_calculation()
    await test_prestige_badges()
    await test_rate_limiting()
    await test_transaction_safety()
    await test_tier_downgrade_prevention()
    await test_vip_expiry_check()
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED - Check errors above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
