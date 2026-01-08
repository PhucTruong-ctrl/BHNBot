---
name: debug-protocol
description: Systematic approach to analyzing and fixing bugs
license: MIT
compatibility: opencode
metadata:
  task: debugging
---

## 🕵️‍♂️ Deep Debug Protocol

When the user reports an error or provides a traceback, DO NOT guess. Follow this procedure:

### Step 1: Traceback Autopsy
1. Locate the **Exact File and Line Number** where the error originated.
2. Identify the **Exception Type** (e.g., `AttributeError`, `RuntimeError`).
3. Determine if the error is User Logic or Library Constraint (discord.py limitations).

### Step 2: Reverse Engineering
- If code is provided, simulate the execution flow in your "mind".
- Identify **Race Conditions** (Async tasks running out of order).
- Check for **NoneType** propagation (Did a previous function return None?).

### Step 3: Strategic Fix
1. Explain the **Root Cause** to the user clearly.
2. Propose a fix that addresses the root cause, not just the symptom.
3. Check for side effects (Does this fix break other features?).

## 🚫 Anti-Patterns to Avoid
- Do not suggest: "Try updating pip" (unless version is clearly wrong).
- Do not suggest: wrapping everything in `try/except` to hide the error.