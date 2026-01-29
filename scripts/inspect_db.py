import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def inspect_schema():
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        print("❌ DATABASE_URL not found in env")
        return

    try:
        conn = await asyncpg.connect(dsn)
        print(f"✅ Connected to {dsn.split('@')[1]}")
        
        tables = ['cog_config', 'users', 'active_events', 'auto_fishing']
        
        for table in tables:
            print(f"\n--- Table: {table} ---")
            columns = await conn.fetch(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            
            if not columns:
                print("❌ Table not found!")
            else:
                for col in columns:
                    print(f"  - {col['column_name']}: {col['data_type']} ({'Null' if col['is_nullable']=='YES' else 'Not Null'})")
                    
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
