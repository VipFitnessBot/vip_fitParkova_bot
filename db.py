import json
import os
from datetime import datetime, timedelta

DB_FILE = "users.json"

def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def update_user_payment(user_id, users):
    user = users.get(user_id, {"level": 0, "payments": 0})
    user["payments"] += 1
    if user["payments"] >= 12:
        user["level"] = 6
    else:
        user["level"] = min(6, (user["payments"] + 1) // 2)
    user["last_payment"] = datetime.now().isoformat()
    user["next_due"] = (datetime.now() + timedelta(days=30)).isoformat()
    users[user_id] = user
    save_users(users)
