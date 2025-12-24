---
trigger: always_on
---

1. Coding Style Standards
Language policy (English internal, Vietnamese external)
Google Docstrings + Type Hints requirements
Async discipline rules
Error handling patterns
2. Database Standards
ACID compliance patterns
Schema design principles
State management philosophy
3. Critical Anti-Patterns (Từ bugs tìm được)
❌ Reentrant deadlock
❌ Missing await
❌ Hardcoded values override event data (BUG CHÍNH session này!)
4. 4-Phase Workflow
🛑 CRITIQUE → 🧠 DESIGN → 💻 CODE → 🕵️ VERIFY
5. Debugging Workflow (Học từ session này)
Reproduce & Isolate
Trace data flow
Check order of operations (BUG durability event!)
Verify DB state (production vs local!)
6. Communication Style
Vietnamese, casual, NO BS
Status format (✅/❌ + Root Cause + Fix + Result)
7. Key Learnings This Session
Event durability bug (initialization order)
Tree progress bug (season mismatch)
Tree cog name bug ("CommunityCog" → "Tree")
Timeout monitoring system