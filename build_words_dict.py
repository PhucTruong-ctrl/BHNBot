#!/usr/bin/env python3
"""
Build words dictionary from JSONL dictionary file.
Creates a memory-based lookup structure for fast word chain validation.

Format: JSONL file where each line is {"text": "word", "source": [...]}
Output: JSON with mapping first_syllable -> [second_syllables]
"""
import json
from collections import defaultdict
from pathlib import Path

DICT_FILE = "./data/tu_dien.txt"
OUTPUT_FILE = "./data/words_dict.json"


def load_words_from_jsonl(file_path: str) -> set:
    """Load all words from JSONL dictionary file.
    
    Each line format: {"text": "word", "source": ["source1", "source2"]}
    """
    words = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    word = entry.get("text", "").strip()
                    if word:
                        words.add(word)
                except json.JSONDecodeError as e:
                    print(f"[WARNING] Line {line_num}: Invalid JSON - {e}")
                    continue
    except FileNotFoundError:
        print(f"[ERROR] Dictionary file not found: {file_path}")
        return set()
    
    return words


def build_words_dict_from_jsonl(input_file: str, output_file: str) -> dict:
    """Build dictionary mapping first syllable -> [second syllables].
    
    Only processes 2-syllable words (words with one space).
    """
    print("[BUILDING WORDS DICT FROM JSONL]")
    
    # Load all words
    words = load_words_from_jsonl(input_file)
    
    if not words:
        print("[ERROR] No words loaded from dictionary file")
        return {}
    
    print(f"[OK] Loaded {len(words)} total words")
    
    # Build mapping: first_syllable -> [second_syllables]
    words_dict = defaultdict(set)
    two_syllable_count = 0
    
    for word in words:
        # Split by space to get syllables
        parts = word.split()
        
        # Only process 2-syllable words
        if len(parts) == 2:
            first, second = parts
            words_dict[first].add(second)
            two_syllable_count += 1
    
    # Convert sets to sorted lists for better JSON and consistency
    words_dict_json = {
        k: sorted(list(v)) for k, v in words_dict.items()
    }
    
    # Save to file
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(words_dict_json, f, ensure_ascii=False, indent=2)
        print(f"[OK] Saved to: {output_file}")
    except IOError as e:
        print(f"[ERROR] Error writing output file: {e}")
        return {}
    
    # Print statistics
    print(f"\n[STATS] Dictionary Statistics:")
    print(f"  * Total words: {len(words)}")
    print(f"  * 2-syllable words: {two_syllable_count}")
    print(f"  * Starting syllables: {len(words_dict_json)}")
    
    return words_dict_json


if __name__ == "__main__":
    build_words_dict_from_jsonl(DICT_FILE, OUTPUT_FILE)
