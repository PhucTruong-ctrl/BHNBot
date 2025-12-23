
import os
import sys
import requests
import logging
import json
from flask import Flask, render_template, jsonify, request, make_response
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# --- CONFIGURATION ---
GUILD_ID = "1424116735782682778"
BASE_URL = f"https://discord.com/api/v10"
CATEGORY_ROLE_IDS = [
    "1447197290686058596", # Thành tựu
    "1447198817014255757", # Cảnh giới (Level)
    "1447266358000750702", # Thông tin
    "1447203449744785408"  # Ping/Thông báo
]

# --- SETUP ENV & LOGGING ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
load_dotenv(os.path.join(root_dir, '.env'))
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Setup Logging
log_file = os.path.join(current_dir, 'manager.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RoleManager")

app = Flask(__name__)
HEADERS = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}

# --- CORS SUPPORT ---
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS,PATCH')
    return response

# --- HELPER FUNCTIONS ---
def safe_request(method, url, **kwargs):
    """Wrapper to handle timeouts and connection errors safely."""
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        return response
    except requests.exceptions.Timeout:
        logger.error(f"Timeout connecting to {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

def fetch_all_roles():
    response = safe_request('GET', f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=HEADERS)
    if response and response.status_code == 200:
        return response.json()
    logger.error(f"Failed to fetch roles: {response.text if response else 'No Response'}")
    return None

def process_roles_into_categories(roles):
    # Sort by position descending (Top -> Bottom)
    roles.sort(key=lambda x: x['position'], reverse=True)
    
    categories = []
    # Default 'Uncategorized' for roles at the top/bottom that don't fit
    current_category = {
        "id": "uncategorized_top", 
        "name": "Chưa phân loại (Trên cùng)", 
        "color": 0, 
        "roles": [],
        "is_real_category": False
    }
    
    # We want to maintain order: Top -> Bottom.
    # Logic: 
    # Iterate through roles.
    # If role.id IN CATEGORY_IDS -> Start new Category Group.
    # Else -> Add to current Category Group.
    
    categories.append(current_category)
    
    for role in roles:
        role_id = role['id']
        
        # If this role is a Category Header
        if role_id in CATEGORY_ROLE_IDS:
            # Check if previous category was empty/useless? No, keep it.
            
            # Start new category
            new_cat = {
                "id": role_id,
                "name": role['name'],
                "color": role['color'],
                "roles": [], # The category header role itself is NOT inside the 'roles' list of children
                "is_real_category": True,
                "position": role['position'] # Keep track of header pos
            }
            categories.append(new_cat)
            current_category = new_cat
        else:
            # It's a child role
            current_category["roles"].append(role)
            
    # Filter empty uncategorized groups if needed, but safer to keep to show all roles
    return categories

def find_free_port(start_port=5000, max_port=5100):
    import socket
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(('0.0.0.0', port)) != 0:
                return port
    return None

# --- ASYNC TASK MANAGER ---
import threading
import uuid
import time
from collections import deque

TASKS = {}
MAX_TASK_AGE = 3600 # Clear tasks older than 1 hour

class TaskManager:
    @staticmethod
    def create_task():
        task_id = str(uuid.uuid4())
        TASKS[task_id] = {
            "status": "queued",
            "progress": 0,
            "total": 0,
            "message": "Waiting in queue...",
            "created_at": time.time(),
            "errors": []
        }
        return task_id

    @staticmethod
    def update_task(task_id, status, progress=None, message=None, error=None):
        if task_id in TASKS:
            TASKS[task_id]["status"] = status
            if progress is not None:
                TASKS[task_id]["progress"] = progress
            if message:
                TASKS[task_id]["message"] = message
            if error:
                TASKS[task_id]["errors"].append(error)

    @staticmethod
    def get_task(task_id):
        return TASKS.get(task_id)

    @staticmethod
    def run_background(task_id, func, *args):
        thread = threading.Thread(target=func, args=(task_id, *args))
        thread.daemon = True
        thread.start()

def process_batch(task_id, updates, reorder_payload):
    """
    Background worker.
    1. Process Updates (Name/Color)
    2. Process Reorder
    """
    try:
        total_steps = len(updates) + 1 # +1 for reorder
        current_step = 0
        
        TaskManager.update_task(task_id, "processing", 0, "Starting batch update...")
        
        # 1. Process Individual Updates
        for update in updates:
            role_id = update['id']
            payload = {}
            if 'name' in update: payload['name'] = update['name']
            if 'color' in update: payload['color'] = int(update['color'])
            
            TaskManager.update_task(task_id, "processing", int((current_step/total_steps)*100), f"Updating role {role_id}...")
            
            # Rate limit handling: crude sleep if needed, but requests.patch is synchronous
            res = safe_request('PATCH', f"{BASE_URL}/guilds/{GUILD_ID}/roles/{role_id}", headers=HEADERS, json=payload)
            
            if not res or res.status_code >= 300:
                err = res.text if res else "Timemout/ConnErr"
                TaskManager.update_task(task_id, "processing", error=f"Failed to update {role_id}: {err}")
            
            current_step += 1
            # Polite delay to avoid aggressive rate limits if processing many
            time.sleep(0.2) 

        # 2. Process Reorder
        TaskManager.update_task(task_id, "processing", int((current_step/total_steps)*100), "Reordering roles...")
        
        # We reuse the logic but call the API directly
        # The reorder payload is already formatted as list of {id, position} or we need to format it?
        # The frontend sends 'categories', we need to parse it like in `reorder_roles`
        # Wait, the PLAN said frontend sends 'positions' (final list). 
        # Let's support the existing format "categories" to reuse logic or make frontend do the work?
        # Reusing the parsing logic is safer.
        
        # Parsing Categories to Payload (Code duplication from reorder_roles, or refactor?)
        # Let's extract reorder logic if we can, or just duplicate for safety in this One-Shot.
        # Actually, let's look at arguments. `reorder_payload` is {categories: [...]}.
        
        categories = reorder_payload.get('categories', [])
        ordered_ids = []
        for cat in categories:
            if cat.get('is_real_category'):
                ordered_ids.append(cat['id'])
            for role_id in cat.get('role_ids', []):
                ordered_ids.append(role_id)
        
        total_roles = len(ordered_ids)
        payload = []
        current_pos = total_roles
        for role_id in ordered_ids:
            payload.append({"id": role_id, "position": current_pos})
            current_pos -= 1

        # Send Batch Move
        res = safe_request('PATCH', f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=HEADERS, json=payload)
        
        if not res or res.status_code >= 300:
             err = res.text if res else "Timeout"
             TaskManager.update_task(task_id, "completed", 100, f"Done with errors (Reorder failed: {err})", error=f"Reorder failed: {err}")
        else:
             TaskManager.update_task(task_id, "completed", 100, "All operations completed successfully!")

    except Exception as e:
        logger.exception("Batch processing failed")
        TaskManager.update_task(task_id, "failed", message=f"Internal Server Error: {str(e)}")

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/batch/submit', methods=['POST'])
def batch_submit():
    data = request.json
    updates = data.get('updates', []) # List of {id, name, color}
    reorder_payload = data.get('reorder', {}) # {categories: []}
    
    task_id = TaskManager.create_task()
    TaskManager.run_background(task_id, process_batch, updates, reorder_payload)
    
    return jsonify({"task_id": task_id, "message": "Batch queued"})

@app.route('/api/batch/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = TaskManager.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

@app.route('/api/roles', methods=['GET'])
def get_roles():
    roles = fetch_all_roles()
    if roles:
        data = process_roles_into_categories(roles)
        logger.info(f"Fetched and grouped {len(roles)} roles")
        return jsonify(data)
    return jsonify({"error": "Failed to fetch from Discord API"}), 500

# Legacy endpoints (kept for compatibility or single actions if needed)
@app.route('/api/roles/update/<role_id>', methods=['POST'])
def update_role(role_id):
    data = request.json
    name = data.get('name')
    color = data.get('color') 
    payload = {}
    if name: payload['name'] = name
    if color is not None: payload['color'] = int(color)
    res = safe_request('PATCH', f"{BASE_URL}/guilds/{GUILD_ID}/roles/{role_id}", headers=HEADERS, json=payload)
    if res and res.status_code < 300:
        return jsonify({"message": "Updated successfully", "data": res.json()})
    else:
        return jsonify({"error": res.text if res else "Err"}), res.status_code if res else 500

@app.route('/api/roles/reorder', methods=['POST'])
def reorder_roles():
    # ... Legacy reorder ...
    # We can effectively disable this or keep it.
    pass 


@app.route('/api/roles/create', methods=['POST'])
def create_role():
    data = request.json
    name = data.get('name', 'New Role')
    is_category = data.get('is_category', False)
    
    payload = {
        "name": name,
        "permissions": "0" # Default no perms
    }
    
    logger.info(f"Creating role: {name}")
    
    res = safe_request('POST', f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=HEADERS, json=payload)
    
    if res and res.status_code < 300:
        role_data = res.json()
        logger.info(f"Created Role ID: {role_data['id']}")
        
        # If it's a category, we should append it to our CATEGORY_ROLE_IDS list
        if is_category:
            CATEGORY_ROLE_IDS.append(role_data['id'])
            
        return jsonify(role_data)
    else:
        err_msg = res.text if res else "Connection Error"
        return jsonify({"error": err_msg}), res.status_code if res else 504

if __name__ == '__main__':
    port = find_free_port()
    if not port:
        print("No free port found.")
        sys.exit(1)
        
    # BIND TO 0.0.0.0
    print(f"Server running at http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
