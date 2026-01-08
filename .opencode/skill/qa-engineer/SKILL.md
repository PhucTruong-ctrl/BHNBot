---
name: qa-engineer
description: Unit Testing, TDD, and Mocking
license: MIT
compatibility: opencode
metadata:
  framework: pytest
---

## 🧪 Quality Assurance Protocol

"It works" is not enough. Prove it with tests.

### 1. Testing Framework: Pytest
- Use `pytest` for all test suites.
- Use `conftest.py` for shared fixtures (e.g., spinning up a temporary event loop).

### 2. Mocking & Dependency Injection
- **Problem:** You cannot connect to real Discord API or real Bank API during tests.
- **Solution:** Use `unittest.mock` or `pytest-mock` to fake external calls.
- **Rule:** If a function makes a network call, it MUST be mocked in unit tests.

### 3. Coverage Standards
- Aim for high coverage on **Core Logic** (Economy calculations, RNG logic).
- UI/View code is harder to test, but Logic layers must be bulletproof.

### 4. Test Driven Development (TDD) Mindset
- When fixing a bug:
  1. Write a test that reproduces the bug (Fail).
  2. Fix the code.
  3. Run the test (Pass).
  4. Commit both.