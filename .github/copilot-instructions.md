# BHNBot - AI Coding Guidelines

## STYLE AND ARCHITECTURE GUIDELINES
GOAL: đánh giá, suy luận, thử phản ứng AI dựa trên kiến trúc và phong cách mã hiện có của BHNBot, không cần quá clean code.
CONSTRAINTS: trả lời ngắn, không hỏi lại, không phản biện.
TOPICS: AI tự do, ràng buộc, token, kiến trúc, mẫu thiết kế, quy ước mã hóa, quy trình phát triển, cơ sở dữ liệu, kiểm thử, cạm bẫy phổ biến, discord, async, quản lý lỗi, bản địa hóa tiếng Việt.
TONE_USER: ít kinh nghiệm, cần hướng dẫn rõ ràng.
TONE_AI: chuyên nghiệp, súc tích, rõ ràng, hữu ích, như 1 thầy giáo.
EXPECTATION: suy luận sâu, trả lời chi tiết, có ví dụ minh họa, phân tích rõ ràng.

## Architecture Overview
BHNBot is a Discord.py bot using a modular cog architecture. Core components:
- **main.py**: Bot initialization and cog loading
- **cogs/**: Feature modules (fishing, economy, admin, etc.)
- **core/**: Shared services (database, achievements)
- **data/**: JSON configuration files
- **database_manager.py**: Centralized database operations

## Key Patterns

### Database Operations
Use `database_manager.py` for all DB interactions. Never access SQLite directly.
```python
from database_manager import get_inventory, add_seeds, get_user_balance
inventory = await get_inventory(user_id)
```

### Cog Structure
Each cog follows this pattern:
- `cog.py`: Main slash commands and logic
- `constants.py`: Event data, item definitions, paths
- `helpers.py`: Utility functions
- `views.py`: Discord UI components
- `models.py`: Data structures (if needed)

### Async Everywhere
All Discord interactions are async. Use `await` for database calls and Discord API.
```python
@commands.command()
async def example(self, ctx):
    balance = await get_user_balance(ctx.author.id)
    await ctx.send(f"Balance: {balance}")
```

### Error Handling
Wrap operations in try/except with logging. Use `print()` for debug logs.
```python
try:
    result = await some_operation()
except Exception as e:
    print(f"[ERROR] Operation failed: {e}")
    await ctx.send("An error occurred")
```

### Vietnamese Localization
UI strings and comments are in Vietnamese. Maintain this convention.

## Development Workflow

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 setup_data.py

# Run bot
python3 main.py
```

### Database Schema
Tables are defined in `setup_data.py`. Use NEW MODULAR SCHEMA with user_stats for flexible key-value stats.

### Testing
Run bot locally with test token. Check console logs for errors. No formal test suite exists.

### Key Files to Reference
- `cogs/fishing/cog.py`: Complex event system example
- `database_manager.py`: DB operation patterns
- `core/database.py`: Connection management
- `configs/settings.py`: Configuration paths

## Common Pitfalls
- Don't modify database schema without updating setup_data.py
- Always check user permissions before admin operations
- Use absolute paths for file operations
- Handle cooldowns and rate limits properly</content>
<parameter name="filePath">/home/phuctruong/BHNBot/.github/copilot-instructions.md