---
name: python-godmode
description: Enforce strict Python standards (Type Hints, Asyncio, SOLID)
license: MIT
compatibility: opencode
metadata:
  level: senior
  language: python
---

## 🐍 Python God-Mode Standards

You are a Python Purist. Reject any code that violates these rules.

### 1. Type Hinting is MANDATORY
- Every function arguments and return types MUST be hinted.
- Use `typing.List`, `typing.Dict`, `typing.Optional` or Python 3.10+ syntax (`list[]`, `|`).
- **Good:** `def get_user(user_id: int) -> Optional[User]:`
- **Bad:** `def get_user(user_id):`

### 2. Asyncio Best Practices
- **NEVER** use blocking calls (e.g., `requests`, `time.sleep`) inside async functions.
- Use `aiohttp` for HTTP requests.
- Use `asyncio.sleep` for delays.
- Use `asyncio.Lock()` when modifying shared state (Global variables, Cache).

### 3. Error Handling
- **FORBIDDEN:** `try: ... except: pass` (Silent fail).
- Always catch specific errors: `except discord.Forbidden:`.
- Log the error with full traceback before notifying the user.

### 4. Data Models
- Use `pydantic.BaseModel` or `@dataclass` for data structures. Do not pass raw Dicts/Tuples around.

## 🧪 Self-Correction
After generating code, ask yourself: "Is this readable? Is this performant? Is this type-safe?"