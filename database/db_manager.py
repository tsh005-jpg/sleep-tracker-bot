import sqlite3
from datetime import datetime

DB_NAME = "sleep_tracker.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sleep_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bedtime TEXT,
            wakeup_time TEXT,
            duration REAL,
            feeling TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def start_sleep(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sleep_logs WHERE user_id = ? AND status = 'active'", (user_id,))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO sleep_logs (user_id, bedtime, status) VALUES (?, ?, 'active')", (user_id, now))
    conn.commit()
    conn.close()

def get_active_sleep(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, bedtime FROM sleep_logs WHERE user_id = ? AND status = 'active'", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def end_sleep(log_id, wakeup_time, duration, feeling):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE sleep_logs 
        SET wakeup_time = ?, duration = ?, feeling = ?, status = 'completed'
        WHERE id = ?
    ''', (wakeup_time, duration, feeling, log_id))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=7):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT bedtime, wakeup_time, duration, feeling 
        FROM sleep_logs 
        WHERE user_id = ? AND status = 'completed'
        ORDER BY id DESC LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows[::-1]