# AGENTS.md - BHNBot AI Agent Skills & Protocols

> **Comprehensive guide for AI agents working on BHNBot**
> 
> This document consolidates all skills, instructions, and prompts for the OpenCode AI system.

---

## Table of Contents

1. [Architecture & Design](#1-discord-arch---scalable-4-layer-architecture)
2. [Python Standards](#2-python-godmode---strict-python-standards)
3. [Database](#3-postgres-supreme---postgresql-optimization)
4. [Algorithms & Performance](#4-algo-god---performance--algorithm-protocol)
5. [Debugging](#5-debug-protocol---systematic-bug-analysis)
6. [Testing](#6-qa-engineer---quality-assurance-protocol)
7. [Security](#7-sec-ops---security-operations-protocol)
8. [Git Workflow](#8-git-commander---git-workflow-protocol)
9. [DevOps](#9-devops-master---deployment-protocol)
10. [Web Integration](#10-fullstack-bridge---web--api-integration)
11. [Competitive Analysis](#11-market-analyst---competitive-analysis)
12. [Reverse Engineering](#12-reverse-engineer---code-analysis)
13. [Code Generation](#13-cog-template---boilerplate-generator)

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

#### 2. Asyncio Best Practices
- **NEVER** use blocking calls (e.g., `requests`, `time.sleep`) inside async functions
- Use `aiohttp` for HTTP requests
- Use `asyncio.sleep` for delays
- Use `asyncio.Lock()` when modifying shared state (Global variables, Cache)

#### 3. Error Handling
- **FORBIDDEN:** `try: ... except: pass` (Silent fail)
- Always catch specific errors: `except discord.Forbidden:`
- Log the error with full traceback before notifying the user

#### 4. Data Models
- Use `pydantic.BaseModel` or `@dataclass` for data structures
- Do not pass raw Dicts/Tuples around

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

#### 3. Performance & Concurrency
- **Connection Pooling:** MANDATORY. Use `asyncpg.create_pool`. Never open a new connection for every command
- **Transactions:** Wrap money/inventory transfers in `async with connection.transaction():`
- **Indexes:** Create indexes on columns used in `WHERE` and `JOIN` clauses

#### 4. Migration Plan (SQLite -> Postgres)
1. **Dump Data:** Export SQLite data to standard CSV/JSON
2. **Schema Re-creation:** Define SQLAlchemy models matching the Postgres standards
3. **ETL Script:** Write a Python script to load data, sanitize it (fix booleans, datetimes), and bulk insert into Postgres

---

## 4. algo-god - Performance & Algorithm Protocol

**Trigger:** `/algo-god`  
**Level:** Expert

### Performance & Algorithm Protocol

Scale from 10 users to 1,000,000 users.

#### 1. Big O Awareness
| Pattern | Complexity | Action |
|---------|------------|--------|
| Nested Loops | `O(n^2)` | Avoid whenever possible |
| List membership | `O(n)` | Use **Sets** instead `O(1)` |
| Dict lookups | `O(1)` | Preferred for key-based access |

#### 2. Caching Strategy (Redis)
- **Read-Heavy Data:** Cache User Profiles/Guild Configs in Redis. Only write to Postgres on change or periodically (Write-Back)
- **TTL (Time To Live):** Don't cache forever. Set expiry

#### 3. Lazy Loading
- Don't fetch the entire User Inventory on startup. Fetch on demand
- Use Generators (`yield`) for processing large datasets to save RAM

#### 4. Profiling
- If the bot is slow, don't guess. Use `cProfile` or `py-spy` to find the bottleneck

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

#### Step 2: Reverse Engineering
- If code is provided, simulate the execution flow in your "mind"
- Identify **Race Conditions** (Async tasks running out of order)
- Check for **NoneType** propagation (Did a previous function return None?)

#### Step 3: Strategic Fix
1. Explain the **Root Cause** to the user clearly
2. Propose a fix that addresses the root cause, not just the symptom
3. Check for side effects (Does this fix break other features?)

### Anti-Patterns to Avoid
- Do not suggest: "Try updating pip" (unless version is clearly wrong)
- Do not suggest: wrapping everything in `try/except` to hide the error

---

## 6. qa-engineer - Quality Assurance Protocol

**Trigger:** `/qa-engineer`  
**Framework:** pytest

### Quality Assurance Protocol

"It works" is not enough. Prove it with tests.

#### 1. Testing Framework: Pytest
- Use `pytest` for all test suites
- Use `conftest.py` for shared fixtures (e.g., spinning up a temporary event loop)

#### 2. Mocking & Dependency Injection
- **Problem:** You cannot connect to real Discord API or real Bank API during tests
- **Solution:** Use `unittest.mock` or `pytest-mock` to fake external calls
- **Rule:** If a function makes a network call, it MUST be mocked in unit tests

#### 3. Coverage Standards
- Aim for high coverage on **Core Logic** (Economy calculations, RNG logic)
- UI/View code is harder to test, but Logic layers must be bulletproof

#### 4. Test Driven Development (TDD) Mindset
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

#### 2. Rate Limiting (Anti-Spam)
- Use `commands.Cooldown` mapping to `BucketType.user`
- For heavy commands (Image generation), implement a custom Redis-based lock/cooldown

#### 3. Secret Management
- **Scan:** Ensure no API Keys/Tokens are ever committed to Git
- **Rotation:** Design the system so tokens can be rotated without code changes

#### 4. Privilege Principle
- Bot should request minimal Discord Intents
- Database user should not be `postgres` (root). Create a specific user for the bot

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

#### 2. Commit Standards (Conventional Commits)
Refuse to generate commit messages that don't follow this format:
```
feat: add postgres connection pool
fix: resolve race condition in xp loop
refactor: move ui logic to view layer
chore: update requirements.txt
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
  - *Builder Stage:* Install compilers, build-essentials
  - *Runner Stage:* `python:slim` or `alpine` (if compatible), copy only virtualenv/artifacts
- **No Root:** Create a non-root user in the Dockerfile for security
- **Caching:** Copy `requirements.txt` and run `pip install` *before* copying source code to leverage Docker Layer Caching

#### 2. Docker Compose Strategy
- Define services clearly: `bot`, `postgres`, `redis`, `dashboard`
- Use **Volumes** for persistent data (Database, Logs)
- Use **Healthchecks** to ensure the Bot waits for the Database to be ready

#### 3. CI/CD (GitHub Actions)
| Stage | Requirement |
|-------|-------------|
| Linting | Pipeline must fail if `flake8` or `black` finds errors |
| Testing | Pipeline must run `pytest` |
| Deployment | If `main` branch is pushed, trigger Docker build and restart logic |

#### 4. Environment Management
- NEVER hardcode secrets. Use `.env` file and `os.getenv`
- In Docker, map env-file: `env_file: .env`

---

## 10. fullstack-bridge - Web & API Integration

**Trigger:** `/fullstack-bridge`  
**Framework:** FastAPI, React

### Web & API Integration Protocol

The Bot is not an island. It connects to the Web Dashboard.

#### 1. API Framework: FastAPI
- Don't build a web server inside `discord.py`. Run `FastAPI` as a separate service or separate thread/loop (advanced)
- Expose endpoints like `/api/user/{id}/inventory`

#### 2. IPC (Inter-Process Communication)
How does the Dashboard tell the Bot to kick a user?

| Option | Description |
|--------|-------------|
| **Option A (Simple)** | Shared Database. Dashboard writes to DB, Bot polls DB |
| **Option B (Realtime)** | Redis Pub/Sub. Dashboard publishes "KICK_EVENT", Bot subscribes and acts |
| **Option C** | Webhooks |

#### 3. JSON Standards
- API responses must be consistent JSON
- Use `pydantic` models to share schemas between Bot and Web

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

**`services/`** - Business logic orchestration

**`core/`** - Pure Python logic (no discord imports)

**`ui/`** - Embeds, Views, Buttons

---

## Quick Reference: Skill Invocation

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

---

## Agent Types (OpenCode System)

| Agent | Role | Cost | Use Case |
|-------|------|------|----------|
| `explore` | The Scout | FREE | Codebase exploration, pattern discovery |
| `librarian` | The Researcher | CHEAP | External docs, library usage, OSS examples |
| `frontend-ui-ux-engineer` | The UI Specialist | CHEAP | React, Tailwind, visual components |
| `document-writer` | The Scribe | CHEAP | Documentation, READMEs, changelogs |
| `oracle` | The Deep Reasoner | EXPENSIVE | Architecture, complex debugging, algorithms |

### Agent Usage Guidelines

**Parallel Execution (Default):**
```python
# Fire multiple agents in background
background_task(agent="explore", prompt="Find auth implementations...")
background_task(agent="librarian", prompt="Find JWT best practices...")
# Continue working, collect results later with background_output
```

**Oracle Consultation (Expensive - Use Wisely):**
- Complex architecture design
- After 2+ failed fix attempts
- Security/performance concerns
- Multi-system tradeoffs

---

*Generated for BHNBot - Discord Bot with Music & Economy Features*
