# AGENTS.md - BHNBot AI Agent Skills & Protocols

> **Comprehensive guide for AI agents working on BHNBot**
> 
> This document consolidates all skills, instructions, and prompts for the OpenCode AI system.
> Based on research from: Domain-Driven Design, Clean Architecture, Hexagonal Architecture, CQRS, Event Sourcing, and industry best practices.

---

## Table of Contents

### Part I: Project-Specific Skills (Discord Bot)
1. [discord-arch - Scalable 4-Layer Architecture](#1-discord-arch---scalable-4-layer-architecture)
2. [python-godmode - Strict Python Standards](#2-python-godmode---strict-python-standards)
3. [postgres-supreme - PostgreSQL Optimization](#3-postgres-supreme---postgresql-optimization)
4. [algo-god - Performance & Algorithm Protocol](#4-algo-god---performance--algorithm-protocol)
5. [debug-protocol - Systematic Bug Analysis](#5-debug-protocol---systematic-bug-analysis)
6. [qa-engineer - Quality Assurance Protocol](#6-qa-engineer---quality-assurance-protocol)
7. [sec-ops - Security Operations Protocol](#7-sec-ops---security-operations-protocol)
8. [git-commander - Git Workflow Protocol](#8-git-commander---git-workflow-protocol)
9. [devops-master - Deployment Protocol](#9-devops-master---deployment-protocol)
10. [fullstack-bridge - Web & API Integration](#10-fullstack-bridge---web--api-integration)
11. [market-analyst - Competitive Analysis](#11-market-analyst---competitive-analysis)
12. [reverse-engineer - Code Analysis](#12-reverse-engineer---code-analysis)
13. [cog-template - Boilerplate Generator](#13-cog-template---boilerplate-generator)

### Part II: Advanced Architecture Skills (NEW)
14. [ddd-master - Domain-Driven Design Protocol](#14-ddd-master---domain-driven-design-protocol)
15. [hexagonal-arch - Ports & Adapters Architecture](#15-hexagonal-arch---ports--adapters-architecture)
16. [cqrs-architect - Command Query Responsibility Segregation](#16-cqrs-architect---command-query-responsibility-segregation)
17. [event-sourcing - Event-Driven State Management](#17-event-sourcing---event-driven-state-management)
18. [clean-arch - Clean Architecture Protocol](#18-clean-arch---clean-architecture-protocol)

### Part III: Code Quality Skills (NEW)
19. [code-auditor - Systematic Code Review](#19-code-auditor---systematic-code-review)
20. [refactor-master - Safe Refactoring Protocol](#20-refactor-master---safe-refactoring-protocol)
21. [anti-pattern-hunter - Code Smell Detection](#21-anti-pattern-hunter---code-smell-detection)

### Part IV: UI/UX Skills (NEW)
22. [ui-architect - Design System Protocol](#22-ui-architect---design-system-protocol)
23. [accessibility-ops - WCAG Compliance Protocol](#23-accessibility-ops---wcag-compliance-protocol)

### Part V: Agent System Reference
24. [Agent Types & Usage Guidelines](#agent-types-opencode-system)
25. [Quick Reference Tables](#quick-reference-skill-invocation)

---

# Part VI: Appendix - Complete AGENTS.md Template

This AGENTS.md serves as a comprehensive reference combining:
- **Project-specific skills** (Discord Bot, Python, PostgreSQL)
- **Universal architecture patterns** (DDD, Clean Architecture, Hexagonal)
- **OpenCode Agent System** (Sisyphus, Oracle, Librarian, etc.)

For the global/universal version, see `~/.config/opencode/AGENTS.md`

---

# Part I: Project-Specific Skills (Discord Bot)

---

## 1. discord-arch - Scalable 4-Layer Architecture

**Trigger:** `/discord-arch`  
**Role:** Architect  
**Framework:** discord.py

### The 4-Layer Architecture Standard

When designing or refactoring a Discord Bot feature, you MUST strictly separate concerns into these 4 layers. DO NOT mix them.

#### Layer 1: Controller (The Cog)
- **Location:** `cogs/<feature>/cog.py`
- **Responsibility:**
  - Receive Commands/Events from Discord
  - Parse arguments
  - Call **Service Layer**
  - Send responses (using **UI Layer**)
  - **FORBIDDEN:** Direct database access, complex math, heavy logic

#### Layer 2: Service (The Orchestrator)
- **Location:** `cogs/<feature>/services/`
- **Responsibility:**
  - Combine Business Logic (Core) with Data Access
  - Handle Transactions (ACID)
  - Error handling logic
- **Example:** `EconomyService.transfer_money(sender, receiver, amount)`

#### Layer 3: Core (Business Logic)
- **Location:** `cogs/<feature>/core/`
- **Responsibility:**
  - Pure Python logic. NO `discord` imports
  - Unit testable
- **Example:** `calculate_tax(amount)`, `check_level_up(xp)`

#### Layer 4: UI (Presentation)
- **Location:** `cogs/<feature>/ui/`
- **Responsibility:**
  - Format Embeds
  - Define Views (Buttons, Dropdowns)
  - **FORBIDDEN:** Executing logic inside buttons (Buttons must callback to Controller/Service)

### Directory Structure Template
```
cogs/<feature>/
├── __init__.py          # Cog loader
├── cog.py               # Controller - Commands/Events
├── services/
│   ├── __init__.py
│   └── feature_service.py
├── core/
│   ├── __init__.py
│   ├── models.py        # Pydantic/dataclass models
│   ├── logic.py         # Pure business logic
│   └── exceptions.py    # Domain exceptions
├── ui/
│   ├── __init__.py
│   ├── embeds.py        # Embed builders
│   └── views.py         # Buttons, Dropdowns, Modals
└── repositories/
    ├── __init__.py
    └── feature_repo.py  # Database access
```

### Usage Instruction
Before writing code for a new feature, output the file structure based on this architecture.

---

## 2. python-godmode - Strict Python Standards

**Trigger:** `/python-godmode`  
**Level:** Senior  
**Language:** Python

### Python God-Mode Standards

You are a Python Purist. Reject any code that violates these rules.

#### 1. Type Hinting is MANDATORY
- Every function arguments and return types MUST be hinted
- Use `typing.List`, `typing.Dict`, `typing.Optional` or Python 3.10+ syntax (`list[]`, `|`)
- **Good:** `def get_user(user_id: int) -> Optional[User]:`
- **Bad:** `def get_user(user_id):`

```python
# CORRECT
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    balance: float

async def get_users_by_ids(user_ids: List[int]) -> List[User]:
    ...

async def find_user(user_id: int) -> Optional[User]:
    ...

# WRONG - No type hints
def get_users(ids):
    return db.query(ids)
```

#### 2. Asyncio Best Practices
- **NEVER** use blocking calls (e.g., `requests`, `time.sleep`) inside async functions
- Use `aiohttp` for HTTP requests
- Use `asyncio.sleep` for delays
- Use `asyncio.Lock()` when modifying shared state (Global variables, Cache)

```python
# CORRECT
async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# WRONG - Blocking in async context
async def fetch_data(url: str) -> dict:
    return requests.get(url).json()  # BLOCKS THE EVENT LOOP!
```

#### 3. Error Handling
- **FORBIDDEN:** `try: ... except: pass` (Silent fail)
- Always catch specific errors: `except discord.Forbidden:`
- Log the error with full traceback before notifying the user

```python
# CORRECT
import logging
logger = logging.getLogger(__name__)

async def send_dm(user: discord.User, message: str) -> bool:
    try:
        await user.send(message)
        return True
    except discord.Forbidden:
        logger.warning(f"Cannot DM user {user.id} - DMs disabled")
        return False
    except discord.HTTPException as e:
        logger.exception(f"Failed to DM user {user.id}")
        raise

# WRONG - Silent failure
async def send_dm(user, message):
    try:
        await user.send(message)
    except:
        pass  # NEVER DO THIS
```

#### 4. Data Models
- Use `pydantic.BaseModel` or `@dataclass` for data structures
- Do not pass raw Dicts/Tuples around

```python
# CORRECT
from pydantic import BaseModel, Field

class TransferRequest(BaseModel):
    sender_id: int
    receiver_id: int
    amount: float = Field(gt=0, description="Must be positive")
    
# WRONG
def transfer(data: dict):  # What keys? What types?
    sender = data["sender"]
    ...
```

#### 5. SOLID Principles

| Principle | Rule |
|-----------|------|
| **Single Responsibility** | Each class/function does ONE thing |
| **Open/Closed** | Open for extension, closed for modification |
| **Liskov Substitution** | Subtypes must be substitutable |
| **Interface Segregation** | Many specific interfaces > one general |
| **Dependency Inversion** | Depend on abstractions, not concretions |

### Self-Correction
After generating code, ask yourself: "Is this readable? Is this performant? Is this type-safe?"

---

## 3. postgres-supreme - PostgreSQL Optimization

**Trigger:** `/postgres-supreme`  
**Database:** PostgreSQL  
**Libraries:** asyncpg, SQLAlchemy

### PostgreSQL Migration & Optimization Standards

You are migrating from a toy database (SQLite) to a production beast (PostgreSQL). Act like it.

#### 1. The Migration Mindset
- **Schema Validation:** Data types in Postgres are strict. `String` != `Text`
- **Migration Tool:** MANDATORY use of **Alembic** for schema changes. Never run raw `CREATE TABLE` in production code

#### 2. Advanced Features (Use these!)
| Feature | Use Case |
|---------|----------|
| **JSONB** | Flexible bot configs, user inventories. Index with `GIN` |
| **Array Fields** | `ARRAY[int]` for simple lists (role_ids) instead of comma-separated strings |
| **Upsert** | `INSERT ... ON CONFLICT DO UPDATE` instead of check-then-insert |
| **CTEs** | `WITH` clauses for complex queries |
| **Window Functions** | `ROW_NUMBER()`, `RANK()` for leaderboards |

#### 3. Performance & Concurrency
- **Connection Pooling:** MANDATORY. Use `asyncpg.create_pool`. Never open a new connection for every command
- **Transactions:** Wrap money/inventory transfers in `async with connection.transaction():`
- **Indexes:** Create indexes on columns used in `WHERE` and `JOIN` clauses

```python
# CORRECT - Connection Pool
class Database:
    pool: asyncpg.Pool
    
    async def init(self, dsn: str):
        self.pool = await asyncpg.create_pool(dsn, min_size=5, max_size=20)
    
    async def get_user(self, user_id: int) -> Optional[UserRow]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )

# CORRECT - Transaction
async def transfer_money(sender_id: int, receiver_id: int, amount: float):
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET balance = balance - $1 WHERE id = $2",
                amount, sender_id
            )
            await conn.execute(
                "UPDATE users SET balance = balance + $1 WHERE id = $2",
                amount, receiver_id
            )
```

#### 4. Migration Plan (SQLite -> Postgres)
1. **Dump Data:** Export SQLite data to standard CSV/JSON
2. **Schema Re-creation:** Define SQLAlchemy models matching the Postgres standards
3. **ETL Script:** Write a Python script to load data, sanitize it (fix booleans, datetimes), and bulk insert into Postgres

#### 5. Query Optimization Checklist
- [ ] Use `EXPLAIN ANALYZE` on slow queries
- [ ] Add indexes on foreign keys and frequently filtered columns
- [ ] Use `LIMIT` with `OFFSET` for pagination (or better: cursor-based)
- [ ] Avoid `SELECT *` - select only needed columns
- [ ] Use prepared statements (`$1`, `$2`) not f-strings

---

## 4. algo-god - Performance & Algorithm Protocol

**Trigger:** `/algo-god`  
**Level:** Expert

### Performance & Algorithm Protocol

Scale from 10 users to 1,000,000 users.

#### 1. Big O Awareness
| Pattern | Complexity | Action |
|---------|------------|--------|
| Nested Loops | `O(n²)` | Avoid whenever possible |
| List membership (`in list`) | `O(n)` | Use **Sets** instead `O(1)` |
| Dict lookups | `O(1)` | Preferred for key-based access |
| Sorting | `O(n log n)` | Use built-in `sorted()` or `list.sort()` |
| Binary Search | `O(log n)` | Use `bisect` module for sorted data |

```python
# WRONG - O(n) lookup repeated
def find_common(list1, list2):
    return [x for x in list1 if x in list2]  # O(n*m)

# CORRECT - O(n) total
def find_common(list1, list2):
    set2 = set(list2)
    return [x for x in list1 if x in set2]  # O(n+m)
```

#### 2. Caching Strategy (Redis)
- **Read-Heavy Data:** Cache User Profiles/Guild Configs in Redis. Only write to Postgres on change or periodically (Write-Back)
- **TTL (Time To Live):** Don't cache forever. Set expiry

```python
import redis.asyncio as redis

class CachedUserService:
    def __init__(self, redis_client: redis.Redis, db: Database):
        self.redis = redis_client
        self.db = db
        self.TTL = 300  # 5 minutes
    
    async def get_user(self, user_id: int) -> Optional[User]:
        # Try cache first
        cached = await self.redis.get(f"user:{user_id}")
        if cached:
            return User.model_validate_json(cached)
        
        # Cache miss - fetch from DB
        user = await self.db.get_user(user_id)
        if user:
            await self.redis.setex(
                f"user:{user_id}", 
                self.TTL,
                user.model_dump_json()
            )
        return user
```

#### 3. Lazy Loading
- Don't fetch the entire User Inventory on startup. Fetch on demand
- Use Generators (`yield`) for processing large datasets to save RAM

```python
# WRONG - Loads everything into memory
def process_all_users(users: List[User]):
    results = []
    for user in users:
        results.append(expensive_operation(user))
    return results

# CORRECT - Generator, constant memory
def process_all_users(users: Iterable[User]) -> Iterator[Result]:
    for user in users:
        yield expensive_operation(user)
```

#### 4. Profiling
- If the bot is slow, don't guess. Use `cProfile` or `py-spy` to find the bottleneck

```bash
# Profile a script
python -m cProfile -s cumtime bot.py

# Live profiling with py-spy
py-spy top --pid <bot_pid>
```

---

## 5. debug-protocol - Systematic Bug Analysis

**Trigger:** `/debug-protocol`  
**Task:** Debugging

### Deep Debug Protocol

When the user reports an error or provides a traceback, DO NOT guess. Follow this procedure:

#### Step 1: Traceback Autopsy
1. Locate the **Exact File and Line Number** where the error originated
2. Identify the **Exception Type** (e.g., `AttributeError`, `RuntimeError`)
3. Determine if the error is User Logic or Library Constraint (discord.py limitations)

```
# Reading a traceback - bottom is the origin
Traceback (most recent call last):
  File "cogs/economy/cog.py", line 45, in transfer  <- CALLED FROM
    result = await self.service.transfer(...)
  File "cogs/economy/services/economy.py", line 23, in transfer  <- ORIGIN
    raise InsufficientFundsError(sender.balance, amount)
```

#### Step 2: Reverse Engineering
- If code is provided, simulate the execution flow in your "mind"
- Identify **Race Conditions** (Async tasks running out of order)
- Check for **NoneType** propagation (Did a previous function return None?)

```python
# Common NoneType bug
user = await get_user(user_id)  # Returns None if not found
user.balance -= amount  # AttributeError: 'NoneType' has no attribute 'balance'

# Fix: Validate before use
user = await get_user(user_id)
if user is None:
    raise UserNotFoundError(user_id)
```

#### Step 3: Strategic Fix
1. Explain the **Root Cause** to the user clearly
2. Propose a fix that addresses the root cause, not just the symptom
3. Check for side effects (Does this fix break other features?)

### Anti-Patterns to Avoid
- Do not suggest: "Try updating pip" (unless version is clearly wrong)
- Do not suggest: wrapping everything in `try/except` to hide the error

### Debug Decision Tree
```
Error Received
    │
    ├── Is it a TypeError/AttributeError?
    │   └── Check: Is something returning None unexpectedly?
    │
    ├── Is it a discord.Forbidden/HTTPException?
    │   └── Check: Does bot have required permissions?
    │
    ├── Is it intermittent (sometimes works)?
    │   └── Check: Race condition or external service timeout?
    │
    └── Is it on startup only?
        └── Check: Missing environment variable or config?
```

---

## 6. qa-engineer - Quality Assurance Protocol

**Trigger:** `/qa-engineer`  
**Framework:** pytest

### Quality Assurance Protocol

"It works" is not enough. Prove it with tests.

#### 1. Testing Framework: Pytest
- Use `pytest` for all test suites
- Use `conftest.py` for shared fixtures (e.g., spinning up a temporary event loop)

```python
# conftest.py
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_database():
    """Provides a test database connection."""
    db = await create_test_database()
    yield db
    await db.cleanup()
```

#### 2. Mocking & Dependency Injection
- **Problem:** You cannot connect to real Discord API or real Bank API during tests
- **Solution:** Use `unittest.mock` or `pytest-mock` to fake external calls
- **Rule:** If a function makes a network call, it MUST be mocked in unit tests

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_transfer_success(mock_database):
    # Arrange
    service = EconomyService(db=mock_database)
    sender = User(id=1, balance=100)
    receiver = User(id=2, balance=50)
    
    mock_database.get_user = AsyncMock(side_effect=[sender, receiver])
    mock_database.update_user = AsyncMock()
    
    # Act
    result = await service.transfer(sender.id, receiver.id, 30)
    
    # Assert
    assert result.success is True
    assert mock_database.update_user.call_count == 2
```

#### 3. Test Organization
```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Pure logic tests (no I/O)
│   └── test_economy_core.py
├── integration/             # Tests with database/external services
│   └── test_economy_service.py
└── e2e/                     # Full flow tests
    └── test_commands.py
```

#### 4. Coverage Standards
- Aim for high coverage on **Core Logic** (Economy calculations, RNG logic)
- UI/View code is harder to test, but Logic layers must be bulletproof
- Target: **80%+ coverage on core/, 60%+ overall**

#### 5. Test Driven Development (TDD) Mindset
When fixing a bug:
1. Write a test that reproduces the bug (Fail)
2. Fix the code
3. Run the test (Pass)
4. Commit both

---

## 7. sec-ops - Security Operations Protocol

**Trigger:** `/sec-ops`  
**Standard:** OWASP

### Security Operations Protocol

Paranoia is a virtue. Assume every user input is malicious.

#### 1. Input Sanitization
| Threat | Prevention |
|--------|------------|
| SQL Injection | NEVER use f-string in SQL. Always use parameterized queries (`$1`, `$2` in asyncpg) |
| Command Injection | Be careful with `subprocess` or `eval()`. AVOID `eval()` at all costs |
| Discord Markdown | Sanitize user input before echoing to prevent mass-pings (`@everyone`) |
| Path Traversal | Never use user input directly in file paths |

```python
# WRONG - SQL Injection vulnerability
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# CORRECT - Parameterized query
query = "SELECT * FROM users WHERE name = $1"
result = await conn.fetch(query, user_input)

# WRONG - Mass ping vulnerability
await ctx.send(f"User said: {user_input}")

# CORRECT - Escape mentions
import discord
await ctx.send(f"User said: {discord.utils.escape_mentions(user_input)}")
```

#### 2. Rate Limiting (Anti-Spam)
- Use `commands.Cooldown` mapping to `BucketType.user`
- For heavy commands (Image generation), implement a custom Redis-based lock/cooldown

```python
from discord.ext import commands

class Economy(commands.Cog):
    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)  # 1 use per 60 seconds per user
    async def daily(self, ctx):
        ...
```

#### 3. Secret Management
- **Scan:** Ensure no API Keys/Tokens are ever committed to Git
- **Rotation:** Design the system so tokens can be rotated without code changes
- **Storage:** Use environment variables or secret managers (never hardcode)

```python
# WRONG
TOKEN = "NzM0..."  # NEVER commit tokens

# CORRECT
import os
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable not set")
```

#### 4. Privilege Principle
- Bot should request minimal Discord Intents
- Database user should not be `postgres` (root). Create a specific user for the bot
- File permissions: Logs should not be world-readable

#### 5. Security Checklist
- [ ] All SQL uses parameterized queries
- [ ] No `eval()` or `exec()` in codebase
- [ ] User input is escaped before display
- [ ] Secrets are in environment variables
- [ ] Bot uses minimal required intents
- [ ] Error messages don't leak internal details

---

## 8. git-commander - Git Workflow Protocol

**Trigger:** `/git-commander`  
**Role:** DevOps  
**Tool:** Git

### Git Workflow Protocol

You are the Release Manager. Do not let the user break the repository.

#### 1. Branching Strategy (Gitflow Lite)
| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code ONLY. Protected |
| `develop` | Integration branch |
| `feat/<name>` | New features (e.g., `feat/economy-system`) |
| `fix/<name>` | Bug fixes |
| `chore/<name>` | Maintenance (deps update, migration) |
| `hotfix/<name>` | Emergency production fixes |

#### 2. Commit Standards (Conventional Commits)
Refuse to generate commit messages that don't follow this format:
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change without feature/fix |
| `docs` | Documentation only |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |
| `perf` | Performance improvement |
| `ci` | CI/CD changes |

Examples:
```
feat(economy): add postgres connection pool
fix(music): resolve race condition in queue
refactor(core): move ui logic to view layer
chore(deps): update requirements.txt
```

#### 3. Intelligent Conflict Resolution
When handling conflicts (merge/rebase):
1. **Analyze Context:** Don't just choose "Incoming" or "Current". Read the logic
2. **Hybrid Approach:** If both changes are valid, combine them manually
3. **Safety Check:** After resolving, verify that imports and variable names are consistent

#### 4. Commands Capability
- **Rebase:** Use `git rebase -i` to squash messy commits before merging
- **Stash:** Use `git stash` when context switching
- **Blame:** Use `git blame` to identify who introduced specific logic (for context, not shaming)
- **Bisect:** Use `git bisect` to find the commit that introduced a bug

### Migration & Safety
- **NEVER** force push (`-f`) to shared branches (`main`, `develop`) unless explicitly authorized
- Always run `pre-commit` checks (if available) before committing

---

## 9. devops-master - Deployment Protocol

**Trigger:** `/devops-master`  
**Stack:** Docker, GitHub Actions

### DevOps & Deployment Protocol

You are responsible for the infrastructure. Code that cannot be deployed is useless code.

#### 1. Dockerization Standard
- **Multi-Stage Builds:** Always use multi-stage builds to keep image size small

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app
RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt -o requirements.txt

# Stage 2: Runner
FROM python:3.11-slim as runner

# Create non-root user
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser
CMD ["python", "main.py"]
```

#### 2. Docker Compose Strategy
```yaml
version: '3.8'

services:
  bot:
    build: .
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### 3. CI/CD (GitHub Actions)
| Stage | Requirement |
|-------|-------------|
| Linting | Pipeline must fail if `ruff` or `black` finds errors |
| Type Check | Pipeline must run `mypy` |
| Testing | Pipeline must run `pytest` |
| Build | Docker build must succeed |
| Deployment | If `main` branch is pushed, trigger Docker build and deploy |

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      
      - name: Lint
        run: ruff check .
      
      - name: Type Check
        run: mypy .
      
      - name: Test
        run: pytest --cov=. --cov-report=xml
```

#### 4. Environment Management
- NEVER hardcode secrets. Use `.env` file and `os.getenv`
- In Docker, map env-file: `env_file: .env`
- Use separate `.env.example` with dummy values for documentation

---

## 10. fullstack-bridge - Web & API Integration

**Trigger:** `/fullstack-bridge`  
**Framework:** FastAPI, React

### Web & API Integration Protocol

The Bot is not an island. It connects to the Web Dashboard.

#### 1. API Framework: FastAPI
- Don't build a web server inside `discord.py`. Run `FastAPI` as a separate service or separate thread/loop (advanced)
- Expose endpoints like `/api/user/{id}/inventory`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="BHNBot API")

class UserResponse(BaseModel):
    id: int
    name: str
    balance: float
    level: int

@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

#### 2. IPC (Inter-Process Communication)
How does the Dashboard tell the Bot to kick a user?

| Option | Description | Use Case |
|--------|-------------|----------|
| **Shared Database** | Dashboard writes to DB, Bot polls DB | Simple, eventual consistency |
| **Redis Pub/Sub** | Dashboard publishes event, Bot subscribes | Real-time actions |
| **Message Queue** | RabbitMQ, Redis Streams | Guaranteed delivery |
| **gRPC** | Direct RPC calls | High performance |

```python
# Redis Pub/Sub Example
import redis.asyncio as redis

# Publisher (Dashboard/API)
async def request_user_kick(guild_id: int, user_id: int):
    await redis_client.publish(
        "bot:actions",
        json.dumps({"action": "kick", "guild_id": guild_id, "user_id": user_id})
    )

# Subscriber (Bot)
async def listen_for_actions():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("bot:actions")
    async for message in pubsub.listen():
        if message["type"] == "message":
            action = json.loads(message["data"])
            await handle_action(action)
```

#### 3. JSON Standards
- API responses must be consistent JSON
- Use `pydantic` models to share schemas between Bot and Web
- Always include error details in a standard format

```python
class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc),
            code=f"ERR_{exc.status_code}"
        ).model_dump()
    )
```

#### 4. OAuth2 Flow
- Understand the Discord OAuth2 flow for the Dashboard login
- Bot validates: Is this user actually an Admin in that server?

---

## 11. market-analyst - Competitive Analysis

**Trigger:** `/market-analyst`  
**Knowledge Base:** GitHub Top Bots

### Competitive Analysis Protocol

You have access to the "Hall of Fame" bot knowledge base (YAGPDB, Red, OwO, Poketwo, etc.).
When the user asks for a feature, **DO NOT invent it from scratch**. Analyze how the giants did it.

#### 1. Category Mapping
Identify which "Giant" to study based on user request:

| Category | Reference Bots | Focus Areas |
|----------|---------------|-------------|
| RPG/Gacha/Economy | OwO Bot, Poketwo, Gelbpunkt/IdleRPG | RNG balance, grinding loops, trade safety |
| Music | Green-bot, Lavalink/Rainlink bots (Lunox) | Audio quality, queue management, DJ roles |
| Moderation/Logs | YAGPDB, DraconianBot, Cronus | Automod regex, raid protection (CAPTCHA) |
| Dashboard/Web | Cially, Fluxpoint, Discord-BOT-Dashboard-V2 | OAuth2, IPC (Inter-Process Communication) |
| Leveling | MEE6, Tatsu, AmariBot | XP formulas, role rewards, leaderboards |
| Utility | Carl-bot, Dyno | Reaction roles, embeds, reminders |

#### 2. Feature Extraction Workflow
1. **Concept:** What is the user trying to build?
2. **Reference Check:** "How does [Reference Bot] handle this?" (e.g., How does OwO handle inventory spam?)
3. **Gap Analysis:** What is missing in the open-source version that we can improve?
4. **Implementation Plan:** Adapt the logic to our **Python/Postgres** stack

#### 3. Innovation Trigger
- Look at *RedCokeDevelopment/Teapot.py* for miscellaneous utility ideas
- Look at *interactions-py* for latest Discord UI features (Modals, Context Menus)
- Look at *Switchblade* for modular architecture references

### Strategic Advice
- If the user wants a "Ticket System", reference *Sayrix/Ticket-Bot* but suggest storing transcripts in Postgres JSONB
- If the user wants "Stable Diffusion", reference *SpenserCai/sd-webui-discord* for queue handling

---

## 12. reverse-engineer - Code Analysis

**Trigger:** `/reverse-engineer`  
**Mode:** Deep Dive

### Reverse Engineering Protocol

When handed a piece of code, a link, or a vague logic description:

#### Phase 1: Static Analysis (The Read)
- **Identify Patterns:** Is this a State Machine? An Event Bus? A Factory pattern?
- **Dependency Graph:** What does this code import? (e.g., If it imports `numpy`, it's doing heavy math)
- **Code Smell:** Detect obfuscated logic or weird variable names (`var a`, `func x`). Rename them mentally to semantic names

#### Phase 2: Logic Reconstruction
- **Flowcharting:** Describe the data flow: `Input -> Parser -> Validator -> Processor -> Database`
- **Black Box Testing:** If we can't see the code (closed source bot), create a hypothesis: "If I send X, and it returns Y, then it must be doing Z"

#### Phase 3: Replication (The "Better" Version)
- Don't just copy. **Improve.**
- If the original code uses a global variable (Bad), refactor it to a Class Attribute (Good)
- If the original code uses blocking IO, rewrite it to Async IO

### Specific Target: OwO/Poketwo Logic
- **Economy:** Analyze how they prevent inflation (Tax, Cooldowns)
- **RNG:** Analyze their drop rates (Weighted Random). *Replicate this using Python `random.choices` with weights*

---

## 13. cog-template - Boilerplate Generator

**Trigger:** `/cog-template`  
**Type:** Generator

### New Cog Boilerplate

When asked to create a new feature (e.g., "Make a music bot"), generate this structure immediately.

#### Directory Structure: `cogs/<name>/`

**`__init__.py`**
```python
from discord.ext import commands
from .cog import MyCog

async def setup(bot: commands.Bot):
    await bot.add_cog(MyCog(bot))
```

**`cog.py`** - Controller layer (see discord-arch)
```python
from discord.ext import commands
from discord import app_commands
import discord

from .services import MyService
from .ui import MyEmbed, MyView

class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = MyService(bot.db)
    
    @app_commands.command(name="example", description="Example command")
    async def example_command(self, interaction: discord.Interaction):
        result = await self.service.do_something(interaction.user.id)
        embed = MyEmbed.success(result)
        await interaction.response.send_message(embed=embed)
```

**`services/`** - Business logic orchestration

**`core/`** - Pure Python logic (no discord imports)

**`ui/`** - Embeds, Views, Buttons

---

# Part II: Advanced Architecture Skills (NEW)

---

## 14. ddd-master - Domain-Driven Design Protocol

**Trigger:** `/ddd-master`  
**Level:** Architect  
**Reference:** Eric Evans, Vaughn Vernon

### Domain-Driven Design Protocol

DDD is not about technology. It's about understanding the business domain deeply.

#### Strategic DDD Patterns

##### 1. Bounded Contexts
- A **Bounded Context** is a boundary within which a particular model is defined and applicable
- Different contexts can have different models for the same concept (e.g., "User" in Auth vs "User" in Billing)

```
┌─────────────────────────────────────────────────────────────┐
│                      Discord Bot System                       │
├──────────────────┬──────────────────┬──────────────────────┤
│   Auth Context   │  Economy Context  │   Music Context      │
├──────────────────┼──────────────────┼──────────────────────┤
│ User             │ User (Wallet)     │ User (Queue)         │
│ - discord_id     │ - balance         │ - current_track      │
│ - permissions    │ - inventory       │ - queue_position     │
│ - session        │ - transactions    │ - preferences        │
└──────────────────┴──────────────────┴──────────────────────┘
```

##### 2. Ubiquitous Language
- Use the SAME terminology everywhere: code, docs, conversations
- If domain experts say "Transfer", code should say `transfer()` not `move_money()`

##### 3. Context Mapping Patterns

| Pattern | Description | Use When |
|---------|-------------|----------|
| **Shared Kernel** | Two contexts share a subset of the model | Tightly coupled teams |
| **Customer-Supplier** | Upstream context supplies data to downstream | Clear dependency direction |
| **Anti-Corruption Layer** | Translate between contexts | Integrating with legacy/external systems |
| **Published Language** | Shared language for integration (API contracts) | Public APIs |
| **Conformist** | Downstream conforms to upstream's model | No control over upstream |

#### Tactical DDD Patterns

##### 1. Entities
- Have identity that persists across state changes
- Mutable (within aggregate boundaries)

```python
from dataclasses import dataclass, field
from uuid import UUID, uuid4

@dataclass
class User:
    id: UUID = field(default_factory=uuid4)
    discord_id: int
    balance: float = 0.0
    
    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount
    
    def withdraw(self, amount: float) -> None:
        if amount > self.balance:
            raise InsufficientFundsError(self.balance, amount)
        self.balance -= amount
```

##### 2. Value Objects
- Defined by their attributes, not identity
- IMMUTABLE - always create new instances

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # Immutable
class Money:
    amount: float
    currency: str = "USD"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
    
    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchError()
        return Money(self.amount + other.amount, self.currency)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency
```

##### 3. Aggregates
- Cluster of entities and value objects with a root entity
- External references only through the root
- Transactional consistency boundary

```python
@dataclass
class Order:  # Aggregate Root
    id: UUID
    user_id: UUID
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    
    def add_item(self, item: OrderItem) -> None:
        if self.status != OrderStatus.PENDING:
            raise InvalidOperationError("Cannot modify confirmed order")
        self.items.append(item)
    
    def confirm(self) -> None:
        if not self.items:
            raise InvalidOperationError("Cannot confirm empty order")
        self.status = OrderStatus.CONFIRMED
```

##### 4. Domain Events
- Represent something that happened in the domain
- Immutable facts
- Named in past tense

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class UserCreatedEvent:
    user_id: UUID
    discord_id: int
    occurred_at: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class MoneyTransferredEvent:
    from_user_id: UUID
    to_user_id: UUID
    amount: float
    occurred_at: datetime = field(default_factory=datetime.utcnow)
```

##### 5. Repositories
- Abstract persistence
- Interface in domain, implementation in infrastructure

```python
from abc import ABC, abstractmethod
from typing import Optional

# Domain layer - interface
class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        ...
    
    @abstractmethod
    async def find_by_discord_id(self, discord_id: int) -> Optional[User]:
        ...
    
    @abstractmethod
    async def save(self, user: User) -> None:
        ...

# Infrastructure layer - implementation
class PostgresUserRepository(UserRepository):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )
            return User(**row) if row else None
```

##### 6. Domain Services
- Logic that doesn't belong to a single entity
- Stateless operations

```python
class TransferService:
    """Handles money transfers between users."""
    
    async def transfer(
        self,
        from_user: User,
        to_user: User,
        amount: float
    ) -> TransferResult:
        from_user.withdraw(amount)
        to_user.deposit(amount)
        
        return TransferResult(
            from_user_id=from_user.id,
            to_user_id=to_user.id,
            amount=amount,
            success=True
        )
```

### DDD Anti-Patterns to AVOID

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| **Anemic Domain Model** | Entities are just data bags, logic is in services | Put behavior in entities |
| **God Aggregate** | One massive aggregate with everything | Split into smaller aggregates |
| **Repository per Table** | One-to-one mapping | Repository per aggregate root |
| **Leaking Domain Logic** | Business rules in controllers/UI | Keep logic in domain layer |

---

## 15. hexagonal-arch - Ports & Adapters Architecture

**Trigger:** `/hexagonal-arch`  
**Alias:** Ports and Adapters, Clean Architecture  
**Level:** Architect

### Hexagonal Architecture Protocol

The core idea: **The domain is at the center, everything else is an adapter.**

#### Core Concept
```
                    ┌─────────────────────────────────┐
                    │         PRIMARY ADAPTERS         │
                    │   (Drive the application)        │
                    │  Discord Commands, REST API      │
                    └─────────────┬───────────────────┘
                                  │ calls
                    ┌─────────────▼───────────────────┐
                    │           PORTS (In)             │
                    │    Use Case Interfaces           │
                    └─────────────┬───────────────────┘
                                  │
        ┌─────────────────────────▼─────────────────────────┐
        │                   DOMAIN CORE                      │
        │   Entities, Value Objects, Domain Services         │
        │            (NO FRAMEWORK IMPORTS!)                 │
        └─────────────────────────┬─────────────────────────┘
                                  │
                    ┌─────────────▼───────────────────┐
                    │          PORTS (Out)             │
                    │   Repository Interfaces          │
                    └─────────────┬───────────────────┘
                                  │ implemented by
                    ┌─────────────▼───────────────────┐
                    │       SECONDARY ADAPTERS         │
                    │   (Driven by the application)    │
                    │  PostgreSQL, Redis, Discord API  │
                    └─────────────────────────────────┘
```

#### The Golden Rule
**Dependency points INWARD.** Domain knows nothing about infrastructure.

```python
# WRONG - Domain depends on infrastructure
from asyncpg import Pool  # Infrastructure import in domain!

class UserService:
    def __init__(self, pool: Pool):  # Domain knows about Postgres
        self.pool = pool

# CORRECT - Domain depends on abstraction
from abc import ABC, abstractmethod

class UserRepository(ABC):  # Port (interface)
    @abstractmethod
    async def find(self, user_id: int) -> Optional[User]: ...

class UserService:
    def __init__(self, repo: UserRepository):  # Depends on abstraction
        self.repo = repo
```

#### Directory Structure
```
src/
├── domain/                    # Pure business logic
│   ├── models/
│   │   ├── user.py           # Entities
│   │   └── money.py          # Value Objects
│   ├── services/
│   │   └── transfer.py       # Domain Services
│   ├── events/
│   │   └── user_events.py    # Domain Events
│   └── ports/
│       ├── repositories.py   # Output Ports (interfaces)
│       └── services.py       # Input Ports (use case interfaces)
│
├── application/               # Use Cases / Application Services
│   ├── commands/
│   │   └── transfer_money.py
│   └── queries/
│       └── get_user_balance.py
│
├── infrastructure/            # Technical implementations
│   ├── persistence/
│   │   ├── postgres/
│   │   │   └── user_repo.py  # Adapter implementing UserRepository
│   │   └── redis/
│   │       └── cache.py
│   └── messaging/
│       └── event_bus.py
│
└── presentation/              # Entry points
    ├── discord/
    │   └── cogs/
    │       └── economy.py    # Primary Adapter
    └── api/
        └── routes/
            └── users.py      # Primary Adapter
```

#### Adapters

##### Primary Adapters (Driving)
These CALL into the application:
- Discord Cog commands
- REST API endpoints
- CLI commands
- Message queue consumers

```python
# Primary Adapter: Discord Cog
class EconomyCog(commands.Cog):
    def __init__(self, transfer_use_case: TransferMoneyUseCase):
        self.transfer = transfer_use_case
    
    @app_commands.command()
    async def pay(self, interaction, user: discord.User, amount: float):
        result = await self.transfer.execute(
            from_id=interaction.user.id,
            to_id=user.id,
            amount=amount
        )
        await interaction.response.send_message(f"Transferred ${amount}")
```

##### Secondary Adapters (Driven)
These are CALLED BY the application:
- Database repositories
- External API clients
- Message publishers
- File storage

```python
# Secondary Adapter: PostgreSQL Repository
class PostgresUserRepository(UserRepository):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def find(self, user_id: int) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE discord_id = $1", user_id
            )
            return self._to_entity(row) if row else None
    
    def _to_entity(self, row: asyncpg.Record) -> User:
        return User(
            id=row["id"],
            discord_id=row["discord_id"],
            balance=row["balance"]
        )
```

#### Dependency Injection
Use a DI container to wire adapters to ports:

```python
# composition_root.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # Infrastructure
    db_pool = providers.Resource(create_db_pool, config.database_url)
    redis = providers.Resource(create_redis, config.redis_url)
    
    # Repositories (Secondary Adapters)
    user_repo = providers.Factory(
        PostgresUserRepository,
        pool=db_pool
    )
    
    # Use Cases
    transfer_use_case = providers.Factory(
        TransferMoneyUseCase,
        user_repo=user_repo
    )
```

---

## 16. cqrs-architect - Command Query Responsibility Segregation

**Trigger:** `/cqrs-architect`  
**Level:** Advanced  
**Pattern:** CQRS

### CQRS Protocol

**Commands change state. Queries read state. NEVER mix them.**

#### Core Principle
```
┌──────────────────────────────────────────────────────────────┐
│                         USER REQUEST                          │
└──────────────────┬────────────────────────────┬──────────────┘
                   │                            │
          ┌────────▼────────┐          ┌────────▼────────┐
          │    COMMAND      │          │     QUERY       │
          │  (Write Model)  │          │  (Read Model)   │
          └────────┬────────┘          └────────┬────────┘
                   │                            │
          ┌────────▼────────┐          ┌────────▼────────┐
          │   Write Store   │  ──sync→ │   Read Store    │
          │   (PostgreSQL)  │          │   (Redis/ES)    │
          └─────────────────┘          └─────────────────┘
```

#### Commands (Write Operations)

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Command definition
@dataclass(frozen=True)
class TransferMoneyCommand:
    from_user_id: int
    to_user_id: int
    amount: float
    idempotency_key: str  # For duplicate detection

# Command Handler
class TransferMoneyHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        event_bus: EventBus
    ):
        self.user_repo = user_repo
        self.event_bus = event_bus
    
    async def handle(self, command: TransferMoneyCommand) -> TransferResult:
        # 1. Load aggregates
        from_user = await self.user_repo.find(command.from_user_id)
        to_user = await self.user_repo.find(command.to_user_id)
        
        # 2. Execute domain logic
        from_user.withdraw(command.amount)
        to_user.deposit(command.amount)
        
        # 3. Persist changes
        await self.user_repo.save(from_user)
        await self.user_repo.save(to_user)
        
        # 4. Publish domain events
        await self.event_bus.publish(MoneyTransferredEvent(
            from_user_id=from_user.id,
            to_user_id=to_user.id,
            amount=command.amount
        ))
        
        return TransferResult(success=True)
```

#### Queries (Read Operations)

```python
# Query definition
@dataclass(frozen=True)
class GetUserBalanceQuery:
    user_id: int

# Query Handler - optimized for reading
class GetUserBalanceHandler:
    def __init__(self, read_db: ReadDatabase):
        self.read_db = read_db
    
    async def handle(self, query: GetUserBalanceQuery) -> BalanceDTO:
        # Direct optimized read - no domain objects needed
        row = await self.read_db.fetchrow(
            "SELECT balance, currency FROM user_balances WHERE user_id = $1",
            query.user_id
        )
        return BalanceDTO(
            user_id=query.user_id,
            balance=row["balance"],
            currency=row["currency"]
        )
```

#### Command Bus & Query Bus

```python
from typing import TypeVar, Generic, Type

TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")

class CommandBus:
    def __init__(self):
        self._handlers: dict[Type, Any] = {}
    
    def register(self, command_type: Type[TCommand], handler: Any):
        self._handlers[command_type] = handler
    
    async def dispatch(self, command: TCommand) -> TResult:
        handler = self._handlers.get(type(command))
        if not handler:
            raise HandlerNotFoundError(type(command))
        return await handler.handle(command)

# Usage
command_bus = CommandBus()
command_bus.register(TransferMoneyCommand, TransferMoneyHandler(repo, bus))

# Dispatch
result = await command_bus.dispatch(TransferMoneyCommand(
    from_user_id=123,
    to_user_id=456,
    amount=100.0,
    idempotency_key="tx-abc123"
))
```

#### When to Use CQRS

| Use CQRS | Don't Use CQRS |
|----------|----------------|
| Complex read patterns differ from write patterns | Simple CRUD operations |
| High read:write ratio | Similar read/write patterns |
| Need to scale reads independently | Small application |
| Multiple read models (different views) | Single consistent view |

---

## 17. event-sourcing - Event-Driven State Management

**Trigger:** `/event-sourcing`  
**Level:** Advanced  
**Pattern:** ES

### Event Sourcing Protocol

**Don't store state. Store events. Replay to reconstruct state.**

#### Core Concept
```
Traditional:  [Current State] ← UPDATE ← [New State]
                    ↓
              We only know NOW

Event Sourced:  [Event1] → [Event2] → [Event3] → ... → [EventN]
                    ↓
              We know EVERYTHING that happened
```

#### Event Store

```python
@dataclass(frozen=True)
class StoredEvent:
    event_id: UUID
    aggregate_id: UUID
    aggregate_type: str
    event_type: str
    event_data: dict
    version: int
    timestamp: datetime

class EventStore:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def append(
        self,
        aggregate_id: UUID,
        events: list[DomainEvent],
        expected_version: int
    ) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Optimistic concurrency check
                current_version = await self._get_version(conn, aggregate_id)
                if current_version != expected_version:
                    raise ConcurrencyError(
                        f"Expected version {expected_version}, got {current_version}"
                    )
                
                # Append events
                for i, event in enumerate(events):
                    await conn.execute("""
                        INSERT INTO events 
                        (event_id, aggregate_id, aggregate_type, event_type, 
                         event_data, version, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        uuid4(),
                        aggregate_id,
                        event.aggregate_type,
                        type(event).__name__,
                        json.dumps(event.to_dict()),
                        expected_version + i + 1,
                        datetime.utcnow()
                    )
    
    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int = 0
    ) -> list[StoredEvent]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM events 
                WHERE aggregate_id = $1 AND version > $2
                ORDER BY version
            """, aggregate_id, from_version)
            return [StoredEvent(**row) for row in rows]
```

#### Event-Sourced Aggregate

```python
class EventSourcedAggregate(ABC):
    def __init__(self):
        self._uncommitted_events: list[DomainEvent] = []
        self._version = 0
    
    @abstractmethod
    def apply(self, event: DomainEvent) -> None:
        """Apply event to update state."""
        ...
    
    def _raise_event(self, event: DomainEvent) -> None:
        self._uncommitted_events.append(event)
        self.apply(event)
    
    def load_from_history(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.apply(event)
            self._version += 1
    
    def get_uncommitted_events(self) -> list[DomainEvent]:
        return self._uncommitted_events.copy()
    
    def clear_uncommitted_events(self) -> None:
        self._uncommitted_events.clear()

class User(EventSourcedAggregate):
    def __init__(self):
        super().__init__()
        self.id: Optional[UUID] = None
        self.discord_id: Optional[int] = None
        self.balance: float = 0.0
    
    @classmethod
    def create(cls, discord_id: int) -> "User":
        user = cls()
        user._raise_event(UserCreatedEvent(
            user_id=uuid4(),
            discord_id=discord_id
        ))
        return user
    
    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self._raise_event(MoneyDepositedEvent(
            user_id=self.id,
            amount=amount
        ))
    
    def apply(self, event: DomainEvent) -> None:
        match event:
            case UserCreatedEvent():
                self.id = event.user_id
                self.discord_id = event.discord_id
            case MoneyDepositedEvent():
                self.balance += event.amount
            case MoneyWithdrawnEvent():
                self.balance -= event.amount
```

#### Projections (Read Models)

```python
class UserBalanceProjection:
    """Maintains a read-optimized view of user balances."""
    
    def __init__(self, read_db: Database):
        self.read_db = read_db
    
    async def handle(self, event: DomainEvent) -> None:
        match event:
            case UserCreatedEvent():
                await self.read_db.execute("""
                    INSERT INTO user_balances (user_id, balance)
                    VALUES ($1, 0)
                """, event.user_id)
            
            case MoneyDepositedEvent():
                await self.read_db.execute("""
                    UPDATE user_balances 
                    SET balance = balance + $1 
                    WHERE user_id = $2
                """, event.amount, event.user_id)
```

#### When to Use Event Sourcing

| Use ES | Don't Use ES |
|--------|--------------|
| Need complete audit trail | Simple CRUD with no history needs |
| Complex domain with many state transitions | Static data |
| Need to rebuild state at any point in time | Real-time state is sufficient |
| Regulatory requirements for history | Team unfamiliar with pattern |

---

## 18. clean-arch - Clean Architecture Protocol

**Trigger:** `/clean-arch`  
**Level:** Architect  
**Reference:** Robert C. Martin (Uncle Bob)

### Clean Architecture Protocol

**The Dependency Rule: Source code dependencies must point only inward.**

#### The Layers
```
┌─────────────────────────────────────────────────────────────┐
│                    FRAMEWORKS & DRIVERS                      │
│              (Discord.py, FastAPI, PostgreSQL)              │
├─────────────────────────────────────────────────────────────┤
│                   INTERFACE ADAPTERS                         │
│           (Controllers, Presenters, Gateways)               │
├─────────────────────────────────────────────────────────────┤
│                   APPLICATION LAYER                          │
│                    (Use Cases)                              │
├─────────────────────────────────────────────────────────────┤
│                    DOMAIN LAYER                             │
│           (Entities, Value Objects, Domain Services)        │
└─────────────────────────────────────────────────────────────┘
              ↑ Dependencies point INWARD only ↑
```

#### Layer Responsibilities

| Layer | Contains | Knows About |
|-------|----------|-------------|
| **Domain** | Entities, Value Objects, Domain Services, Domain Events | Nothing external |
| **Application** | Use Cases, DTOs, Ports (interfaces) | Domain only |
| **Interface Adapters** | Controllers, Presenters, Repository Impls | Application, Domain |
| **Frameworks** | Discord.py, FastAPI, asyncpg | Everything |

#### Project Structure
```
src/
├── domain/
│   ├── entities/
│   │   └── user.py
│   ├── value_objects/
│   │   └── money.py
│   ├── services/
│   │   └── transfer_service.py
│   └── events/
│       └── user_events.py
│
├── application/
│   ├── use_cases/
│   │   ├── transfer_money.py
│   │   └── get_user_balance.py
│   ├── ports/
│   │   ├── input/
│   │   │   └── transfer_money_port.py
│   │   └── output/
│   │       └── user_repository_port.py
│   └── dto/
│       └── transfer_result.py
│
├── adapters/
│   ├── inbound/
│   │   ├── discord/
│   │   │   └── economy_cog.py
│   │   └── api/
│   │       └── user_routes.py
│   └── outbound/
│       ├── persistence/
│       │   └── postgres_user_repo.py
│       └── messaging/
│           └── redis_event_publisher.py
│
└── main.py  # Composition root
```

#### Use Case Structure

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Input Port (interface)
class TransferMoneyInputPort(ABC):
    @abstractmethod
    async def execute(self, request: TransferRequest) -> TransferResponse:
        ...

# Request DTO
@dataclass(frozen=True)
class TransferRequest:
    from_user_id: int
    to_user_id: int
    amount: float

# Response DTO
@dataclass(frozen=True)
class TransferResponse:
    success: bool
    message: str
    new_balance: Optional[float] = None

# Use Case Implementation
class TransferMoneyUseCase(TransferMoneyInputPort):
    def __init__(
        self,
        user_repo: UserRepositoryPort,
        event_publisher: EventPublisherPort
    ):
        self.user_repo = user_repo
        self.event_publisher = event_publisher
    
    async def execute(self, request: TransferRequest) -> TransferResponse:
        # 1. Load entities
        from_user = await self.user_repo.find_by_id(request.from_user_id)
        to_user = await self.user_repo.find_by_id(request.to_user_id)
        
        if not from_user or not to_user:
            return TransferResponse(success=False, message="User not found")
        
        # 2. Execute domain logic
        try:
            from_user.withdraw(request.amount)
            to_user.deposit(request.amount)
        except InsufficientFundsError:
            return TransferResponse(success=False, message="Insufficient funds")
        
        # 3. Persist
        await self.user_repo.save(from_user)
        await self.user_repo.save(to_user)
        
        # 4. Publish events
        await self.event_publisher.publish(MoneyTransferredEvent(...))
        
        return TransferResponse(
            success=True,
            message="Transfer complete",
            new_balance=from_user.balance
        )
```

#### Key Rules

1. **Domain has NO framework imports**
   ```python
   # domain/entities/user.py
   # NO: import discord
   # NO: import asyncpg
   # YES: Only standard library and domain types
   ```

2. **Use Cases define the API**
   - Use Cases are the application's entry points
   - They orchestrate domain objects
   - They don't contain business rules (those are in domain)

3. **Dependency Injection for flexibility**
   - All dependencies passed through constructor
   - Enables testing with mocks
   - Enables swapping implementations

---

# Part III: Code Quality Skills (NEW)

---

## 19. code-auditor - Systematic Code Review

**Trigger:** `/code-auditor`  
**Level:** Senior  
**Reference:** Claude-Code-Auditor patterns

### Code Audit Protocol

When reviewing code, follow this systematic approach.

#### 1. Risk Classification

| Level | Impact | Examples |
|-------|--------|----------|
| **CRITICAL** | Data loss, security breach | SQL injection, exposed secrets |
| **HIGH** | Feature broken, performance issue | Unhandled exceptions, N+1 queries |
| **MEDIUM** | Code smell, maintainability | Missing types, unclear naming |
| **LOW** | Style, minor improvements | Formatting, documentation gaps |

#### 2. Audit Checklist

##### Security
- [ ] No hardcoded secrets (API keys, tokens)
- [ ] All SQL uses parameterized queries
- [ ] User input is validated and sanitized
- [ ] No `eval()` or `exec()` with user input
- [ ] Proper error messages (no internal details leaked)

##### Performance
- [ ] No N+1 query patterns
- [ ] Appropriate use of caching
- [ ] No blocking calls in async context
- [ ] Efficient data structures (sets for membership, dicts for lookup)
- [ ] Pagination for large datasets

##### Reliability
- [ ] All errors handled appropriately
- [ ] No silent failures (`except: pass`)
- [ ] Proper logging at appropriate levels
- [ ] Transactions for multi-step operations
- [ ] Timeouts for external calls

##### Maintainability
- [ ] Full type annotations
- [ ] Clear function/variable names
- [ ] Single responsibility principle
- [ ] No god classes/functions
- [ ] Reasonable function length (<50 lines)

##### Testing
- [ ] Critical paths have tests
- [ ] Edge cases covered
- [ ] Mocks used for external dependencies
- [ ] Tests are deterministic (no flaky tests)

#### 3. Review Output Format

```markdown
## Code Review: [File/Feature Name]

### Summary
[1-2 sentence overview of findings]

### Critical Issues (Must Fix)
1. **[Issue Name]** - Line XX
   - Problem: [Description]
   - Risk: [Impact if not fixed]
   - Fix: [Suggested solution]

### High Priority
...

### Medium Priority
...

### Suggestions (Nice to Have)
...

### Positive Observations
[What's done well - important for morale]
```

#### 4. Diff-Based Review Rules

When showing changes:
1. **Show context** - Include surrounding lines for understanding
2. **Explain WHY** - Not just what changed, but why it's better
3. **One concept per diff** - Don't mix unrelated changes

```python
# BEFORE (Problem: blocking in async)
async def fetch_data(url):
    response = requests.get(url)  # BLOCKS EVENT LOOP
    return response.json()

# AFTER (Solution: use aiohttp)
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

---

## 20. refactor-master - Safe Refactoring Protocol

**Trigger:** `/refactor-master`  
**Level:** Senior

### Safe Refactoring Protocol

**Rule #1: Never refactor without tests. Rule #2: One refactor at a time.**

#### Pre-Refactoring Checklist
- [ ] Tests exist and pass
- [ ] You understand the current behavior
- [ ] You have a clear goal for the refactoring
- [ ] You can verify the refactoring didn't break anything

#### Refactoring Catalog

| Refactoring | When to Use | Risk Level |
|-------------|-------------|------------|
| **Rename** | Unclear names | Low |
| **Extract Function** | Long function, repeated code | Low |
| **Extract Class** | Class doing too much | Medium |
| **Move Function** | Function in wrong module | Medium |
| **Replace Conditional with Polymorphism** | Complex if/switch | High |
| **Introduce Parameter Object** | Many parameters | Medium |

#### Extract Function Pattern

```python
# BEFORE - Long function doing too much
async def process_order(order_data: dict):
    # Validate
    if not order_data.get("user_id"):
        raise ValueError("Missing user_id")
    if not order_data.get("items"):
        raise ValueError("Missing items")
    for item in order_data["items"]:
        if item["quantity"] <= 0:
            raise ValueError("Invalid quantity")
    
    # Calculate totals
    subtotal = sum(item["price"] * item["quantity"] for item in order_data["items"])
    tax = subtotal * 0.1
    total = subtotal + tax
    
    # Save to database
    await db.execute("INSERT INTO orders ...")
    
    # Send notification
    await send_email(order_data["user_id"], f"Order total: {total}")

# AFTER - Extracted functions
async def process_order(order_data: dict):
    validate_order(order_data)
    total = calculate_order_total(order_data["items"])
    order_id = await save_order(order_data, total)
    await notify_user(order_data["user_id"], order_id, total)

def validate_order(order_data: dict) -> None:
    if not order_data.get("user_id"):
        raise ValueError("Missing user_id")
    if not order_data.get("items"):
        raise ValueError("Missing items")
    for item in order_data["items"]:
        if item["quantity"] <= 0:
            raise ValueError("Invalid quantity")

def calculate_order_total(items: list[dict]) -> OrderTotal:
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    tax = subtotal * 0.1
    return OrderTotal(subtotal=subtotal, tax=tax, total=subtotal + tax)
```

#### Introduce Parameter Object

```python
# BEFORE - Too many parameters
def create_user(
    discord_id: int,
    username: str,
    email: str,
    avatar_url: str,
    is_premium: bool,
    language: str,
    timezone: str
):
    ...

# AFTER - Parameter object
@dataclass
class CreateUserRequest:
    discord_id: int
    username: str
    email: str
    avatar_url: str
    is_premium: bool = False
    language: str = "en"
    timezone: str = "UTC"

def create_user(request: CreateUserRequest):
    ...
```

#### Replace Conditional with Polymorphism

```python
# BEFORE - Type checking with if/elif
def calculate_discount(user_type: str, amount: float) -> float:
    if user_type == "regular":
        return amount * 0.05
    elif user_type == "premium":
        return amount * 0.15
    elif user_type == "vip":
        return amount * 0.25
    else:
        return 0

# AFTER - Polymorphism
from abc import ABC, abstractmethod

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, amount: float) -> float: ...

class RegularDiscount(DiscountStrategy):
    def calculate(self, amount: float) -> float:
        return amount * 0.05

class PremiumDiscount(DiscountStrategy):
    def calculate(self, amount: float) -> float:
        return amount * 0.15

class VIPDiscount(DiscountStrategy):
    def calculate(self, amount: float) -> float:
        return amount * 0.25

# Usage
DISCOUNT_STRATEGIES = {
    "regular": RegularDiscount(),
    "premium": PremiumDiscount(),
    "vip": VIPDiscount(),
}

def calculate_discount(user_type: str, amount: float) -> float:
    strategy = DISCOUNT_STRATEGIES.get(user_type)
    return strategy.calculate(amount) if strategy else 0
```

---

## 21. anti-pattern-hunter - Code Smell Detection

**Trigger:** `/anti-pattern-hunter`  
**Level:** Senior

### Anti-Pattern Detection Protocol

**Identify and eliminate code that will cause pain later.**

#### Common Anti-Patterns

##### 1. God Class
**Symptom:** One class does everything, thousands of lines
**Solution:** Split by responsibility

```python
# BAD - God class
class Bot:
    def handle_economy(self): ...
    def handle_music(self): ...
    def handle_moderation(self): ...
    def connect_database(self): ...
    def send_notifications(self): ...
    # ... 50 more methods

# GOOD - Separated concerns
class EconomyService: ...
class MusicService: ...
class ModerationService: ...
class Database: ...
class NotificationService: ...
```

##### 2. Anemic Domain Model
**Symptom:** Entities are just data containers, all logic in services
**Solution:** Put behavior in entities

```python
# BAD - Anemic model
@dataclass
class User:
    id: int
    balance: float

class UserService:
    def withdraw(self, user: User, amount: float):
        if user.balance < amount:
            raise InsufficientFundsError()
        user.balance -= amount

# GOOD - Rich domain model
@dataclass
class User:
    id: int
    balance: float
    
    def withdraw(self, amount: float) -> None:
        if self.balance < amount:
            raise InsufficientFundsError(self.balance, amount)
        self.balance -= amount
```

##### 3. Shotgun Surgery
**Symptom:** One change requires modifying many files
**Solution:** Consolidate related code

##### 4. Feature Envy
**Symptom:** Method uses more features of another class than its own
**Solution:** Move method to the class it envies

```python
# BAD - Feature envy
class OrderPrinter:
    def print_order(self, order: Order):
        print(f"Items: {len(order.items)}")
        print(f"Subtotal: {order.subtotal}")
        print(f"Tax: {order.tax}")
        print(f"Total: {order.subtotal + order.tax}")

# GOOD - Logic in Order
class Order:
    def format_receipt(self) -> str:
        return f"""
Items: {len(self.items)}
Subtotal: {self.subtotal}
Tax: {self.tax}
Total: {self.total}
"""
```

##### 5. Primitive Obsession
**Symptom:** Using primitives instead of small objects
**Solution:** Create Value Objects

```python
# BAD - Primitive obsession
def transfer(from_id: int, to_id: int, amount: float, currency: str):
    ...

# GOOD - Value Objects
@dataclass(frozen=True)
class UserId:
    value: int

@dataclass(frozen=True)
class Money:
    amount: float
    currency: str

def transfer(from_user: UserId, to_user: UserId, amount: Money):
    ...
```

##### 6. Leaky Abstraction
**Symptom:** Implementation details leak through abstraction
**Solution:** Hide implementation details

```python
# BAD - Leaky abstraction
class UserRepository:
    async def find(self, user_id: int) -> asyncpg.Record:  # Leaks asyncpg
        ...

# GOOD - Clean abstraction
class UserRepository:
    async def find(self, user_id: int) -> Optional[User]:  # Returns domain object
        ...
```

#### Detection Checklist

| Smell | Question to Ask |
|-------|-----------------|
| God Class | Does this class have more than 5-7 responsibilities? |
| Long Method | Is this method longer than 20-30 lines? |
| Long Parameter List | Does this function have more than 3-4 parameters? |
| Duplicate Code | Have I seen this code somewhere else? |
| Dead Code | Is this code ever executed? |
| Speculative Generality | Am I building for a future that may never come? |
| Magic Numbers | Are there unexplained numeric literals? |

---

# Part IV: UI/UX Skills (NEW)

---

## 22. ui-architect - Design System Protocol

**Trigger:** `/ui-architect`  
**Framework:** Discord Embeds, Buttons, Modals

### Design System Protocol for Discord

Create consistent, beautiful, and accessible Discord interfaces.

#### 1. Color System

```python
from enum import Enum
import discord

class BotColors(Enum):
    # Primary colors
    PRIMARY = 0x5865F2      # Discord Blurple
    SUCCESS = 0x57F287      # Green
    WARNING = 0xFEE75C      # Yellow
    ERROR = 0xED4245        # Red
    INFO = 0x5865F2         # Blue
    
    # Semantic colors
    ECONOMY = 0xF1C40F      # Gold for economy
    MUSIC = 0x1DB954        # Spotify green
    MODERATION = 0xE74C3C   # Red for warnings
    
    # Neutral
    NEUTRAL = 0x2F3136      # Discord dark
    MUTED = 0x99AAB5        # Gray

def create_embed(
    title: str,
    description: str,
    color: BotColors = BotColors.PRIMARY
) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=color.value
    )
```

#### 2. Embed Templates

```python
class EmbedTemplates:
    @staticmethod
    def success(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=BotColors.SUCCESS.value
        )
    
    @staticmethod
    def error(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=BotColors.ERROR.value
        )
    
    @staticmethod
    def warning(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=BotColors.WARNING.value
        )
    
    @staticmethod
    def info(title: str, description: str) -> discord.Embed:
        return discord.Embed(
            title=f"ℹ️ {title}",
            description=description,
            color=BotColors.INFO.value
        )
    
    @staticmethod
    def economy(
        title: str,
        user: discord.User,
        balance: float,
        transaction: Optional[str] = None
    ) -> discord.Embed:
        embed = discord.Embed(
            title=f"💰 {title}",
            color=BotColors.ECONOMY.value
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.add_field(name="Balance", value=f"${balance:,.2f}", inline=True)
        if transaction:
            embed.add_field(name="Transaction", value=transaction, inline=True)
        embed.set_footer(text="BHNBot Economy")
        return embed
```

#### 3. Button Styling Guidelines

| Style | Use For | Example |
|-------|---------|---------|
| `primary` (blurple) | Main actions | Confirm, Submit |
| `secondary` (gray) | Secondary actions | Cancel, Back |
| `success` (green) | Positive confirmations | Accept, Approve |
| `danger` (red) | Destructive actions | Delete, Deny |
| `link` | External URLs | Documentation |

```python
class ConfirmationView(discord.ui.View):
    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.confirmed: Optional[bool] = None
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()
```

#### 4. Pagination Pattern

```python
class PaginatedEmbed(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self._update_buttons()
    
    def _update_buttons(self):
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.pages) - 1
        self.last_page.disabled = self.current_page == len(self.pages) - 1
    
    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[0], view=self)
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
    
    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[-1], view=self)
```

#### 5. Discord Formatting Reference

| Format | Syntax | Result |
|--------|--------|--------|
| Bold | `**text**` | **text** |
| Italic | `*text*` | *text* |
| Underline | `__text__` | <u>text</u> |
| Strikethrough | `~~text~~` | ~~text~~ |
| Code | `` `code` `` | `code` |
| Code Block | `` ```lang\ncode``` `` | Code block |
| Quote | `> text` | Quote block |
| Spoiler | `\|\|text\|\|` | Spoiler |
| Timestamp | `<t:unix:R>` | Relative time |

---

## 23. accessibility-ops - WCAG Compliance Protocol

**Trigger:** `/accessibility-ops`  
**Standard:** WCAG 2.1

### Accessibility Protocol for Discord Bots

Make your bot usable by everyone.

#### 1. Text Accessibility

```python
# GOOD - Clear, descriptive text
embed.add_field(
    name="Your Balance",
    value="$1,234.56 USD",
    inline=True
)

# BAD - Icon-only, no screen reader support
embed.add_field(
    name="💰",
    value="1234.56",
    inline=True
)
```

#### 2. Color Accessibility

- Never rely on color alone to convey information
- Always include text labels or icons

```python
# GOOD - Color + Icon + Text
embed = discord.Embed(
    title="✅ Success",
    description="Your transfer was completed successfully.",
    color=BotColors.SUCCESS.value
)

# BAD - Color only (colorblind users can't distinguish)
embed = discord.Embed(color=0x00FF00)  # Just green, no context
```

#### 3. Alternative Text

```python
# For important images, include descriptions
embed.set_image(url="https://example.com/chart.png")
embed.add_field(
    name="Chart Description",
    value="Bar chart showing monthly earnings: Jan $100, Feb $150, Mar $200"
)
```

#### 4. Keyboard Navigation

- Ensure all interactive elements work with buttons
- Provide clear labels for buttons
- Use consistent positioning

#### 5. Timing Considerations

```python
# Give users enough time to interact
view = MyView(timeout=180.0)  # 3 minutes, not 30 seconds

# Warn before timeout
embed.set_footer(text="This menu will expire in 3 minutes")
```

#### 6. Error Messages

```python
# GOOD - Specific, actionable error
embed = EmbedTemplates.error(
    title="Transfer Failed",
    description=(
        "You don't have enough funds for this transfer.\n\n"
        f"**Your balance:** ${user.balance:,.2f}\n"
        f"**Amount requested:** ${amount:,.2f}\n"
        f"**Shortfall:** ${amount - user.balance:,.2f}\n\n"
        "Use `/deposit` to add funds to your account."
    )
)

# BAD - Vague error
embed = EmbedTemplates.error(
    title="Error",
    description="Something went wrong. Try again."
)
```

---

# Part V: OpenCode Agent System (oh-my-opencode)

> **Complete reference for the specialized AI agent team**
>
> This section documents ALL agents defined in `oh-my-opencode.json` and provides
> Sisyphus (the primary orchestrator) with detailed guidance on when and how to
> delegate work to each specialized sub-agent.

---

## Agent Overview & Cost Matrix

### The Agent Team (12 Agents)

| Agent | Model | Role | Cost | Permissions |
|-------|-------|------|------|-------------|
| **Sisyphus** | antigravity-claude-opus-4-5-thinking | Primary Orchestrator | 💎 PREMIUM | edit, bash, webfetch, external_directory |
| **oracle** | github-copilot/gpt-5.2 | Deep Reasoner | 💰 EXPENSIVE | READ ONLY |
| **librarian** | perplexity/sonar-reasoning-pro | Researcher | 💵 PAID | webfetch only |
| **explore** | github-copilot/grok-code-fast-1 | Scout | 🆓 FREE | bash only |
| **devops-master** | github-copilot/gpt-5.1-codex | Infrastructure Engineer | 💰 MEDIUM | edit, bash |
| **qa-engineer** | github-copilot/claude-sonnet-4.5 | Code Reviewer | 💵 MEDIUM | READ ONLY |
| **test-writer** | opencode/grok-code | Test Engineer | 🆓 FREE | edit, bash |
| **frontend-ui-ux-engineer** | antigravity-gemini-3-pro | UI Specialist | 💰 MEDIUM | edit, bash, webfetch |
| **market-analyst** | antigravity-gemini-3-flash | Product Researcher | 💵 CHEAP | webfetch only |
| **document-writer** | antigravity-gemini-3-flash | Scribe | 💵 CHEAP | edit only |
| **multimodal-looker** | antigravity-gemini-3-pro-high | Visual Interpreter | 💰 MEDIUM | - |
| **general** | opencode/grok-code | General/Fallback | 🆓 FREE | edit, bash |

### Cost Classification

```
🆓 FREE      → explore, test-writer, general (use liberally, fire in parallel)
💵 CHEAP     → market-analyst, document-writer
💵 PAID      → librarian (Perplexity API)
💰 MEDIUM    → devops-master, qa-engineer, frontend-ui-ux-engineer, multimodal-looker
💰 EXPENSIVE → oracle (consult wisely, announce before invocation)
💎 PREMIUM   → Sisyphus (you - the orchestrator)
```

### Provider Distribution

| Provider | Agents | Auth Method |
|----------|--------|-------------|
| **Antigravity (Google)** | Sisyphus, frontend, market-analyst, document-writer, multimodal | OAuth (7 accounts) |
| **GitHub Copilot** | oracle, explore, devops-master, qa-engineer | OAuth |
| **Perplexity** | librarian | API Key |
| **OpenCode** | test-writer, general | FREE (no auth) |

---

## 1. Sisyphus - The Primary Orchestrator

**Model:** `google/antigravity-claude-opus-4-5-thinking`  
**Temperature:** 0.3  
**Permissions:** edit, bash, webfetch, external_directory (FULL ACCESS)

### Role
Primary Architect and Orchestrator. Responsible for session state, high-level planning, and delegating tasks to specialized sub-agents. Maintains the "God Mode" perspective.

### Responsibilities
- Receive and analyze user requests
- Break down complex tasks into subtasks
- Delegate work to appropriate specialized agents
- Verify and integrate results from sub-agents
- Maintain context across the session
- Make final decisions on implementation

### Key Behaviors
```
1. NEVER work alone when specialists are available
2. Fire explore/librarian in PARALLEL (background_task)
3. Delegate visual work to frontend-ui-ux-engineer
4. Consult oracle for complex architecture decisions
5. Use qa-engineer to review significant code changes
```

---

## 2. oracle - The Deep Reasoner

**Model:** `github-copilot/gpt-5.2`  
**Temperature:** 0.7  
**Permissions:** READ ONLY (no edit, no bash, no webfetch)

### Role
A pure logic engine consulted for architectural paradoxes, complex debugging, and algorithmic challenges. Does NOT write boilerplate code.

### When to Invoke

| Trigger | Action |
|---------|--------|
| Complex architecture design | Oracle FIRST, then implement |
| 2+ failed fix attempts | Oracle FIRST, then implement |
| Unfamiliar code patterns | Oracle FIRST, then implement |
| Security/performance concerns | Oracle FIRST, then implement |
| Multi-system tradeoffs | Oracle FIRST, then implement |
| After completing significant work | Oracle for review |

### When NOT to Invoke
- Simple file operations (use direct tools)
- First attempt at any fix (try yourself first)
- Questions answerable from code you've read
- Trivial decisions (variable names, formatting)
- Things inferable from existing patterns

### Invocation Pattern
```python
# ALWAYS announce before invoking oracle
"Consulting Oracle for [specific reason]..."

# Then invoke
task(
    subagent_type="oracle",
    description="Architecture review for...",
    prompt="""
    CONTEXT: [Full context of the problem]
    QUESTION: [Specific question]
    CONSTRAINTS: [Any limitations]
    EXPECTED OUTPUT: [What you need back]
    """
)
```

### Anti-Patterns
```
❌ "Hey oracle, can you help me?"  # Too vague
❌ Asking oracle to write boilerplate code
❌ Using oracle for simple debugging
❌ Invoking oracle without announcing first

✅ "Oracle, analyze the tradeoffs between CQRS and traditional..."
✅ "Oracle, why does this race condition occur despite locking?"
✅ "Oracle, review this architecture decision before I implement"
```

---

## 3. librarian - The Researcher

**Model:** `perplexity/sonar-reasoning-pro`  
**Temperature:** 0.2  
**Permissions:** webfetch only (no edit, no bash)

### Role
The Researcher. Grounded in real-time web data. Responsible for fetching documentation, verifying library versions (discord.py, fastapi), and finding solutions to errors.

### When to Invoke
- Unfamiliar libraries or packages
- Need official API documentation
- Library best practices & quirks
- OSS implementation examples
- Error messages from unknown sources
- Version compatibility questions

### Trigger Phrases (Fire Immediately)
```
"How do I use [library]?"
"What's the best practice for [framework feature]?"
"Why does [external dependency] behave this way?"
"Find examples of [library] usage"
"Working with unfamiliar npm/pip/cargo packages"
```

### Invocation Pattern
```python
# ALWAYS run in background, ALWAYS parallel with explore
background_task(
    agent="librarian",
    prompt="""
    TASK: Find [specific information needed]
    LIBRARY: [library name and version if known]
    CONTEXT: [Why you need this information]
    RETURN: [Specific deliverables - code examples, API docs, etc.]
    """
)

# Continue working immediately, collect results later
task_id = "librarian_task_123"
# ... do other work ...
result = background_output(task_id)
```

### Best Practices
```
✅ Fire librarian + explore in parallel
✅ Be specific about what documentation you need
✅ Ask for code examples, not just explanations
✅ Include library version when asking about compatibility

❌ Wait synchronously for librarian results
❌ Ask librarian about YOUR codebase (use explore)
❌ Use librarian for internal patterns (use explore)
```

---

## 4. explore - The Scout

**Model:** `github-copilot/grok-code-fast-1`  
**Temperature:** 0.1  
**Permissions:** bash only (no edit, no webfetch)

### Role
The Scout. A high-speed, low-cost agent for mapping directories, listing files, and reading content. Optimized for latency.

### When to Invoke
- Multiple search angles needed
- Unfamiliar module structure
- Cross-layer pattern discovery
- Need to understand codebase organization
- Finding all usages of a pattern

### Cost: FREE - Use Liberally
```
explore = Contextual Grep (internal codebase search)
Use as a PEER TOOL, not a fallback
Fire in parallel with librarian when needed
```

### Invocation Pattern
```python
# ALWAYS run in background
background_task(
    agent="explore",
    prompt="""
    TASK: Find [what you're looking for]
    SCOPE: [directories or file patterns]
    CONTEXT: [Why you need this]
    RETURN: File paths, code snippets, patterns found
    """
)

# Fire multiple explores in parallel for different aspects
background_task(agent="explore", prompt="Find all database access patterns...")
background_task(agent="explore", prompt="Find all error handling patterns...")
background_task(agent="explore", prompt="Find how authentication is implemented...")
```

### When to Use Direct Tools Instead
```
Use Direct Tools:
- You know exactly what to search
- Single keyword/pattern suffices
- Known file location

Use Explore:
- Multiple search angles needed
- Unfamiliar module structure
- Cross-layer pattern discovery
```

---

## 5. devops-master - The Infrastructure Engineer

**Model:** `github-copilot/gpt-5.1-codex`  
**Temperature:** 0.1  
**Permissions:** edit, bash (no webfetch)

### Role
The Infrastructure Engineer. Specializes in Docker, PostgreSQL configuration, Redis, and CI/CD pipelines. Enforces strict syntax compliance.

### When to Invoke
- Docker/docker-compose configuration
- PostgreSQL setup and optimization
- Redis configuration
- CI/CD pipeline creation (GitHub Actions, etc.)
- Infrastructure as Code (Terraform, etc.)
- Environment configuration
- Deployment scripts

### Invocation Pattern
```python
task(
    subagent_type="devops-master",
    description="Configure Docker for production...",
    prompt="""
    TASK: [Specific infrastructure task]
    ENVIRONMENT: [dev/staging/prod]
    REQUIREMENTS: [Performance, security constraints]
    EXISTING: [What's already configured]
    MUST DO: [Explicit requirements]
    MUST NOT DO: [Forbidden actions]
    """
)
```

### Delegation Checklist
```
✅ Create Dockerfiles and docker-compose.yml
✅ Configure PostgreSQL connection pooling
✅ Set up GitHub Actions workflows
✅ Write deployment scripts
✅ Configure environment variables

❌ Write application business logic
❌ Design API endpoints
❌ Create UI components
```

---

## 6. qa-engineer - The Reviewer

**Model:** `github/claude-sonnet-4.5`  
**Temperature:** 0.2  
**Permissions:** READ ONLY (no edit, no bash, no webfetch)

### Role
The Reviewer. Analyzes code diffs for security vulnerabilities, logic errors, and style violations. Uses cost-effective reasoning for exhaustive checks.

### When to Invoke
- After significant code changes
- Before merging PRs
- Security-sensitive code review
- Performance-critical code review
- When you need a second opinion

### Invocation Pattern
```python
task(
    subagent_type="qa-engineer",
    description="Review security of auth changes...",
    prompt="""
    TASK: Review the following code changes
    FOCUS: [security/performance/logic/style]
    CODE:
    ```python
    [code to review]
    ```
    CONTEXT: [What this code does]
    RETURN: Issues found with severity classification
    """
)
```

### Review Categories
```
CRITICAL: Security vulnerabilities, data loss risks
HIGH: Logic errors, performance issues
MEDIUM: Code smells, maintainability issues
LOW: Style violations, documentation gaps
```

---

## 7. frontend-ui-ux-engineer - The UI Specialist

**Model:** `google/antigravity-gemini-3-pro`  
**Temperature:** 0.5  
**Permissions:** edit, bash, webfetch (FULL ACCESS for frontend)

### Role
The UI Specialist. Handles React, Tailwind CSS, and dashboard components. Leverages multimodal understanding and large context windows.

### When to Invoke (MANDATORY for Visual Changes)

**ALWAYS delegate when these keywords are involved:**
```
style, className, tailwind, color, background, border, shadow,
margin, padding, width, height, flex, grid, animation, transition,
hover, responsive, font-size, icon, svg
```

### Frontend Files Decision Gate

| Change Type | Examples | Action |
|-------------|----------|--------|
| **Visual/UI/UX** | Color, spacing, layout, typography, animation | **DELEGATE** |
| **Pure Logic** | API calls, data fetching, state management | Handle directly |
| **Mixed** | Both visual AND logic | Split: logic yourself, visual → delegate |

### Invocation Pattern
```python
task(
    subagent_type="frontend-ui-ux-engineer",
    description="Create responsive dashboard component...",
    prompt="""
    TASK: [Specific UI task]
    DESIGN: [Visual requirements, mockup description]
    FRAMEWORK: [React/Vue/Svelte + CSS framework]
    COMPONENTS: [Existing components to reference]
    MUST DO: [Accessibility, responsiveness requirements]
    MUST NOT DO: [Forbidden patterns]
    CONTEXT: [File paths, existing styles]
    """
)
```

---

## 8. market-analyst - The Product Researcher

**Model:** `google/antigravity-gemini-3-flash`  
**Temperature:** 0.7  
**Permissions:** webfetch only (no edit, no bash)

### Role
The Product Researcher. Analyzes competitor bots, market trends, and feature sets to inform the roadmap.

### When to Invoke
- Feature research and ideation
- Competitive analysis
- Market trends for Discord bots
- Best practices from successful bots
- User engagement patterns

### Reference Knowledge Base
```
Economy Bots: OwO Bot, Poketwo, Gelbpunkt/IdleRPG
Music Bots: Green-bot, Lavalink/Rainlink bots
Moderation: YAGPDB, DraconianBot, Cronus
Dashboard: Cially, Fluxpoint, Discord-BOT-Dashboard-V2
Leveling: MEE6, Tatsu, AmariBot
Utility: Carl-bot, Dyno
```

### Invocation Pattern
```python
task(
    subagent_type="market-analyst",
    description="Research economy bot features...",
    prompt="""
    TASK: Analyze [feature/category]
    COMPETITORS: [Specific bots to study]
    FOCUS: [Engagement, monetization, UX]
    RETURN: Feature comparison, recommendations, implementation ideas
    """
)
```

---

## 9. document-writer - The Scribe

**Model:** `google/antigravity-gemini-3-flash`  
**Temperature:** 0.3  
**Permissions:** edit only (no bash, no webfetch)

### Role
The Scribe. Generates technical documentation, changelogs, and READMEs. Uses the massive context window to synthesize project-wide knowledge.

### When to Invoke
- README creation/updates
- API documentation
- Changelog generation
- Architecture documentation
- User guides
- Code comments and docstrings

### Invocation Pattern
```python
task(
    subagent_type="document-writer",
    description="Generate API documentation...",
    prompt="""
    TASK: [Specific documentation task]
    SCOPE: [What to document]
    FORMAT: [Markdown, OpenAPI, etc.]
    AUDIENCE: [Developers, end users, etc.]
    STYLE: [Technical level, tone]
    MUST INCLUDE: [Required sections]
    MUST NOT INCLUDE: [Sensitive info, etc.]
    """
)
```

---

## 10. multimodal-looker - The Eye

**Model:** `google/antigravity-gemini-3-pro-high`  
**Temperature:** N/A (Visual processing)  
**Permissions:** Visual interpretation only

### Role
The Eye. Specialized in interpreting visual data, screenshots, and diagrams for the team.

### When to Invoke
- Analyzing UI screenshots
- Interpreting diagrams and flowcharts
- Understanding visual designs
- Extracting information from images
- Comparing visual implementations

### Invocation Pattern
```python
task(
    subagent_type="multimodal-looker",
    description="Analyze dashboard screenshot...",
    prompt="""
    TASK: [What to analyze in the image]
    IMAGE: [Path or URL to image]
    FOCUS: [Specific elements to examine]
    RETURN: [Detailed description, issues found, etc.]
    """
)
```

---

## 11. test-writer - The Test Engineer

**Model:** `opencode/grok-code`  
**Temperature:** 0.2  
**Permissions:** edit, bash (no webfetch)  
**Cost:** 🆓 FREE

### Role
The Test Engineer. Generates unit tests, integration tests, and test fixtures. Uses TDD principles. This agent WRITES tests, while qa-engineer only REVIEWS code.

### When to Invoke
- Writing unit tests for new features
- Creating integration test suites
- Generating test fixtures and mocks
- Implementing TDD workflow (test first, then code)
- Adding regression tests after bug fixes

### Invocation Pattern
```python
task(
    subagent_type="test-writer",
    description="Write unit tests for EconomyService...",
    prompt="""
    TASK: Write comprehensive unit tests for [component]
    FILE: [path to file being tested]
    FRAMEWORK: pytest (with pytest-asyncio for async)
    COVERAGE: [specific methods/functions to test]
    MUST DO:
      - Use AAA pattern (Arrange, Act, Assert)
      - Mock external dependencies
      - Include edge cases and error scenarios
      - Follow existing test patterns in tests/
    MUST NOT DO:
      - Modify production code
      - Skip error case testing
    CONTEXT: [existing test examples, fixtures available]
    """
)
```

### Test Categories to Generate
```
Unit Tests:
  - Individual function behavior
  - Edge cases (empty, null, boundary values)
  - Error handling paths

Integration Tests:
  - Service layer interactions
  - Database operations
  - External API mocks

Fixtures:
  - Mock users, guilds, channels
  - Test database setup/teardown
  - Fake external services
```

---

## 12. general - The Fallback Agent

**Model:** `opencode/grok-code`  
**Temperature:** 0.3  
**Permissions:** edit, bash (no webfetch)  
**Cost:** 🆓 FREE

### Role
General-purpose FREE agent for simple tasks, quick fixes, and fallback when other agents are rate-limited. Use when:
1. Task is too simple for specialized agents
2. Primary agents are rate-limited
3. Need quick parallel workers for grunt work

### When to Invoke
- Simple code generation tasks
- Quick file modifications
- Backup when GitHub Copilot is rate-limited
- Parallel grunt work (many small tasks)
- Cost-conscious operations

### Invocation Pattern
```python
# As primary for simple tasks
task(
    subagent_type="general",
    description="Add logging to function...",
    prompt="""
    TASK: [Simple, well-defined task]
    FILE: [target file]
    MUST DO: [specific requirements]
    MUST NOT DO: [constraints]
    """
)

# As parallel workers
for file in files_to_process:
    background_task(
        agent="general",
        prompt=f"Add type hints to all functions in {file}"
    )
```

### Best Practices
```
✅ Use for simple, well-defined tasks
✅ Fire multiple in parallel for batch operations
✅ Use as fallback when premium agents are rate-limited
✅ Perfect for code formatting, adding comments, simple refactors

❌ Don't use for complex architecture decisions (use oracle)
❌ Don't use for security-sensitive code (use qa-engineer to review)
❌ Don't use for UI work (use frontend-ui-ux-engineer)
```

---

## Agent Selection Decision Tree

```
User Request Received
    │
    ├── Is this about EXTERNAL libraries/docs?
    │   └── YES → Fire librarian (background)
    │
    ├── Does it involve MULTIPLE modules?
    │   └── YES → Fire explore (background)
    │
    ├── Is this VISUAL/UI work?
    │   └── YES → Delegate to frontend-ui-ux-engineer
    │
    ├── Is this INFRASTRUCTURE work?
    │   └── YES → Delegate to devops-master
    │
    ├── Is this DOCUMENTATION?
    │   └── YES → Delegate to document-writer
    │
    ├── Need COMPETITIVE research?
    │   └── YES → Fire market-analyst (background)
    │
    ├── Need to ANALYZE an image?
    │   └── YES → Use multimodal-looker
    │
    ├── Is this COMPLEX architecture/debugging?
    │   └── YES → Consult oracle (announce first)
    │
    ├── After SIGNIFICANT code changes?
    │   └── YES → Use qa-engineer for review
    │
    └── Otherwise → Handle directly (Sisyphus)
```

---

## Parallel Execution Patterns

### Default Pattern: Fire and Continue
```python
# 1. Launch parallel agents (receive task_ids)
explore_task = background_task(
    agent="explore",
    prompt="Find auth implementations in our codebase..."
)
librarian_task = background_task(
    agent="librarian",
    prompt="Find JWT best practices in official docs..."
)

# 2. Continue immediate work while agents run

# 3. Collect results when needed
explore_result = background_output(task_id=explore_task)
librarian_result = background_output(task_id=librarian_task)

# 4. BEFORE final answer: Cancel all running tasks
background_cancel(all=True)
```

### Common Parallel Combinations

| Scenario | Agents to Fire in Parallel |
|----------|----------------------------|
| New feature research | explore + librarian + market-analyst |
| Bug investigation | explore (multiple angles) |
| Architecture design | librarian + oracle (after initial research) |
| Code review | qa-engineer + (optional) oracle for complex parts |
| Documentation | explore (to gather info) + document-writer |

---

## Delegation Prompt Structure (MANDATORY)

When delegating to ANY sub-agent, include ALL 7 sections:

```markdown
1. TASK: Atomic, specific goal (one action per delegation)
2. EXPECTED OUTCOME: Concrete deliverables with success criteria
3. REQUIRED SKILLS: Which skill to invoke (if applicable)
4. REQUIRED TOOLS: Explicit tool whitelist (prevents tool sprawl)
5. MUST DO: Exhaustive requirements - leave NOTHING implicit
6. MUST NOT DO: Forbidden actions - anticipate and block rogue behavior
7. CONTEXT: File paths, existing patterns, constraints
```

### Example Delegation
```python
task(
    subagent_type="frontend-ui-ux-engineer",
    description="Create Discord embed design system",
    prompt="""
    1. TASK: Create a standardized embed template system for BHNBot

    2. EXPECTED OUTCOME:
       - EmbedTemplates class with success/error/info/economy methods
       - BotColors enum with semantic color definitions
       - Working code that matches existing patterns

    3. REQUIRED SKILLS: /ui-architect

    4. REQUIRED TOOLS: read, edit (for ui/ files only)

    5. MUST DO:
       - Follow existing code style (Google docstrings)
       - Use discord.py 2.0+ patterns
       - Include type hints on all methods
       - Match colors to Discord's design system

    6. MUST NOT DO:
       - Create new files outside cogs/<feature>/ui/
       - Modify any existing logic code
       - Use deprecated discord.py patterns

    7. CONTEXT:
       - File: cogs/fishing/ui/embeds.py (reference)
       - Style: Vietnamese user-facing, English code
       - Framework: discord.py 2.3+
    """
)
```

---

## Post-Delegation Verification Checklist

**ALWAYS verify after delegated work completes:**

- [ ] Does it work as expected?
- [ ] Does it follow existing codebase patterns?
- [ ] Expected result came out?
- [ ] Did the agent follow "MUST DO" requirements?
- [ ] Did the agent avoid "MUST NOT DO" restrictions?
- [ ] Run `lsp_diagnostics` on changed files

---

## Quick Reference: Skill Invocation

### Project-Specific Skills (Discord Bot)

| Skill | Command | Use When |
|-------|---------|----------|
| discord-arch | `/discord-arch` | Designing new features, refactoring structure |
| python-godmode | `/python-godmode` | Writing/reviewing Python code |
| postgres-supreme | `/postgres-supreme` | Database operations, migrations |
| algo-god | `/algo-god` | Performance optimization, scaling |
| debug-protocol | `/debug-protocol` | Fixing bugs, analyzing errors |
| qa-engineer | `/qa-engineer` | Writing tests, TDD |
| sec-ops | `/sec-ops` | Security review, input validation |
| git-commander | `/git-commander` | Git operations, branching |
| devops-master | `/devops-master` | Docker, CI/CD, deployment |
| fullstack-bridge | `/fullstack-bridge` | API design, web dashboard |
| market-analyst | `/market-analyst` | Feature research, competitive analysis |
| reverse-engineer | `/reverse-engineer` | Analyzing external code |
| cog-template | `/cog-template` | Creating new bot features |

### Advanced Architecture Skills

| Skill | Command | Use When |
|-------|---------|----------|
| ddd-master | `/ddd-master` | Domain modeling, bounded contexts |
| hexagonal-arch | `/hexagonal-arch` | Ports & adapters, dependency inversion |
| cqrs-architect | `/cqrs-architect` | Separating read/write operations |
| event-sourcing | `/event-sourcing` | Audit trails, event-driven state |
| clean-arch | `/clean-arch` | Layer organization, use cases |

### Code Quality Skills

| Skill | Command | Use When |
|-------|---------|----------|
| code-auditor | `/code-auditor` | Systematic code review |
| refactor-master | `/refactor-master` | Safe refactoring techniques |
| anti-pattern-hunter | `/anti-pattern-hunter` | Detecting code smells |

### UI/UX Skills

| Skill | Command | Use When |
|-------|---------|----------|
| ui-architect | `/ui-architect` | Discord embeds, buttons, design system |
| accessibility-ops | `/accessibility-ops` | Making bot accessible to all users |

---

## Skill Combination Patterns

### New Feature Development
```
1. /market-analyst     → Research how others solved it
2. /ddd-master         → Model the domain
3. /discord-arch       → Structure the feature
4. /cog-template       → Generate boilerplate
5. /python-godmode     → Implement with best practices
6. /qa-engineer        → Write tests
7. /code-auditor       → Review the code
```

### Performance Optimization
```
1. /algo-god           → Identify bottlenecks
2. /postgres-supreme   → Optimize queries
3. /cqrs-architect     → Consider read/write separation
4. /refactor-master    → Apply optimizations safely
```

### Bug Investigation
```
1. /debug-protocol     → Analyze the error
2. /reverse-engineer   → Understand the code flow
3. /qa-engineer        → Write regression test
4. /code-auditor       → Review the fix
```

### Architecture Review
```
1. /hexagonal-arch     → Check layer boundaries
2. /clean-arch         → Verify dependency direction
3. /anti-pattern-hunter → Find code smells
4. /ddd-master         → Validate domain model
```

---

*Generated for BHNBot - Discord Bot with Music & Economy Features*
*Last Updated: January 2026*
*Enhanced with Superpowers & Beads patterns*

---

# Part VII: Superpowers Integration (Enhanced Skills)

> **Based on [obra/superpowers](https://github.com/obra/superpowers) (21.5k ⭐) and [steveyegge/beads](https://github.com/steveyegge/beads) (10.1k ⭐)**
>
> These are MANDATORY behavioral upgrades for all agents, especially Sisyphus.

---

## Iron Laws (NON-NEGOTIABLE)

### Iron Law #1: TDD or DELETE
```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST

If you wrote production code before a test:
  → DELETE THE CODE
  → Write the test first
  → Watch it FAIL (proves test works)
  → THEN write the code

Common rationalizations (ALL WRONG):
  ❌ "This is too simple to need a test"
  ❌ "I'll add tests after I get it working"
  ❌ "Writing tests after achieves the same goals"
```

### Iron Law #2: Root Cause Before Fix
```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST

Before ANY fix attempt:
  1. Read the FULL error message
  2. Reproduce the error
  3. Check recent changes
  4. Form a hypothesis with EVIDENCE

If 3+ fix attempts failed:
  → STOP everything
  → Question the architecture
  → Consult oracle
```

### Iron Law #3: Verification Before Completion
```
NEVER claim "done" without EVIDENCE

Required evidence:
  ✅ Tests pass (not just "should pass")
  ✅ lsp_diagnostics clean
  ✅ Build succeeds (if applicable)
  ✅ Manual verification if needed

"It should work" is NOT evidence.
```

---

## 1. tdd-master - Test-Driven Development (Superpowers)

**Trigger:** `/tdd-master`  
**Source:** obra/superpowers  
**Iron Law:** NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST

### The RED-GREEN-REFACTOR Cycle

```
┌─────────────────────────────────────────────────────┐
│  RED: Write a failing test                          │
│       └── Test MUST fail first (proves it works)    │
│                         ↓                           │
│  GREEN: Write MINIMAL code to pass                  │
│       └── Just enough, no more                      │
│                         ↓                           │
│  REFACTOR: Clean up while tests stay green          │
│       └── Improve structure, keep behavior          │
│                         ↓                           │
│  REPEAT: Next test case                             │
└─────────────────────────────────────────────────────┘
```

### TDD Workflow for Agents

```python
# 1. FIRST: Write the test
async def test_transfer_insufficient_funds_raises_error():
    user = User(id=1, balance=50)
    with pytest.raises(InsufficientFundsError):
        await transfer(user, amount=100)

# 2. Run test → MUST FAIL (RED)
# If it passes, your test is WRONG

# 3. Write MINIMAL code to pass
async def transfer(user: User, amount: float):
    if amount > user.balance:
        raise InsufficientFundsError()
    # ... rest of implementation

# 4. Run test → MUST PASS (GREEN)

# 5. REFACTOR: Clean up, add more tests
```

### Anti-Patterns (BLOCKING)

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| Code before test | You don't know if test actually tests the right thing |
| Test passes on first run | Test might be wrong, not proving anything |
| Skipping RED phase | "It's obvious" - famous last words |
| Multiple features per cycle | One behavior per RED-GREEN-REFACTOR |

---

## 2. systematic-debugging - 4-Phase Root Cause Protocol (Superpowers)

**Trigger:** `/systematic-debugging`  
**Source:** obra/superpowers  
**Iron Law:** NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST

### The 4 Phases

```
Phase 1: ROOT CAUSE INVESTIGATION
├── Read FULL error message (stack trace, line numbers)
├── Reproduce the error reliably
├── Check recent changes (git diff, git log)
├── Gather evidence (logs, state, inputs)
└── Form hypothesis with EVIDENCE

Phase 2: PATTERN ANALYSIS
├── Find working examples of similar code
├── Compare working vs broken code
├── Identify the DIFFERENCE
└── Narrow down to specific component

Phase 3: HYPOTHESIS TESTING
├── ONE hypothesis at a time
├── Make MINIMAL change to test
├── Observe result
└── If wrong, REVERT and try next hypothesis

Phase 4: IMPLEMENTATION
├── Write failing test that reproduces bug
├── Apply SINGLE fix
├── Verify test passes
└── Check for regressions
```

### The 3-Strike Rule

```
If 3 consecutive fix attempts FAILED:
  
  ┌─────────────────────────────────────────┐
  │ STOP. Something is fundamentally wrong. │
  └─────────────────────────────────────────┘
  
  Actions:
  1. REVERT all attempted fixes
  2. Document what was tried
  3. Question the architecture
  4. Consult oracle with FULL context
  5. Consider if requirements are correct
```

### Debugging Anti-Patterns

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Shotgun debugging (random changes) | One hypothesis, one change |
| "Let me try this..." without evidence | Gather evidence first |
| Fixing symptoms instead of cause | Find ROOT cause |
| Continuing after 3 failures | STOP, escalate, reconsider |

---

## 3. subagent-driven-development - Orchestrated Delegation (Superpowers)

**Trigger:** `/subagent-driven-development`  
**Source:** obra/superpowers

### The Two-Stage Review Protocol

```
                    ┌──────────────┐
                    │   DISPATCH   │
                    │ (Sisyphus)   │
                    └──────┬───────┘
                           │ Clear spec + constraints
                           ▼
                    ┌──────────────┐
                    │ IMPLEMENTER  │
                    │ (Subagent)   │
                    └──────┬───────┘
                           │ Code complete
                           ▼
              ┌────────────────────────────┐
              │   STAGE 1: SPEC REVIEW     │
              │   "Does code match spec?"  │
              │   (qa-engineer)            │
              └────────────┬───────────────┘
                           │ Spec compliant
                           ▼
              ┌────────────────────────────┐
              │  STAGE 2: QUALITY REVIEW   │
              │  "Is code well-written?"   │
              │  (qa-engineer or oracle)   │
              └────────────┬───────────────┘
                           │ Quality approved
                           ▼
                    ┌──────────────┐
                    │   COMPLETE   │
                    └──────────────┘
```

### Review Order Matters

```
SPEC COMPLIANCE FIRST, QUALITY SECOND

Why this order?
1. Correct but ugly code → can be refactored
2. Beautiful but wrong code → waste of time

Stage 1 Questions (Spec):
  - Does it do what was asked?
  - Are all requirements met?
  - Any missing functionality?

Stage 2 Questions (Quality):
  - Is code readable?
  - Are there edge cases?
  - Performance concerns?
  - Security issues?
```

### Subagent Dispatch Template

```python
task(
    subagent_type="[implementer]",
    description="[atomic task]",
    prompt="""
    SPEC:
      - [Requirement 1]
      - [Requirement 2]
      - [Requirement 3]
    
    CONSTRAINTS:
      - [Constraint 1]
      - [Constraint 2]
    
    SUCCESS CRITERIA:
      - [How to know it's done]
    
    CONTEXT:
      - [Relevant files]
      - [Existing patterns]
    """
)

# After implementer completes:
task(
    subagent_type="qa-engineer",
    description="Spec compliance review",
    prompt="Review if code matches spec: [spec summary]"
)

task(
    subagent_type="qa-engineer", 
    description="Quality review",
    prompt="Review code quality, edge cases, security"
)
```

---

## 4. landing-the-plane - Session Completion Protocol (Beads)

**Trigger:** `/landing-the-plane`  
**Source:** steveyegge/beads  
**Rule:** NEVER end session with uncommitted work

### The Landing Checklist

```
Before ending ANY session:

□ Step 1: FILE REMAINING WORK
  └── Create todos for unfinished tasks
  └── Document blockers and context

□ Step 2: RUN QUALITY GATES
  └── lsp_diagnostics on all changed files
  └── Run tests if applicable
  └── Build if applicable

□ Step 3: CLOSE FINISHED ITEMS
  └── Mark completed todos as done
  └── Update any tracking

□ Step 4: GIT SYNC (NON-NEGOTIABLE if user requests commit)
  └── git add .
  └── git commit -m "descriptive message"
  └── git push (if requested)

□ Step 5: CLEAN UP
  └── Remove temp files
  └── Cancel background agents: background_cancel(all=True)

□ Step 6: VERIFY CLEAN STATE
  └── git status shows clean
  └── No orphaned processes

□ Step 7: PROVIDE CONTINUATION PROMPT
  └── Summary of what was done
  └── What remains to be done
  └── Copy-paste prompt for next session
```

### Anti-Patterns

```
❌ "Ready to push when you are"
   → YOU must push (if requested), don't defer to user

❌ Ending with uncommitted changes
   → Always offer to commit before ending

❌ No context for next session
   → Always provide continuation prompt

❌ Leaving background agents running
   → Always cancel: background_cancel(all=True)
```

---

## 5. ready-work-detection - Dependency-Aware Task Management (Beads)

**Trigger:** `/ready-work`  
**Source:** steveyegge/beads

### Dependency Types

```
┌─────────────────────────────────────────────────────────┐
│  BLOCKS: Task A blocks Task B                           │
│  └── B cannot start until A is complete                 │
│                                                         │
│  RELATED: Tasks share context                           │
│  └── Changes to one may affect the other                │
│                                                         │
│  PARENT-CHILD: Hierarchical breakdown                   │
│  └── Parent complete when all children done             │
│                                                         │
│  DISCOVERED-FROM: Found during investigation            │
│  └── "While working on X, found we also need Y"         │
└─────────────────────────────────────────────────────────┘
```

### Ready Work Algorithm

```python
def get_ready_tasks(all_tasks: list[Task]) -> list[Task]:
    """Return tasks that can be worked on NOW."""
    ready = []
    for task in all_tasks:
        if task.status == "completed":
            continue
        if task.status == "in_progress":
            continue
        
        # Check if all blockers are resolved
        blockers = get_blocking_tasks(task)
        if all(b.status == "completed" for b in blockers):
            ready.append(task)
    
    return sorted(ready, key=lambda t: t.priority)
```

### TodoWrite with Dependencies

```python
todowrite(todos=[
    {
        "id": "1",
        "content": "Set up database schema",
        "status": "completed",
        "priority": "high"
    },
    {
        "id": "2", 
        "content": "Create repository layer (blocked by: 1)",
        "status": "pending",  # NOW READY - blocker complete
        "priority": "high"
    },
    {
        "id": "3",
        "content": "Implement service layer (blocked by: 2)",
        "status": "pending",  # NOT READY - blocker pending
        "priority": "medium"
    }
])
```

---

## 6. memory-compaction - Context Management Protocol (Beads)

**Trigger:** `/memory-compaction`  
**Source:** steveyegge/beads

### When to Compact

```
Compact context when:
  - Completed a major task unit
  - About to start a new phase
  - Context is getting noisy
  - Same information appearing repeatedly

Do NOT compact when:
  - You'll need the raw output soon
  - File you plan to edit
  - Complex debugging in progress
```

### Compaction Workflow

```python
# 1. Identify completed work outputs
prunable = [
    "old file reads you won't need",
    "completed command outputs",
    "superseded search results"
]

# 2. Extract key insights BEFORE discarding
extract(
    ids=["10", "11", "12"],
    distillation=[
        "auth.ts: JWT validation with 5min TTL, bcrypt 12 rounds",
        "user.ts: User interface with id, email, permissions[]",
        "Completed: Database migration for new schema"
    ]
)

# 3. Discard pure noise
discard(ids=["noise", "5", "6", "7"])
```

### Memory Hierarchy

```
┌─────────────────────────────────────────┐
│ ACTIVE CONTEXT (keep in full)           │
│ - Files being edited                     │
│ - Current task requirements              │
│ - Recent tool outputs                    │
├─────────────────────────────────────────┤
│ DISTILLED KNOWLEDGE (extracted)         │
│ - Key patterns discovered                │
│ - Architecture decisions                 │
│ - API signatures                         │
├─────────────────────────────────────────┤
│ DISCARDED (removed)                     │
│ - Old reads superseded by edits          │
│ - Completed task outputs                 │
│ - Failed attempts (lessons learned)      │
└─────────────────────────────────────────┘
```

---

## Quick Reference: Superpowers Commands

| Skill | Trigger | Key Principle |
|-------|---------|---------------|
| TDD Master | `/tdd-master` | No code without failing test |
| Systematic Debugging | `/systematic-debugging` | Root cause before fix |
| Subagent Development | `/subagent-driven-development` | 2-stage review |
| Landing the Plane | `/landing-the-plane` | Never leave uncommitted |
| Ready Work | `/ready-work` | Dependency-aware tasks |
| Memory Compaction | `/memory-compaction` | Extract before discard |

---

## Integration with OpenCode Agents

### How Each Agent Uses These Skills

| Agent | Primary Skills |
|-------|---------------|
| **Sisyphus** | All skills, orchestration, landing-the-plane |
| **test-writer** | tdd-master (mandatory) |
| **qa-engineer** | systematic-debugging, 2-stage review |
| **oracle** | systematic-debugging (phase 1-2 analysis) |
| **explore** | ready-work-detection (find next task) |
| **general** | All skills at basic level |

### Skill Activation Flow

```
User Request
    │
    ├── Is this a BUG FIX?
    │   └── Activate: /systematic-debugging
    │
    ├── Is this a NEW FEATURE?
    │   └── Activate: /tdd-master → /subagent-driven-development
    │
    ├── Is user ending session?
    │   └── Activate: /landing-the-plane
    │
    ├── Are there multiple tasks?
    │   └── Activate: /ready-work (find unblocked tasks)
    │
    └── Is context getting large?
        └── Activate: /memory-compaction
```

---

*Enhanced with patterns from obra/superpowers and steveyegge/beads*
