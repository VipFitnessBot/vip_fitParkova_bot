# db.py
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 0,
            payments_count INTEGER DEFAULT 0,
            last_payment DATE,
            subscription_active INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def update_payment(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT payments_count FROM users WHERE user_id=?", (user_id,))
    payments_count = cur.fetchone()[0] + 1

    # Логіка рівнів
    if payments_count == 1 or payments_count == 2:
        level = 1
    elif payments_count in [3, 4]:
        level = 2
    elif payments_count in [5, 6]:
        level = 3
    elif payments_count in [7, 8]:
        level = 4
    elif payments_count in [9, 10]:
        level = 5
    elif payments_count >= 11:
        level = 6
    else:
        level = 0

    cur.execute("""
        UPDATE users SET payments_count=?, level=?, last_payment=?, subscription_active=1
        WHERE user_id=?
    """, (payments_count, level, datetime.now().date(), user_id))
    conn.commit()
    conn.close()
    return level

def check_subscriptions():
    """Перевірка прострочених оплат: якщо >3 днів — знижуємо рівень."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id, level, last_payment FROM users WHERE subscription_active=1")
    rows = cur.fetchall()
    for user_id, level, last_payment in rows:
        if not last_payment:
            continue
        last_date = datetime.strptime(last_payment, "%Y-%m-%d")
        if (datetime.now().date() - last_date.date()).days > 3:
            new_level = max(0, level - 1)
            cur.execute("""
                UPDATE users SET level=?, subscription_active=0 WHERE user_id=?
            """, (new_level, user_id))
    conn.commit()
    conn.close()
