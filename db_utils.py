# db_utils.py - simple JSON-based storage for users
import json, os
from datetime import datetime, timedelta

DB_FILE = "users.json"

def _load():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_user(uid):
    data = _load()
    if str(uid) not in data:
        data[str(uid)] = {
            "payments": 0,
            "level": 0,
            "recToken": None,
            "last_payment": None,
            "next_due": None,
            "status": "inactive"
        }
        _save(data)

def mark_paid(uid, months=1, recToken=None):
    data = _load()
    u = data.get(str(uid))
    if not u:
        ensure_user(uid)
        data = _load()
        u = data[str(uid)]
    u["payments"] = int(u.get("payments",0)) + 1
    p = u["payments"]
    if p <= 0:
        lvl = 0
    elif p in (1,2):
        lvl = 1
    elif p in (3,4):
        lvl = 2
    elif p in (5,6):
        lvl = 3
    elif p in (7,8):
        lvl = 4
    elif p in (9,10):
        lvl = 5
    else:
        lvl = 6
    u["level"] = lvl
    if recToken:
        u["recToken"] = recToken
    now = datetime.utcnow()
    u["last_payment"] = now.isoformat()
    u["next_due"] = (now + timedelta(days=30*months)).isoformat()
    u["status"] = "active"
    data[str(uid)] = u
    _save(data)
    return u

def set_next_due(uid, days):
    data = _load()
    u = data.get(str(uid))
    if not u:
        return
    from datetime import datetime, timedelta
    u["next_due"] = (datetime.utcnow() + timedelta(days=days)).isoformat()
    data[str(uid)] = u
    _save(data)

def get_user(uid):
    return _load().get(str(uid))

def all_users():
    return _load().items()

def reduce_level_for_overdue():
    from datetime import datetime
    data = _load()
    changed = []
    now = datetime.utcnow()
    for k,u in data.items():
        nd = u.get("next_due")
        if not nd:
            continue
        try:
            ndt = datetime.fromisoformat(nd)
        except:
            continue
        overdue_days = (now - ndt).days
        if overdue_days >= 4:
            steps = overdue_days // 4
            new_level = max(0, int(u.get("level",0)) - steps)
            if new_level != u.get("level",0):
                u["level"] = new_level
                u["status"] = "inactive"
                data[k] = u
                changed.append((k,new_level))
    _save(data)
    return changed
