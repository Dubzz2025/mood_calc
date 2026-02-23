import streamlit as st
import calendar
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
from dateutil.relativedelta import relativedelta

# --- 1. Database Setup ---
def init_db():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS persons
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, moods TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mood_entries
                 (date TEXT, person_id INTEGER, mood TEXT, notes TEXT,
                  PRIMARY KEY (date, person_id))''')
    
    c.execute("PRAGMA table_info(mood_entries)")
    columns = [column[1] for column in c.fetchall()]
    if 'notes' not in columns:
        c.execute("ALTER TABLE mood_entries ADD COLUMN notes TEXT")
    conn.commit()
    conn.close()

def get_persons():
    try:
        conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
        df = pd.read_sql_query("SELECT * FROM persons", conn)
        conn.close()
        return [{'id': r['id'], 'name': r['name'], 'color': r['color'], 
                 'moods': json.loads(r['moods'])} for _, r in df.iterrows()]
    except:
        return []

def load_mood_data():
    try:
        conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
        df_m = pd.read_sql_query("SELECT * FROM mood_entries", conn)
        conn.close()
        processed_data = {}
        for _, row in df_m.iterrows():
            processed_data.setdefault(row['date'], {})[row['person_id']] = {
                'mood': row['mood'],
                'notes': row.get('notes', "") or ""
            }
        return processed_data
    except:
        return {}

def update_mood_entry(date_str, person_id, mood, notes=None):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    if notes is None:
        c.execute("SELECT notes FROM mood_entries WHERE date=? AND person_id=?", (date_str, person_id))
        res = c.fetchone()
        notes = res[0] if res else ""
    c.execute("INSERT OR REPLACE INTO mood_entries (date, person_id, mood, notes) VALUES (?, ?, ?, ?)",
              (date_str, person_id, mood, notes))
    conn.commit()
    conn.close()

# --- 2. Cycle Logic ---
CYCLE_PRESETS = {
    "Standard Cycle": [
        {'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'start': 14, 'end': 14, 'mood': '🥚 Ovulation'},
        {'start': 20, 'end': 28, 'mood': '⚡ PMT'}
    ],
    "Fertility Focus": [
        {'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'start': 10, 'end': 16, 'mood': '✨ Fertile'},
        {'start': 14, 'end': 14, 'mood': '🥚 Ovulation'}
    ]
}

def apply_cycle_
