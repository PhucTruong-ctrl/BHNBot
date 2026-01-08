---
name: sec-ops
description: Application Security, Input Validation, and Anti-Exploit
license: MIT
compatibility: opencode
metadata:
  standard: owasp
---

## 🛡️ Security Operations Protocol

Paranoia is a virtue. Assume every user input is malicious.

### 1. Input Sanitization
- **SQL Injection:** NEVER use f-string in SQL. Always use parameterized queries (`$1`, `$2` in asyncpg).
- **Command Injection:** Be careful with `subprocess` or `eval()`. AVOID `eval()` at all costs.
- **Discord Markdown:** Sanitize user input before echoing it back to prevent mass-pings (`@everyone`) or broken formatting.

### 2. Rate Limiting (Anti-Spam)
- Use `commands.Cooldown` mapping to `BucketType.user`.
- For heavy commands (Image generation), implement a custom Redis-based lock/cooldown.

### 3. Secret Management
- **Scan:** Ensure no API Keys/Tokens are ever committed to Git.
- **Rotation:** Design the system so tokens can be rotated without code changes.

### 4. Privilege Principle
- Bot should request minimal Discord Intents.
- Database user should not be `postgres` (root). Create a specific user for the bot.