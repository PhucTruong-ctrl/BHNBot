---
name: discord-arch
description: Enforce Scalable 4-Layer Architecture for Discord Bots
license: MIT
compatibility: opencode
metadata:
  role: architect
  framework: discord.py
---

## 🏛️ The 4-Layer Architecture Standard

When designing or refactoring a Discord Bot feature, you MUST strictly separate concerns into these 4 layers. DO NOT mix them.

### 1. Layer 1: Controller (The Cog)
- **Location:** `cogs/<feature>/cog.py`
- **Responsibility:**
  - Receive Commands/Events from Discord.
  - Parse arguments.
  - Call **Service Layer**.
  - Send responses (using **UI Layer**).
  - **FORBIDDEN:** Direct database access, complex math, heavy logic.

### 2. Layer 2: Service (The Orchestrator)
- **Location:** `cogs/<feature>/services/`
- **Responsibility:**
  - Combine Business Logic (Core) with Data Access.
  - Handle Transactions (ACID).
  - Error handling logic.
- **Example:** `EconomyService.transfer_money(sender, receiver, amount)`

### 3. Layer 3: Core (Business Logic)
- **Location:** `cogs/<feature>/core/`
- **Responsibility:**
  - Pure Python logic. NO `discord` imports.
  - Unit testable.
- **Example:** `calculate_tax(amount)`, `check_level_up(xp)`

### 4. Layer 4: UI (Presentation)
- **Location:** `cogs/<feature>/ui/`
- **Responsibility:**
  - Format Embeds.
  - Define Views (Buttons, Dropdowns).
  - **FORBIDDEN:** Executing logic inside buttons (Buttons must callback to Controller/Service).

## 🛠️ Usage Instruction
Before writing code for a new feature, output the file structure based on this architecture.