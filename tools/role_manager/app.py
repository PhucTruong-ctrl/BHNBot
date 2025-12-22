
import os
import sys
import requests
import logging
import json
from flask import Flask, render_template, jsonify, request
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# --- CONFIGURATION ---
HOST_IP = "100.118.206.30"
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

# --- HELPER FUNCTIONS ---
def fetch_all_roles():
    response = requests.get(f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    logger.error(f"Failed to fetch roles: {response.text}")
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
            if sock.connect_ex((HOST_IP, port)) != 0:
                return port
    return None

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/roles', methods=['GET'])
def get_roles():
    roles = fetch_all_roles()
    if roles:
        data = process_roles_into_categories(roles)
        logger.info(f"Fetched and grouped {len(roles)} roles")
        return jsonify(data)
    return jsonify({"error": "Failed to fetch"}), 500

@app.route('/api/roles/update/<role_id>', methods=['POST'])
def update_role(role_id):
    data = request.json
    name = data.get('name')
    color = data.get('color') # Expecting decimal integer
    
    payload = {}
    if name: payload['name'] = name
    if color is not None: payload['color'] = int(color)
    
    logger.info(f"Updating Role {role_id}: {payload}")
    
    res = requests.patch(f"{BASE_URL}/guilds/{GUILD_ID}/roles/{role_id}", headers=HEADERS, json=payload)
    if res.status_code < 300:
        return jsonify({"message": "Updated successfully", "data": res.json()})
    else:
        logger.error(f"Update failed: {res.text}")
        return jsonify({"error": res.text}), res.status_code

@app.route('/api/roles/reorder', methods=['POST'])
def reorder_roles():
    """
    Receives list of Categories. Each Category has a list of Role IDs.
    Top category comes first. Inside category, top role comes first.
    """
    data = request.json
    categories = data.get('categories', [])
    
    # Flatten to get the absolute desired order (Top -> Bottom)
    # The API expects {id, position}. 
    # Position logic: Higher number = Higher in list.
    
    # Let's count total items to determine max position
    total_count = 0
    ordered_ids = []
    
    for cat in categories:
        # 1. The Category Header Role itself (if it's a real category)
        if cat.get('is_real_category'):
            ordered_ids.append(cat['id'])
            
        # 2. The Children Roles
        for role_id in cat.get('role_ids', []):
            ordered_ids.append(role_id)
            
    total_roles = len(ordered_ids)
    logger.info(f"Reordering {total_roles} roles...")
    
    # Build Payload
    # We only need to send the roles that are moving, but sending all guarantees state.
    # Caution: We cannot move managed roles. If we try, Discord might error or ignore.
    # Strategy: Send update for ALL roles we know about to ensure order.
    
    payload = []
    current_pos = total_roles # Start from top
    
    # We need to map Ordered List (Top->Bottom) to Position (Max->1)
    # But wait, we don't know the exact absolute position of the top role relative to @everyone/other bots.
    # Actually, we can just send relative updates, but it's safer to use the positions reflected from current state?
    # No, simplest way: Just valid integers. Discord sorts them.
    # If we have 100 roles, and we send positions 100 down to 1, it should work.
    
    # IMPROVEMENT: Fetch current roles to get 'managed' status and filter them out?
    # If we try to move a managed role, it fails.
    # Frontend should prevent dragging managed roles.
    
    for role_id in ordered_ids:
        payload.append({"id": role_id, "position": current_pos})
        current_pos -= 1
        
    # Batch Update
    res = requests.patch(f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=HEADERS, json=payload)
    
    if res.status_code < 300:
        logger.info("Reorder successful")
        return jsonify({"message": "Reorder successful"})
    else:
        logger.error(f"Reorder failed: {res.text}")
        return jsonify({"error": res.text}), res.status_code

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
    
    res = requests.post(f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=HEADERS, json=payload)
    if res.status_code < 300:
        role_data = res.json()
        logger.info(f"Created Role ID: {role_data['id']}")
        
        # If it's a category, we should append it to our CATEGORY_ROLE_IDS list
        # Note: This is in-memory only. For persistence, we should save to a file/db.
        if is_category:
            CATEGORY_ROLE_IDS.append(role_data['id'])
            # Save to file or DB if needed for persistence across restarts
            
        return jsonify(role_data)
    else:
        return jsonify({"error": res.text}), res.status_code

if __name__ == '__main__':
    port = find_free_port()
    if not port:
        print("No free port found.")
        sys.exit(1)
        
    print(f"Server running at http://{HOST_IP}:{port}")
    app.run(host=HOST_IP, port=port, debug=True)
