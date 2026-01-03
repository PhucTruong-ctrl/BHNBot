
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def analyze():
    try:
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "discord_bot"),
            password=os.getenv("DB_PASSWORD", "discord_bot_password"),
            database=os.getenv("DB_NAME", "discord_bot_db"),
            host=os.getenv("DB_HOST", "localhost")
        )
        print("--- TOTAL SUPPLY ---")
        total = await conn.fetchval("SELECT SUM(seeds) FROM users")
        print(f"Total: {total}")
        
        print("\n--- WHALES (>5%) ---")
        # Calc 5%
        # Fix Decimal Error
        threshold = float(total) * 0.05
        print(f"Threshold: {threshold}")
        whales = await conn.fetch("SELECT username, seeds FROM users WHERE seeds > $1 ORDER BY seeds DESC", threshold)
        for w in whales:
            print(f"- {w['username']}: {w['seeds']} ({w['seeds']/float(total)*100:.2f}%)")

        print("\n--- DISTRIBUTION ---")
        dist = await conn.fetch("""
            SELECT 
            CASE 
                WHEN seeds < 100 THEN 'Nghèo (<100)'
                WHEN seeds < 500 THEN 'Bình dân (100-500)'
                WHEN seeds < 2000 THEN 'Trung lưu (500-2K)'
                WHEN seeds < 10000 THEN 'Giàu (2K-10K)'
                ELSE 'Đại gia (>10K)'
            END as bracket,
            COUNT(*) as count
            FROM users
            GROUP BY bracket
        """)
        for d in dist:
            print(f"{d['bracket']}: {d['count']}")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(analyze())
