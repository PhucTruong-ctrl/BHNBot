#!/usr/bin/env python3
"""
CLI Tool for generating seasonal event configurations.

Usage:
    python tools/generate_event.py halloween 2026
    python tools/generate_event.py --all 2026
    python tools/generate_event.py --preview spring 2026
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cogs.seasonal.services.rotation_service import rotation_service


ALL_EVENTS = [
    "halloween",
    "spring", 
    "summer",
    "autumn",
    "winter",
    "mid_autumn",
    "earth_day",
    "birthday",
]


async def generate_event_config(event_type: str, year: int, preview: bool = False) -> dict:
    """Generate event configuration using rotation service."""
    content = await rotation_service.export_event_config(event_type, year)
    
    if preview:
        print(f"\n{'='*60}")
        print(f"PREVIEW: {event_type} {year}")
        print(f"{'='*60}")
        print(f"Fish count: {len(content['fish'])}")
        for fish in content["fish"]:
            exclusive = " [EXCLUSIVE]" if fish.get("is_yearly_exclusive") else ""
            print(f"  - {fish['name']} ({fish['tier']}){exclusive}")
        print(f"\nCosmetics:")
        print(f"  Frame: {content['cosmetics'].get('frame', {}).get('name', 'N/A')}")
        print(f"  Background: {content['cosmetics'].get('background', {}).get('name', 'N/A')}")
        print(f"  Title: {content['cosmetics'].get('title', {}).get('name', 'N/A')}")
        print(f"\nShop items: {len(content['shop'])}")
        print(f"Seed: {content['_meta']['seed']}")
    
    return content


async def update_event_json(event_type: str, year: int, content: dict) -> None:
    """Update the event's JSON file with rotated content."""
    event_file = Path(f"data/events/{event_type}.json")
    
    if not event_file.exists():
        print(f"WARNING: {event_file} does not exist. Creating new file.")
        existing = {}
    else:
        with open(event_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
    
    existing["fish"] = content["fish"]
    existing["shop"] = content["shop"]
    if "cosmetics" not in existing:
        existing["cosmetics"] = {}
    existing["cosmetics"].update(content["cosmetics"])
    existing["_rotation_meta"] = content["_meta"]
    
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    print(f"Updated: {event_file}")


async def main():
    parser = argparse.ArgumentParser(description="Generate seasonal event configurations")
    parser.add_argument("event", nargs="?", help="Event type (e.g., halloween, spring)")
    parser.add_argument("year", type=int, help="Year to generate for")
    parser.add_argument("--all", action="store_true", help="Generate for all events")
    parser.add_argument("--preview", action="store_true", help="Preview only, don't write files")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if exists")
    
    args = parser.parse_args()
    
    if args.all:
        events = ALL_EVENTS
    elif args.event:
        if args.event not in ALL_EVENTS:
            print(f"ERROR: Unknown event '{args.event}'. Valid: {ALL_EVENTS}")
            sys.exit(1)
        events = [args.event]
    else:
        print("ERROR: Specify an event or use --all")
        sys.exit(1)
    
    print(f"Generating event configs for year {args.year}...")
    print(f"Events: {', '.join(events)}")
    print()
    
    for event_type in events:
        try:
            content = await generate_event_config(event_type, args.year, args.preview)
            
            if not args.preview:
                await update_event_json(event_type, args.year, content)
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            continue
        except Exception as e:
            print(f"ERROR generating {event_type}: {e}")
            continue
    
    if not args.preview:
        print(f"\nDone! Generated configs for {len(events)} events.")
        print("Remember to commit the changes to data/events/*.json")


if __name__ == "__main__":
    asyncio.run(main())
