---
name: reverse-engineer
description: Analyze legacy code, unknown libraries, and competitive logic
license: MIT
compatibility: opencode
metadata:
  mode: deep_dive
---

## 🔬 Reverse Engineering Protocol

When handed a piece of code, a link, or a vague logic description:

### Phase 1: Static Analysis (The Read)
- **Identify Patterns:** Is this a State Machine? An Event Bus? A Factory pattern?
- **Dependency Graph:** What does this code import? (e.g., If it imports `numpy`, it's doing heavy math).
- **Code Smell:** Detect obfuscated logic or weird variable names (`var a`, `func x`). Rename them mentally to semantic names.

### Phase 2: Logic Reconstruction
- **Flowcharting:** Describe the data flow: `Input -> Parser -> Validator -> Processor -> Database`.
- **Black Box Testing:** If we can't see the code (closed source bot), create a hypothesis: "If I send X, and it returns Y, then it must be doing Z".

### Phase 3: Replication (The "Better" Version)
- Don't just copy. **Improve.**
- If the original code uses a global variable (Bad), refactor it to a Class Attribute (Good).
- If the original code uses blocking IO, rewrite it to Async IO.

### 📜 specific Target: OwO/Poketwo Logic
- **Economy:** Analyze how they prevent inflation (Tax, Cooldowns).
- **RNG:** Analyze their drop rates (Weighted Random). *Replicate this using Python `random.choices` with weights.*