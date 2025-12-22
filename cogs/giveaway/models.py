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
    image_url: Optional[str] = None

    @classmethod
    def from_db(cls, row):
        end_time = row[6]
        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time)
            except ValueError:
                try:
                    # Fallback for other formats like "YYYY-MM-DD HH:MM:SS" or similar
                    # SQLite default timestamp often looks like "2023-01-01 12:00:00"
                    end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # If all else fails, try parsing with timezone if present or just return current time to avoid crash
                    # But better to raise or log. For now, let's try one more common format
                    try:
                        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        # Critical error: cannot parse timestamp
                        import logging
                        logger = logging.getLogger("GiveawayCog")
                        logger.error(f"Failed to parse end_time: {end_time} for giveaway {row[0]}")
                        raise ValueError(f"Cannot parse end_time: {end_time}")

        if end_time.tzinfo is None:
             # Assume UTC if no timezone info
             from datetime import timezone
             end_time = end_time.replace(tzinfo=timezone.utc)

        return cls(
            message_id=row[0],
            channel_id=row[1],
            guild_id=row[2],
            host_id=row[3],
            prize=row[4],
            winners_count=row[5],
            end_time=end_time,
            requirements=json.loads(row[7]) if row[7] else {},
            status=row[8],
            image_url=row[9] if len(row) > 9 else None
        )
