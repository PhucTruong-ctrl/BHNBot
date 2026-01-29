# Database Migration Plan - BHNBot

**Objective:** Unify database layer from mixed SQLite/PostgreSQL to pure PostgreSQL with versioned migrations.

---

## Current State Analysis

### Dual-Database Mess
- **SQLite** (`data/database.db`): 268KB, legacy
- **PostgreSQL** (localhost:5432): New features (VIP, Aquarium)
- **Placeholder Hell**: Mix of `?` (SQLite) and `$1` (Postgres) in queries
- **Migration Strategy**: Ad-hoc `ensure_*_tables()` calls at startup

### Pain Points
1. **Cross-DB Transactions**: VIP deducts seeds (SQLite?) + updates VIP (Postgres) → no atomicity
2. **Schema Drift**: No single source of truth for schema
3. **Deployment Issues**: New instances need manual schema setup
4. **Type Confusion**: Developers don't know which placeholder to use

---

## Migration Strategy

### Phase 1: Preparation (1 week)

#### Step 1.1: Audit Current Usage (2 days)
```bash
# Find all ? placeholders
grep -r "SELECT.*?" cogs/ core/ database_manager.py > audit_sqlite_queries.txt

# Find all $1 placeholders  
grep -r "SELECT.*\$" cogs/ core/ database_manager.py > audit_postgres_queries.txt

# Compare schemas
sqlite3 data/database.db ".schema" > sqlite_schema.sql
pg_dump -s bhnbot_db > postgres_schema.sql
```

**Deliverable:** Spreadsheet mapping tables to DB engine

#### Step 1.2: Create Migration Framework (3 days)

**File:** `migrations/migration_runner.py`
```python
import asyncio
from core.database import db_manager
from core.logger import setup_logger

logger = setup_logger("Migrations", "migrations.log")

class Migration:
    version: int
    name: str
    
    async def up(self, conn):
        raise NotImplementedError
    
    async def down(self, conn):
        raise NotImplementedError

async def run_migrations():
    async with db_manager.transaction() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INT PRIMARY KEY,
                name VARCHAR(255),
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        applied = await conn.fetch("SELECT version FROM schema_migrations")
        applied_versions = {row['version'] for row in applied}
        
        import glob
        migration_files = sorted(glob.glob("migrations/0*.py"))
        
        for file in migration_files:
            version = int(file.split('/')[1].split('_')[0])
            
            if version in applied_versions:
                logger.info(f"Skipping migration {version} (already applied)")
                continue
            
            module = __import__(f"migrations.{file.split('/')[1][:-3]}", fromlist=['Migration'])
            migration = module.Migration()
            
            logger.info(f"Applying migration {version}: {migration.name}")
            await migration.up(conn)
            
            await conn.execute(
                "INSERT INTO schema_migrations (version, name) VALUES ($1, $2)",
                version, migration.name
            )
            logger.info(f"✓ Migration {version} applied")
```

**Example Migration:** `migrations/0001_initial_schema.py`
```python
from migration_runner import Migration

class Migration(Migration):
    version = 1
    name = "Initial PostgreSQL schema"
    
    async def up(self, conn):
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                seeds BIGINT DEFAULT 0 CHECK (seeds >= 0),
                last_daily TIMESTAMP,
                last_chat_reward TIMESTAMP
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_seeds ON users(seeds DESC)
        """)
    
    async def down(self, conn):
        await conn.execute("DROP TABLE IF EXISTS users")
```

#### Step 1.3: Standardize Placeholder Convention (1 day)

**File:** `docs/DB_CONVENTIONS.md`
```markdown
# Database Conventions

## MANDATORY RULES

1. **Always use PostgreSQL `$1, $2, ...` placeholders**
2. **Never use SQLite `?` placeholders** (except in legacy adaptor layer)
3. **All new queries must use asyncpg syntax**

## Query Template
```python
# CORRECT
result = await db_manager.fetchone(
    "SELECT * FROM users WHERE user_id = $1",
    user_id
)

# WRONG
result = await db_manager.fetchone(
    "SELECT * FROM users WHERE user_id = ?",
    (user_id,)
)
```
```

#### Step 1.4: Create SQLite → Postgres Data Migration Script (2 days)

