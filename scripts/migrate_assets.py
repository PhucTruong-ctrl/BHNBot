#!/usr/bin/env python3
"""
Asset Migration Script for BHNBot Seasonal Events.

Renames existing seasonal assets to include year suffix for rotation system.
"""

import shutil
from pathlib import Path

ASSETS_BASE = Path("assets")

SEASONAL_EVENTS = [
    "autumn",
    "birthday", 
    "earthday",
    "halloween",
    "midautumn",
    "spring",
    "summer",
    "winter",
]

STATIC_BACKGROUNDS = ["cabin", "forest", "ocean", "starry", "sunrise"]


def migrate_frames(year: int, dry_run: bool = True) -> list[tuple[Path, Path]]:
    """Rename frame assets to include year suffix."""
    frames_dir = ASSETS_BASE / "frames"
    migrations = []
    
    for event in SEASONAL_EVENTS:
        old_path = frames_dir / f"frame_{event}.png"
        new_path = frames_dir / f"frame_{event}_{year}.png"
        
        if old_path.exists() and not new_path.exists():
            migrations.append((old_path, new_path))
            if not dry_run:
                shutil.copy2(old_path, new_path)
                print(f"  Copied: {old_path.name} -> {new_path.name}")
        elif new_path.exists():
            print(f"  Skip (exists): {new_path.name}")
    
    return migrations


def migrate_backgrounds(year: int, dry_run: bool = True) -> list[tuple[Path, Path]]:
    """Rename background assets to include year suffix."""
    profile_dir = ASSETS_BASE / "profile"
    migrations = []
    
    for event in SEASONAL_EVENTS:
        old_name = f"bg_{event}.png"
        if event == "midautumn":
            old_name = "bg_midatumn.png"
        
        old_path = profile_dir / old_name
        new_path = profile_dir / f"bg_{event}_{year}.png"
        
        if old_path.exists() and not new_path.exists():
            migrations.append((old_path, new_path))
            if not dry_run:
                shutil.copy2(old_path, new_path)
                print(f"  Copied: {old_path.name} -> {new_path.name}")
        elif new_path.exists():
            print(f"  Skip (exists): {new_path.name}")
    
    return migrations


def fix_typo(dry_run: bool = True) -> bool:
    """Fix bg_midatumn.png -> bg_midautumn.png typo."""
    profile_dir = ASSETS_BASE / "profile"
    old_path = profile_dir / "bg_midatumn.png"
    new_path = profile_dir / "bg_midautumn.png"
    
    if old_path.exists() and not new_path.exists():
        if not dry_run:
            shutil.copy2(old_path, new_path)
            print(f"  Fixed typo: {old_path.name} -> {new_path.name}")
        return True
    return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate seasonal assets to year-based naming")
    parser.add_argument("year", type=int, help="Year to assign to existing assets (e.g., 2025)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--fix-typo", action="store_true", help="Also fix bg_midatumn typo")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN - No changes will be made\n")
    
    print(f"Migrating assets to year {args.year}...\n")
    
    print("Frames:")
    frame_migrations = migrate_frames(args.year, args.dry_run)
    if args.dry_run:
        for old, new in frame_migrations:
            print(f"  Would copy: {old.name} -> {new.name}")
    
    print("\nBackgrounds:")
    bg_migrations = migrate_backgrounds(args.year, args.dry_run)
    if args.dry_run:
        for old, new in bg_migrations:
            print(f"  Would copy: {old.name} -> {new.name}")
    
    if args.fix_typo:
        print("\nTypo fix:")
        if fix_typo(args.dry_run):
            if args.dry_run:
                print("  Would fix: bg_midatumn.png -> bg_midautumn.png")
        else:
            print("  Typo already fixed or file not found")
    
    total = len(frame_migrations) + len(bg_migrations)
    if args.dry_run:
        print(f"\nTotal: {total} files would be copied")
        print("\nRun without --dry-run to apply changes")
    else:
        print(f"\nDone! Copied {total} files.")
        print("\nNote: Original files are preserved. Delete them manually if needed.")


if __name__ == "__main__":
    main()
