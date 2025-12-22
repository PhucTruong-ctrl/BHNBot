#!/usr/bin/env python3
"""
Test script for giveaway winner selection logic.
Simulates the scenario: 13 participants, 5 winners.
"""
import sys
import random

def test_winner_selection():
    """Test the winner selection logic matching helpers.py"""
    
    # Simulate 13 participants
    participants = [(i+1, ) for i in range(13)]  # [(1,), (2,), (3,), ..., (13,)]
    winners_count = 5
    
    print("=" * 60)
    print("GIVEAWAY WINNER SELECTION TEST")
    print("=" * 60)
    print(f"Participants: {len(participants)}")
    print(f"Winners needed: {winners_count}")
    print()
    
    # Extract user IDs (matching helpers.py logic)
    user_ids = [row[0] for row in participants]
    print(f"User IDs: {user_ids}")
    print()
    
    # Pick Winners (simple random selection)
    winners_ids = []
    if user_ids:
        count = min(len(user_ids), winners_count)
        winners_ids = random.sample(user_ids, count)
    
    print(f"✅ Winners selected: {winners_ids}")
    print(f"✅ Number of winners: {len(winners_ids)}")
    print()
    
    # Verify uniqueness
    assert len(winners_ids) == len(set(winners_ids)), "❌ FAIL: Duplicate winners!"
    print("✅ PASS: All winners are unique")
    
    # Verify count
    assert len(winners_ids) == winners_count, f"❌ FAIL: Expected {winners_count} winners, got {len(winners_ids)}"
    print(f"✅ PASS: Correct number of winners ({winners_count})")
    
    # Verify all winners are from participant pool
    for winner in winners_ids:
        assert winner in user_ids, f"❌ FAIL: Winner {winner} not in participant pool!"
    print("✅ PASS: All winners are valid participants")
    
    print()
    print("=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)

def test_reroll_logic():
    """Test reroll logic matching views.py"""
    print()
    print("=" * 60)
    print("REROLL LOGIC TEST")
    print("=" * 60)
    
    # Initial state
    all_participants = [(i+1, ) for i in range(13)]
    current_winners = [3, 7, 11, 2, 9]  # 5 initial winners
    
    print(f"Total participants: {len(all_participants)}")
    print(f"Current winners: {current_winners}")
    print()
    
    # Reroll for 3 new winners
    reroll_count = 3
    
    # Extract user IDs excluding current winners (matching views.py)
    available_users = [row[0] for row in all_participants if row[0] not in current_winners]
    
    print(f"Available for reroll: {available_users}")
    print(f"Available count: {len(available_users)}")
    print(f"Reroll count requested: {reroll_count}")
    print()
    
    # Pick new winners
    available_count = len(available_users)
    if available_count < reroll_count:
        print(f"⚠️ Only {available_count} users available!")
        reroll_count = available_count
    
    new_winners_ids = random.sample(available_users, reroll_count)
    
    print(f"✅ New winners: {new_winners_ids}")
    print()
    
    # Verify no overlap with current winners
    for winner in new_winners_ids:
        assert winner not in current_winners, f"❌ FAIL: New winner {winner} is already a current winner!"
    print("✅ PASS: No overlap with current winners")
    
    # Verify uniqueness
    assert len(new_winners_ids) == len(set(new_winners_ids)), "❌ FAIL: Duplicate new winners!"
    print("✅ PASS: All new winners are unique")
    
    # Add to current winners
    all_winners = current_winners + new_winners_ids
    print(f"✅ Total winners after reroll: {all_winners} ({len(all_winners)} people)")
    
    print()
    print("=" * 60)
    print("REROLL TEST PASSED! ✅")
    print("=" * 60)

def test_edge_cases():
    """Test edge cases"""
    print()
    print("=" * 60)
    print("EDGE CASE TESTS")
    print("=" * 60)
    
    # Case 1: More winners than participants
    print("\n[Case 1] More winners requested than participants")
    participants = [(i+1, ) for i in range(3)]
    winners_count = 5
    user_ids = [row[0] for row in participants]
    count = min(len(user_ids), winners_count)
    winners = random.sample(user_ids, count)
    print(f"  Participants: {len(participants)}, Requested: {winners_count}")
    print(f"  Winners: {winners} ({len(winners)} people)")
    assert len(winners) == 3, "Should cap at participant count"
    print("  ✅ PASS: Correctly capped at participant count")
    
    # Case 2: No participants
    print("\n[Case 2] No participants")
    participants = []
    user_ids = [row[0] for row in participants]
    winners = []
    if user_ids:
        winners = random.sample(user_ids, min(len(user_ids), 5))
    print(f"  Winners: {winners}")
    assert len(winners) == 0, "Should have no winners"
    print("  ✅ PASS: No winners when no participants")
    
    # Case 3: Exactly matching count
    print("\n[Case 3] Exactly 5 participants for 5 winners")
    participants = [(i+1, ) for i in range(5)]
    user_ids = [row[0] for row in participants]
    winners = random.sample(user_ids, min(len(user_ids), 5))
    print(f"  Winners: {winners}")
    assert len(winners) == 5, "Should select all"
    assert set(winners) == set(user_ids), "Should be all participants"
    print("  ✅ PASS: All participants selected")
    
    print()
    print("=" * 60)
    print("ALL EDGE CASES PASSED! ✅")
    print("=" * 60)

if __name__ == "__main__":
    try:
        random.seed(42)  # For reproducible results
        test_winner_selection()
        test_reroll_logic()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
        print("=" * 60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
