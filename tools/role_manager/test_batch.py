
import requests
import time
import json

URL = "http://localhost:5000/api/batch/submit"
STATUS_URL = "http://localhost:5000/api/batch/status"

# Mock payload
payload = {
    "updates": [
        {"id": "123", "name": "Test Role 1", "color": 16711680},
        {"id": "456", "name": "Test Role 2", "color": 65280}
    ],
    "reorder": {
        "categories": []
    }
}

print("1. Submitting Batch...")
try:
    res = requests.post(URL, json=payload, timeout=5)
    data = res.json()
    print("Response:", data)
    
    if 'task_id' in data:
        task_id = data['task_id']
        print(f"Task ID: {task_id}")
        
        # Poll
        for i in range(10):
            print(f"Polling attempt {i+1}...")
            time.sleep(1)
            res = requests.get(f"{STATUS_URL}/{task_id}")
            task = res.json()
            print("Status:", task)
            
            if task.get('status') in ['completed', 'failed']:
                print("Task Finished!")
                break
    else:
        print("Failed to get task_id")

except Exception as e:
    print(f"Error: {e}")
