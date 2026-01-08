---
name: algo-god
description: Algorithms, Data Structures, and Performance Optimization
license: MIT
compatibility: opencode
metadata:
  level: expert
---

## ⚡ Performance & Algorithm Protocol

Scale from 10 users to 1,000,000 users.

### 1. Big O Awareness
- Avoid Nested Loops (`O(n^2)`) whenever possible.
- Use **Sets** (`O(1)`) for membership checks (`if user in user_list`) instead of Lists (`O(n)`).
- Use **Dictionaries** (HashMaps) for lookups.

### 2. Caching Strategy (Redis)
- **Read-Heavy Data:** Cache User Profiles/Guild Configs in Redis. only write to Postgres on change or periodically (Write-Back).
- **TTL (Time To Live):** Don't cache forever. Set expiry.

### 3. Lazy Loading
- Don't fetch the entire User Inventory on startup. Fetch on demand.
- Use Generators (`yield`) for processing large datasets to save RAM.

### 4. Profiling
- If the bot is slow, don't guess. Use `cProfile` or `py-spy` to find the bottleneck.