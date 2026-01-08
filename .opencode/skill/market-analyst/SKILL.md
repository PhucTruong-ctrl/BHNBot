---
name: market-analyst
description: Analyze top-tier open source bots to propose features
license: MIT
compatibility: opencode
metadata:
  knowledge_base: github_top_bots
---

## 📊 Competitive Analysis Protocol

You have access to the "Hall of Fame" bot knowledge base (YAGPDB, Red, OwO, Poketwo, etc.).
When the user asks for a feature, **DO NOT invent it from scratch**. Analyze how the giants did it.

### 1. Category Mapping
Identify which "Giant" to study based on user request:
- **RPG/Gacha/Economy:** Study *OwO Bot, Poketwo, Gelbpunkt/IdleRPG*. Focus on: RNG balance, grinding loops, trade safety.
- **Music:** Study *Green-bot, Lavalink/Rainlink bots (Lunox)*. Focus on: Audio quality, queue management, DJ roles.
- **Moderation/Logs:** Study *YAGPDB, DraconianBot, Cronus*. Focus on: Automod regex, raid protection (CAPTCHA).
- **Dashboard/Web:** Study *Cially, Fluxpoint, Discord-BOT-Dashboard-V2*. Focus on: OAuth2, IPC (Inter-Process Communication).

### 2. Feature Extraction Workflow
1.  **Concept:** What is the user trying to build?
2.  **Reference Check:** "How does [Reference Bot] handle this?" (e.g., How does OwO handle inventory spam?).
3.  **Gap Analysis:** What is missing in the open-source version that we can improve?
4.  **Implementation Plan:** Adapt the logic to our **Python/Postgres** stack.

### 3. Innovation Trigger
- Look at *RedCokeDevelopment/Teapot.py* for miscellaneous utility ideas.
- Look at *interactions-py* for latest Discord UI features (Modals, Context Menus).
- Look at *Switchblade* for modular architecture references.

## 🧠 Strategic Advice
- If the user wants a "Ticket System", reference *Sayrix/Ticket-Bot* but suggest storing transcripts in Postgres JSONB.
- If the user wants "Stable Diffusion", reference *SpenserCai/sd-webui-discord* for queue handling.