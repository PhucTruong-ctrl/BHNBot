import asyncio
import json
from typing import Dict, List, Any

# Mock Event Data
# We will load from sell_events.json structure manually or copy relevant parts to ensure standalone execution
# For accurate simulation, we should read the actual file

def load_events():
    with open('data/sell_events.json', 'r') as f:
        data = json.load(f)
    return data.get('events', {})

def calculate_ev(event_key: str, event_data: Dict, base_value: int = 1000):
    print(f"\n--- Analyzing {event_data.get('name', event_key)} ({event_key}) ---")
    print(f"Base Value: {base_value}")
    
    choices = event_data.get('interactive', {}).get('choices', [])
    
    for choice in choices:
        label = choice.get('label', 'Unknown')
        outcomes = choice.get('outcomes', [])
        
        total_weight = sum(o.get('weight', 1.0) for o in outcomes)
        expected_value = 0
        min_value = float('inf')
        max_value = float('-inf')
        
        print(f"  Choice: {label}")
        
        for outcome in outcomes:
            weight = outcome.get('weight', 1.0)
            prob = weight / total_weight
            
            mul = outcome.get('mul', 1.0)
            flat = outcome.get('flat', 0)
            
            outcome_val = (base_value * mul) + flat
            outcome_val = int(outcome_val) # Integer arithmetic in bot
            
            expected_value += outcome_val * prob
            
            min_value = min(min_value, outcome_val)
            max_value = max(max_value, outcome_val)
            
            print(f"    - Outcome ({prob*100:.1f}%): x{mul} + {flat} = {outcome_val} (Change: {outcome_val - base_value})")
            
        print(f"    => Expected Value (EV): {expected_value:.2f}")
        print(f"    => Profit/Loss vs Base: {expected_value - base_value:.2f}")
        print(f"    => Range: [{min_value}, {max_value}]")
        
        # Risk Rating
        if min_value < base_value:
            loss_potential = base_value - min_value
            print(f"    => RISK: Can lose up to {loss_potential}")
        else:
             print(f"    => RISK: Safe (Min >= Base)")

async def main():
    try:
        events = load_events()
        # Filter interactive
        interactive_events = {k: v for k, v in events.items() if v.get('type') == 'interactive'}
        
        # Test Case 1: Standard Fish Value
        base = 1000
        print(f"SIMULATION RUN: Base Value = {base}")
        
        for key, data in interactive_events.items():
            calculate_ev(key, data, base)
            
    except FileNotFoundError:
        print("Error: data/sell_events.json not found. Run from bot root.")

if __name__ == "__main__":
    asyncio.run(main())
