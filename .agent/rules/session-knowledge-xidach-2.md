# 🧠 AGENT HANDOVER: XI DACH MODULE

**ROLE:** Senior Python Backend Engineer (Discord Bot)
**CONTEXT:** "Xi Dach" (Blackjack) - Multiplayer Card Game

---

## 1. 📜 CORE CODING STANDARDS (NON-NEGOTIABLE)

*   **Async Discipline**:
    *   **NO** `time.sleep()`.
    *   **NO** blocking IO (Requests, File Read/Write, Image Processing).
    *   **Use** `loop.run_in_executor()` for `Pillow` operations.
*   **Database (ACID)**:
    *   Currency/Inventory changes **MUST** use `async with db.batch_modify()`.
    *   **NEVER** modify balance in memory without DB commit.
*   **State Management**:
    *   **Tables**: Stored in `GameManager` (Singleton).
    *   **Players**: Transient in RAM (linked to Table), persisted in DB (Currency).
    *   **UI**: Ephemeral Views. Do NOT rely on View persistence across restarts.

---

## 2. 🚫 CRITICAL BUG HISTORY (AVOID REPEATING)

### A. "Interaction Failed" / "Unknown Interaction"
*   **Cause**: Lobby Timeout (30s) < Default View Timeout (180s). Users clicked stale buttons.
*   **Fix**:
    1.  **Increased View Timeout** to 300s.
    2.  **Robust Lock Check** in callbacks.
    3.  **Auto-Delete Logic**: When lobby closes, iterate all players and call `player.interaction.delete_original_response()`.

### B. "Ghost" Quote Replies ("Chào mừng...")
*   **Symptom**: Error messages quoted the "Welcome" text, confusing users.
*   **Fix**: **Delete-on-Timeout**. Instead of replying to the stale message, **DELETE IT** (`message.delete()`) then send a fresh ephemeral error (`response.send_message()`).

### C. Dealer AI Suicide
*   **Symptom**: Dealer hit on 18/19 just to beat a player, ignored "Ngũ Linh" (5 cards <= 21) potential.
*   **Fix**: **Hard Stop Rule**. If Dealer has 5 cards and Score <= 21, **ALWAYS STAND** regardless of score comparison.

### D. Reentrant Deadlock
*   **Symptom**: Bot hangs forever during turn processing.
*   **Cause**: Acquiring `table.lock` inside a function already holding `table.lock`.
*   **Fix**: Use one outer lock in `turn_logic`. Inner functions assume lock is held.

---

## 3. 🛡️ ROBUSTNESS CHECKLIST (FOR FUTURE FEATURES)

1.  **Liveness Check**: Always verify `game_manager.get_table(channel_id)` exists before processing buttons. Views can outlive Tables!
2.  **Atomic UI Updates**: Use `interaction.response.edit_message()` for state changes. Avoid `send_message` spam.
3.  **Cleanup**: If you create a Message/View that is game-bound, you **MUST** track it and delete it on Game End/Cancel.
4.  **Error Handling**: Wrap ALL button callbacks in `try...except`. Log errors with `logger.error(..., exc_info=True)`.

---

## 4. 🎨 STYLE GUIDE

*   **Language**: Internal = **English** (Technical), External = **Vietnamese** (Casual/Fun).
*   **Docstrings**: **Google Style** Required.
*   **Type Hits**: Required for all args/returns.

---
*Created: 2025-12-25 | Last Updated By: Antigravity*
