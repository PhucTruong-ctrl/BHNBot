from dataclasses import dataclass
from datetime import datetime
import json
from typing import Optional, Dict

@dataclass
class Giveaway:
    message_id: int
    channel_id: int
    guild_id: int
    host_id: int
    prize: str
    winners_count: int
    end_time: datetime
    requirements: Dict
    status: str = 'active'

    @classmethod
    def from_db(cls, row):
        return cls(
            message_id=row[0],
            channel_id=row[1],
            guild_id=row[2],
            host_id=row[3],
            prize=row[4],
            winners_count=row[5],
            end_time=row[6], # Expected to be handled as datetime by aiosqlite or converted
            requirements=json.loads(row[7]) if row[7] else {},
            status=row[8]
        )
