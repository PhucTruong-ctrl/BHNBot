---
name: postgres-supreme
description: Full-power PostgreSQL usage (Migration from SQLite, JSONB, Optimization)
license: MIT
compatibility: opencode
metadata:
  database: postgresql
  lib: asyncpg
  orm: sqlalchemy
---

## 🐘 PostgreSQL Migration & Optimization Standards

You are migrating from a toy database (SQLite) to a production beast (PostgreSQL). Act like it.

### 1. The Migration Mindset
- **Schema Validation:** Data types in Postgres are strict. `String` != `Text`.
- **Migration Tool:** MANDATORY use of **Alembic** for schema changes. Never run raw `CREATE TABLE` in production code.

### 2. Advanced Features (Use these!)
- **JSONB:** For flexible bot configs or user inventories (like OwO bot items), use `JSONB` columns instead of creating 50 helper tables. Index them with `GIN`.
- **Array Fields:** Use `ARRAY[int]` for simple lists (e.g., role_ids) instead of comma-separated strings.
- **Upsert:** Use `INSERT ... ON CONFLICT DO UPDATE` instead of `Check if exist -> Insert/Update`.

### 3. Performance & Concurrency
- **Connection Pooling:** MANDATORY. Use `asyncpg.create_pool`. Never open a new connection for every command.
- **Transactions:** Wrap money/inventory transfers in `async with connection.transaction():`.
- **Indexes:** Create indexes on columns used in `WHERE` and `JOIN` clauses.

### 4. Migration Plan (SQLite -> Postgres)
1.  **Dump Data:** Export SQLite data to standard CSV/JSON.
2.  **Schema Re-creation:** Define SQLAlchemy models matching the Postgres standards.
3.  **ETL Script:** Write a Python script to load data, sanitize it (fix booleans, datetimes), and bulk insert into Postgres.