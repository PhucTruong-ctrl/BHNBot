#!/usr/bin/env python3
"""
Build words dictionary from dictionary database
Creates a memory-based lookup structure for fast word chain validation
"""
import json
import sqlite3
from collections import defaultdict

DB_PATH = "./data/database.db"
OUTPUT_FILE = "./data/words_dict.json"

def build_words_dict():
    """Build dictionary mapping first syllable -> [possible second syllables]"""
    print("[BUILDING WORDS DICT]")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get all 2-syllable words
    c.execute("SELECT word FROM dictionary")
    rows = c.fetchall()
    conn.close()
    
    words_dict = defaultdict(set)
    words_set = set()
    
    for row in rows:
        word = row[0]
        words_set.add(word)
        
        # Extract first and second syllable
        parts = word.split()
        if len(parts) == 2:
            first, second = parts
            words_dict[first].add(second)
    
    # Convert sets to lists for JSON serialization
    words_dict_json = {
        k: list(v) for k, v in words_dict.items()
    }
    
    # Save to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(words_dict_json, f, ensure_ascii=False, indent=2)
    
    print(f"Built words dict with {len(words_dict_json)} starting syllables")
    print(f"Total words: {len(words_set)}")
    print(f"Saved to: {OUTPUT_FILE}")
    
    return words_dict_json

if __name__ == "__main__":
    build_words_dict()
