import json
import random
from collections import defaultdict
from datetime import datetime, timedelta

def load_config():
    with open("data/fishing_global_events.json", "r", encoding="utf-8") as f:
        return json.load(f)

def run_simulation(config, days_to_sim=7, iterations=100):
    """
    Simulates event triggers.
    Since probabilistic events vary, we run 'iterations' weeks to get averages.
    """
    events_cfg = config["events"]
    # Sort by priority
    sorted_event_keys = sorted(
        events_cfg.keys(), 
        key=lambda k: events_cfg[k].get("priority", 0), 
        reverse=True
    )

    # Stats
    week_triggers = defaultdict(int)
    conflicts = defaultdict(int) # (event1, event2) -> count
    hourly_load = defaultdict(int) # hour_of_week -> count active

    # For average calculation
    total_triggers_all_runs = defaultdict(int)

    print(f"Running {iterations} simulations of {days_to_sim} days...")
    
    for _ in range(iterations):
        # State
        last_run_times = {k: -999999 for k in events_cfg}
        active_event = None
        current_time_min = 0 # 0 to 7*24*60
        
        # Minutes in a week
        total_minutes = days_to_sim * 24 * 60
        
        for m in range(0, total_minutes, 1): # Check every minute
            # Current Date Simulation
            day_of_week = (m // (24 * 60)) % 7
            hour_of_day = (m // 60) % 24
            minute_of_hour = m % 60
            hhmm = f"{hour_of_day:02d}:{minute_of_hour:02d}"
            
            # Check Active Event Expiry
            if active_event:
                if m >= active_event["end_time"]:
                    active_event = None
                else:
                    hourly_load[m // 60] += 1
                    continue # One event at a time rule (as per GlobalEventManager line 136)

            # Check Triggers
            potential_triggers = []
            
            for key in sorted_event_keys:
                data = events_cfg[key]
                schedule = data["schedule"]
                
                # Cooldown
                cooldown_min = schedule.get("cooldown_minutes", 0)
                if m * 60 < last_run_times[key] + (cooldown_min * 60):
                    continue
                
                # Days
                days = schedule.get("days", [])
                if days and day_of_week not in days:
                    continue
                
                # Time Range
                in_range = False
                time_ranges = schedule.get("time_ranges", ["00:00-23:59"])
                for rng in time_ranges:
                    start, end = rng.split("-")
                    if start <= hhmm <= end:
                        in_range = True
                        break
                if not in_range:
                    continue
                    
                potential_triggers.append(key)

            # Detect Conflicts (Multiple potential triggers at same moment)
            if len(potential_triggers) > 1:
                # Log usage conflict
                k1 = potential_triggers[0]
                for k2 in potential_triggers[1:]:
                    pair = tuple(sorted((k1, k2)))
                    conflicts[pair] += 1

            # Try to trigger (Priority Order)
            for key in potential_triggers:
                data = events_cfg[key]
                schedule = data["schedule"]
                chance = schedule.get("frequency_chance", 0.0)
                
                # Roll
                triggered = False
                if chance >= 1.0:
                    triggered = True
                else:
                    if random.random() < chance:
                        triggered = True
                
                if triggered:
                    duration = schedule.get("duration_minutes", 30)
                    active_event = {
                        "key": key,
                        "end_time": m + duration
                    }
                    last_run_times[key] = m * 60
                    week_triggers[key] += 1
                    total_triggers_all_runs[key] += 1
                    break # Only one event starts per tick
    
    # Report
    print("\n" + "="*50)
    print("📊 WEEKLY EVENT ANALYSIS (Average over 100 weeks)")
    print("="*50)
    print(f"{'Event':<25} | {'Avg/Week':<10} | {'Chance':<6} | {'Schedule'}")
    print("-" * 75)
    
    for key in sorted_event_keys:
        avg = total_triggers_all_runs[key] / iterations
        data = events_cfg[key]
        sch = data["schedule"]
        chance = sch.get("frequency_chance")
        days = sch.get("days", "ALL")
        if days == []: days = "ALL"
        
        print(f"{key:<25} | {avg:<10.1f} | {chance:<6} | Days: {days}")

    print("\n" + "="*50)
    print("⚔️ DETECTED CONFLICTS (Potential Clashes)")
    print("="*50)
    if not conflicts:
        print("No direct start-time conflicts detected.")
    else:
        for (e1, e2), count in sorted(conflicts.items(), key=lambda x: x[1], reverse=True):
             # Divide by iterations to get avg overlaps per week
             avg_conflict = count / iterations
             if avg_conflict > 0.1:
                print(f"⚠️ {e1} vs {e2}: ~{avg_conflict:.1f} times/week")

    print("\n" + "="*50)
    print("📝 RECOMMENDATIONS")
    print("="*50)
    print("- 'vip_blind_box' runs ALL DAY. Avg will be huge.")
    print("- 'dragon_sacrifice' vs 'cthulhu_raid' overlap on Sat/Sun 20:00.")

if __name__ == "__main__":
    try:
        cfg = load_config()
        run_simulation(cfg)
    except Exception as e:
        print(f"Error: {e}")
