# 📚 Xi Dach (Blackjack) - Technical Documentation

## 🏗️ Architecture Overview

The Xi Dach module follows a **Service-Oriented Architecture (SOA)** with strict **Separation of Concerns**, resembling an MVC (Model-View-Controller) pattern adapted for Discord bots.

*   **Model (`models.py`, `game.py`):** Holds state (Players, Table, Deck) and pure game logic (Card calculation, Win conditions).
*   **View (`views.py`, `card_renderer.py`):** Handles UI (Discord Buttons, Embeds) and Visual Assets (Image drawing).
*   **Controller (`cog.py`):** Manages game flow, Discord events, interaction handling, and orchestrates calls between Model and View.

### 📁 Directory Structure
`cogs/xi_dach/`
*   `cog.py`: **The Brain**. Main entry point, loops, event handling.
*   `models.py`: **Datahub**. Classes for `Player`, `Table` (GameState), `GameManager` (Singleton).
*   `views.py`: **Interactive UI**. Discord UI Views (`LobbyView`, `MultiBetView`, `GameView`).
*   `game.py`: **Pure Logic**. Deck generation, card values, hand comparison algorithms.
*   `card_renderer.py`: **Visuals**. Uses `Pillow` to draw cards, names, and avatars onto a canvas.

---

## 🛠️ Detailed Component Analysis

### 1. `cog.py` (Controller)
*   **Role**: Coordinates the entire game lifecycle.
*   **Key Loops**:
    *   `_start_multiplayer`: Manages the 30s Lobby Countdown. Handles **Auto-Ready** and **Auto-Delete** of betting UIs.
    *   `_start_multi_game`: The main game loop. Deals cards -> Player Turns -> Dealer Turn -> Results.
*   **Critical Features**:
    *   **Auto-Delete UI**: Tracks `discord.Interaction` objects in `Player` model and triggers `delete_original_response()` when the lobby closes.
    *   **ACID Transactions**: Uses `self.db_manager.batch_modify()` for ATOMIC currency deduction/refunds.
    *   **Concurrency**: Uses `asyncio.Lock` per Table to prevent race conditions during turns.

### 2. `models.py` (Data Model)
*   **Role**: Defines the shapes of data.
*   **Classes**:
    *   `Player`: Stores `hand`, `bet`, `status`, and **CRITICALLY** `interaction` (for UI cleanup).
    *   `Table`: Stores `deck`, `players`, `turn_index`, and `locks`.
    *   `GameManager`: Singleton that maps `Channel ID` -> `Table`. Ensures one game per channel.
*   **Key Logic**:
    *   `get_dealer_decision`: **Smart AI** logic. Decides Hit/Stand based on "Desperation" (losing to big players) and "Safety" (Ngũ Linh rules).

### 3. `views.py` (Interaction Layer)
*   **Role**: Defines buttons (Hit, Stand, Double, Split not impl yet).
*   **Key Pattern**: **Stateless & Direct**.
    *   **No Defer (Mostly)**: Uses `interaction.response.edit_message` for immediate "In-Place" UI updates.
    *   **Timeout Handling**: Increases timeout to **300s** to prevent "Interaction Failed" errors.
*   **Classes**:
    *   `MultiBetView`: Handles betting logic. Buttons disappear on clicking "Ready".
    *   `GameView`: The main game controls (Rut/Dan). Updates continuously based on turn.

### 4. `game.py` (Core Logic)
*   **Role**: Mathematical backend.
*   **Key Functions**:
    *   `calculate_hand_value`: Handles Ace logic (1/10/11).
    *   `determine_hand_type`: Identifies XI_BAN (AA), XI_DACH (A+10), NGU_LINH (5 cards <= 21).
    *   `compare_hands`: The ultimate judge. Priority: **Xi Ban > Xi Dach > Ngu Linh > Score**.

### 5. `card_renderer.py` (Visual Engine)
*   **Role**: Generates dynamic game images.
*   **Constraint**: **CPU Bound**. Must be run in `loop.run_in_executor` to avoid blocking the bot heartbeats.
*   **Assets**: Loads card images from `assets/cards/`.

---

## ⚙️ Key Workflows & Exception Handling

### A. The "Joint & Bet" Flow
1.  **User**: `/xidach` -> Triggers `_start_multiplayer`.
2.  **System**: Creates `Table`, sends `LobbyView` (Global).
3.  **User**: "Tham Gia" -> Triggers `join_game`.
    *   **Action**: Creates `Player`, sends `MultiBetView` (Ephemeral).
    *   **Storage**: Saves `interaction` to `Player.interaction`.
4.  **User**: Bets & Ready.
5.  **Event**: **Lobby Timer Ends**.
    *   **Action**: Loop through all `players`.
    *   **Cleanup**: Call `player.interaction.delete_original_response()`. **(Eliminates Stale UI)**.

### B. The "Dealer AI" Logic
*   **Normal**: Hits on < 16, Stands on >= 17.
*   **Smart**:
    *   Checks visible player hands.
    *   If losing to many players (Targeting Mode), might Hit on Soft 17.
    *   **Hard Stop**: If 5 cards (Ngũ Linh possibility), **ALWAYS STAND** to preserve the hand multiplier.

### C. Error Handling Strategy
1.  **Interaction Failed / Timeout**:
    *   **Prevention**: View Timeout set to 300s.
    *   **Mitigation**: `try...except` blocks around `message.delete()` and `edit_message`.
2.  **Race Conditions**:
    *   **Locking**: `async with table.lock:` used for ALL turn-based actions.
    *   **Verification**: Check `table.status` and `current_player` inside the lock before processing.

---

## 📝 Coding Standards (Strict)

1.  **Async Discipline**:
    *   ❌ **NEVER** use `time.sleep()`. Use `asyncio.sleep()`.
    *   ❌ **NEVER** block on Image Ops. Use `await loop.run_in_executor(None, render_func, ...)`.
2.  **Type Safety**:
    *   All functions must have Type Hints (`def foo(a: int) -> str:`).
    *   `Optional` must be explicit.
3.  **Documentation**:
    *   **Google Style** Docstrings for every class/function.
    *   Explain *Args*, *Returns*, and *Raises*.
4.  **Database**:
    *   **Transactions**: All Money/Item changes MUST happen inside `async with db.batch_modify()`.

---

## ⚠️ Known Pitfalls & Future Advice

1.  **Interaction Tokens**: Are valid for 15 minutes. Deferring helps, but deleting stale UIs is safer.
2.  **State Synchronization**: `views.py` holds a *reference* to `table`. If `table` is re-created (Game Manager clears it), the View becomes orphaned. Always check `game_manager.get_table()` for liveness.
3.  **Image Caching**: Loading images from disk every frame is slow. Ensure `AssetManager` caches these.

---
*Generated by Antigravity Agent - 2025*
