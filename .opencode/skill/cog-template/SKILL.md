---
name: cog-template
description: Generate a boilerplate structure for a new Discord Cog
license: MIT
compatibility: opencode
metadata:
  type: generator
---

## 🏗️ New Cog Boilerplate

When asked to create a new feature (e.g., "Make a music bot"), generate this structure immediately.

### Directory: `cogs/<name>/`

#### `__init__.py`
```python
from discord.ext import commands
from .cog import MyCog

async def setup(bot: commands.Bot):
    await bot.add_cog(MyCog(bot))