**File:** `scripts/migrate_sqlite_to_postgres.py`
```python
import aiosqlite
import asyncpg
import asyncio

async def migrate_table(sqlite_path, pg_pool, table_name, columns):
    async with aiosqlite.connect(sqlite_path) as sqlite_db:
        async with pg_pool.acquire() as pg_conn:
            cursor = await sqlite_db.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
            rows = await cursor.fetchall()
            
            print(f"Migrating {len(rows)} rows from {table_name}...")
            
            placeholders = ', '.join([f"${i+1}" for i in range(len(columns))])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            await pg_conn.executemany(query, rows)
            print(f"✓ {table_name} migrated")

async def main():
    pg_pool = await asyncpg.create_pool(
        host='localhost', port=5432,
        user='postgres', password='password',
        database='bhnbot_db'
    )
    
    await migrate_table("data/database.db", pg_pool, "users", ["user_id", "username", "seeds"])
    await migrate_table("data/database.db", pg_pool, "inventory", ["user_id", "item_key", "quantity"])
    # ... all tables
    
    await pg_pool.close()
    print("✓ All data migrated!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Phase 2: Execution (2 weeks)

#### Step 2.1: Update database_manager.py (3 days)
1. Remove all `?` placeholder conversion logic
2. Update all internal queries to use `$n`
3. Add deprecation warnings for functions using old style
4. Update transaction proxy to use Postgres syntax only

#### Step 2.2: Update All Cogs (5 days)
**Systematic approach:**
```bash
# For each cog:
for cog in cogs/*/; do
    echo "Updating $cog"
    # Replace ? with numbered placeholders
    # Test with pytest
    # Commit
done
```

**Priority order:**
1. Economy (highest usage)
2. Shop
3. Fishing
4. Tree
5. Others

#### Step 2.3: Run Data Migration (1 day)
```bash
# 1. Backup everything
cp data/database.db data/database.db.backup
pg_dump bhnbot_db > postgres_backup.sql

# 2. Run migration
python scripts/migrate_sqlite_to_postgres.py

# 3. Verify row counts match
sqlite3 data/database.db "SELECT COUNT(*) FROM users"
psql bhnbot_db -c "SELECT COUNT(*) FROM users"
```

#### Step 2.4: Update main.py Startup (1 day)
```python
# Remove:
# await ensure_phase1_tables()
# await ensure_phase2_tables()
# ...

# Add:
from migrations.migration_runner import run_migrations
await run_migrations()
```

---

### Phase 3: Cleanup (1 week)

#### Step 3.1: Remove SQLite Dependencies (2 days)
```bash
# Remove aiosqlite from requirements.txt
# Remove sqlite3 imports
# Archive data/database.db to backups/
# Update README.md
```

#### Step 3.2: Performance Tuning (3 days)
```sql
-- Add composite indexes
CREATE INDEX idx_user_stats_composite ON user_stats(user_id, game_id, stat_key);
CREATE INDEX idx_inventory_user_item ON inventory(user_id, item_key);
CREATE INDEX idx_transaction_logs_user_time ON transaction_logs(user_id, created_at DESC);

-- Partition large tables
CREATE TABLE transaction_logs_2026_01 PARTITION OF transaction_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

#### Step 3.3: Documentation Update (1 day)
- Update `docs/COGS_REFERENCE.md` with new DB info
- Create `docs/SCHEMA.md` with full table definitions
- Update contribution guide with migration workflow

#### Step 3.4: Training \u0026 Handoff (1 day)
- Document rollback procedure
- Train team on new migration system
- Create troubleshooting guide

---

## Rollback Plan

### If Migration Fails During Phase 2:

```bash
# 1. Stop bot
pkill -f "python3 main.py"

# 2. Restore SQLite
cp data/database.db.backup data/database.db

# 3. Restore Postgres
dropdb bhnbot_db
createdb bhnbot_db
psql bhnbot_db < postgres_backup.sql

# 4. Revert code
git revert <migration_commit>

# 5. Restart bot
python3 main.py
```

### If Migration Fails After Phase 3:

```bash
# Use schema_migrations table to rollback
python migrations/migration_runner.py --rollback-to-version 5

# This will call down() methods in reverse order
```

---

## Testing Checklist

### Pre-Migration Tests
- [ ] All unit tests pass
- [ ] Bot runs on test instance
- [ ] Backup procedures verified
- [ ] Row counts documented

### Post-Migration Tests
- [ ] All queries use `$n` syntax
- [ ] No `aiosqlite` imports remain
- [ ] Row counts match pre-migration
- [ ] Economy transactions work (buy/sell/transfer)
- [ ] VIP subscriptions work
- [ ] Fishing system works
- [ ] Leaderboards accurate
- [ ] Performance metrics (queries \u003c 100ms)

### Integration Tests
- [ ] Concurrent users (simulate 50 users fishing)
- [ ] Race condition tests (spam bet buttons)
- [ ] Transaction rollback tests
- [ ] Bot restart preserves state

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data loss during migration | Low | Critical | Multiple backups, test on staging |
| Query breakage | Medium | High | Systematic testing per cog |
| Performance regression | Low | Medium | Benchmark before/after |
| Downtime \u003e 1 hour | Medium | Medium | Practice run on staging |

---

## Success Metrics

- [ ] **Zero data loss**: All row counts match
- [ ] **Performance improvement**: Avg query time \u003c 50ms (down from 100ms)
- [ ] **Code quality**: No more `?` placeholders
- [ ] **Maintainability**: New migrations in \u003c 30 mins

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Prep** | 1 week | Migration framework + conventions |
| **Phase 2: Execute** | 2 weeks | All code migrated, data migrated |
| **Phase 3: Cleanup** | 1 week | SQLite removed, docs updated |
| **TOTAL** | **4 weeks** | Pure Postgres bot |

**Recommended Start Date:** After completing critical bug fixes (Xi Dách, Fishing transaction)

---

**Last Updated:** 2026-01-07  
**Author:** Sisyphus AI  
**Status:** Draft - Awaiting approval
