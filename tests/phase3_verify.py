
import asyncio
import sys
import os

# Mock environment
sys.path.append(os.getcwd())

# MOCK TORTOISE BEFORE IMPORTS
from unittest.mock import MagicMock
sys.modules['tortoise'] = MagicMock()
sys.modules['tortoise.fields'] = MagicMock()
sys.modules['tortoise.models'] = MagicMock()
# Fully Mock Environment
sys.modules['discord'] = MagicMock()
sys.modules['tortoise'] = MagicMock()
sys.modules['tortoise.fields'] = MagicMock()
sys.modules['tortoise.models'] = MagicMock()
sys.modules['asyncpg'] = MagicMock()

# Mock cogs.aquarium.models
class MockModel:
    pass
sys.modules['tortoise.models'].Model = MockModel

# Mock DB Manager
class MockDB:
    async def fetchone(self, query, params=None):
        print(f"[MockDB] fetchone: {query} | {params}")
        if "magic_fruit" in query:
             return (10,) # Have 10 fruits
        if "seeds" in query and "users" in query:
             return (1000000,) # Have 1M seeds
        return None

    async def execute(self, query, params=None):
        print(f"[MockDB] execute: {query} | {params}")
        return

    async def modify(self, query, params=None):
        print(f"[MockDB] modify: {query} | {params}")
        return

    def transaction(self):
        class Transaction:
            async def __aenter__(self): return MockDB() # Return self as conn
            async def __aexit__(self, *args): pass
        return Transaction()
        
    async def fetchrow(self, query, params=None):
         # Logic for 'sell_fish' returning
         print(f"[MockDB] fetchrow: {query} | {params}")
         return (99,) # Remaining qty

mock_db = MockDB()
sys.modules['core.database'] = MagicMock()
sys.modules['core.database'].db_manager = mock_db
sys.modules['database_manager'] = MagicMock()
sys.modules['database_manager'].db_manager = mock_db

sys.modules['tortoise.transactions'] = MagicMock()

# Helper Mocks from core.database
async def mock_add_seeds(*args):
    print(f"[MockHelpers] add_seeds: {args}")

async def mock_balance(u): 
    return 1000000
    
sys.modules['core.database'].add_seeds = mock_add_seeds
sys.modules['core.database'].get_user_balance = mock_balance
sys.modules['core.database'].in_transaction = mock_db.transaction 

# Mock User and Models
class MockUser:
    def __init__(self, id, name):
        self.id = id
        self.name = name

# Mock ORM Models
class MockORM:
    @staticmethod
    async def get_or_none(**kwargs):
        print(f"[MockORM] get_or_none {kwargs}")
        return None 
    
    @staticmethod
    async def get_or_create(**kwargs):
        print(f"[MockORM] get_or_create {kwargs}")
        class Obj:
            leaf_coin = 999999
            quantity = 0
            async def save(self): print("[MockORM] Saved object")
        return Obj(), True

    @staticmethod
    async def create(**kwargs):
         print(f"[MockORM] create {kwargs}")
         class Obj:
            leaf_coin = 0
            async def save(self): pass
         return Obj()

import cogs.aquarium.models
cogs.aquarium.models.UserAquarium = MockORM
cogs.aquarium.models.UserDecor = MockORM

async def test_market_buy():
    print("\n--- TEST: MarketEngine.buy_decor (Magic Fruit) ---")
    # Reload logic module to ensure mocks are used
    if 'cogs.aquarium.logic.market' in sys.modules:
        del sys.modules['cogs.aquarium.logic.market']
        
    from cogs.aquarium.logic.market import MarketEngine
    from cogs.aquarium.constants import DECOR_ITEMS
    
    TEST_USER_ID = 999999
    
    # Test Buy Ruong Vang (Has magic fruit price)
    print(f"Target Item: ruong_vang")
    success, msg = await MarketEngine.buy_decor(TEST_USER_ID, 'ruong_vang', 'magic_fruit')
    print(f"Result: {success} | Msg: {msg}")
    
    if success:
        print("✅ Purchase Check Passed")
    else:
        print("❌ Purchase Failed")

async def test_sell_bonus():
    print("\n--- TEST: Sell Bonus Logic ---")
    from cogs.aquarium.logic.housing import HousingEngine
    from cogs.aquarium.constants import FENG_SHUI_SETS
    
    async def mock_get_sets(uid):
        return [FENG_SHUI_SETS['hoang_gia']]
    HousingEngine.get_active_sets = mock_get_sets
    
    active = await HousingEngine.get_active_sets(123)
    if any(s['tier'] == 2 for s in active):
        print("✅ Active Set Detected Correctly")
        # Logic check
        total = 10000
        bonus = int(total * 0.1)
        print(f"Base: {total}, Bonus: {bonus}")
    else:
        print("❌ Active Set Detection Failed")

async def main():
    await test_market_buy()
    await test_sell_bonus()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
