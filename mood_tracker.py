import streamlit as st
import calendar
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
from dateutil.relativedelta import relativedelta

# --- 1. Database & Schema Maintenance ---
def init_db():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS persons
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, moods TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mood_entries
                 (date TEXT, person_id INTEGER, mood TEXT, notes TEXT,
                  PRIMARY KEY (date, person_id))''')
    
    # Ensure 'notes' column exists (Migration)
    c.execute("PRAGMA table_info(mood_entries)")
    columns = [column[1] for column in c.fetchall()]
    if 'notes' not in columns:
        c.execute("ALTER TABLE mood_entries ADD COLUMN notes TEXT")
    
    conn.commit()
    conn.close()

def get_persons():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM persons", conn)
    conn.close()
    return [{'id': r['id'], 'name': r['name'], 'color': r['color'], 
             'moods': json.loads(r['moods'])} for _, r in df.iterrows()]

def load_mood_data():
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

# --- 2. Cycle Tool Presets ---
CYCLE_PRESETS = {
    "Mood Cycle (Standard)": [
        {'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'start': 14, 'end': 14, 'mood': '🥚 Ovulation'},
        {'start': 20, 'end': 28, 'mood': '⚡ PMT'}
    ],
    "Fertility Focus": [
        {'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'start': 10, 'end': 16, 'mood': '✨ Fertile'},
        {'start': 14, 'end': 14, 'mood': '🥚 Ovulation'},
        {'start': 24, 'end': 28, 'mood': '⚡ PMT'}
    ]
}

def apply_cycle_logic(person_id, start_date, cycle_length, apply_future, preset_name):
    current_date_obj = start_date
    num_cycles = 3 if apply_future else 1
    template = CYCLE_PRESETS[preset_name]
    for _ in range(num_cycles):
        for day_idx in range(cycle_length):
            cycle_day = day_idx + 1
            for phase in template:
                if phase['start'] <= cycle_day <= phase['end']:
                    update_mood_entry(current_date_obj.strftime('%Y-%m-%d'), person_id, phase['mood'])
            current_date_obj += timedelta(days=1)

# --- 3. App Setup ---
st.set_page_config(layout="wide", page_title="Mood Calendar")
init_db()

if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

persons = get_persons()
mood_data = load_mood_data()
MASTER_MOOD_BANK = ["😊 Happy", "😢 Sad", "😠 Angry", "😴 Tired", "💪 Energetic", "😐 Neutral", "🩸 Flow", "⚡ PMT", "✨ Fertile", "🥚 Ovulation", "🧘 Calm", "🍕 Cravings"]

# --- 4. Sidebar ---
with st.sidebar:
    st.header("Controls")
    view_mode = st.radio("View Mode", ["Monthly", "Weekly"])
    
    with st.expander("👤 Person & Mood Management"):
        tab1, tab2 = st.tabs(["Edit/Delete", "Add New"])
        with tab2:
            with st.form("new_person"):
                n = st.text_input("Name")
                c = st.color_picker("Color", "#FF4B4B")
                m = st.multiselect("Moods", MASTER_MOOD_BANK, default=MASTER_MOOD_BANK[:6])
                if st.form_submit_button("Create"):
                    conn = sqlite3.connect('mood_tracker.db')
                    conn.execute("INSERT INTO persons (name, color, moods) VALUES (?, ?, ?)", (n, c, json.dumps(m)))
                    conn.commit(); conn.close(); st.rerun()
        with tab1:
            if persons:
                p_select = st.selectbox("Select Person", [p['name'] for p in persons])
                p_edit = next(p for p in persons if p['name'] == p_select)
                with st.form(f"edit_{p_edit['id']}"):
                    new_n = st.text_input("Name", p_edit['name'])
                    new_c = st.color_picker("Color", p_edit['color'])
                    new_m = st.multiselect("Mood Buttons", MASTER_MOOD_BANK, default=p_edit['moods'])
                    if st.form_submit_button("Update Profile"):
                        conn = sqlite3.connect('mood_tracker.db')
                        conn.execute("UPDATE persons SET name=?, color=?, moods=? WHERE id=?", (new_n, new_c, json.dumps(new_m), p_edit['id']))
                        conn.commit(); conn.close(); st.rerun()
                if st.button(f"🗑️ Delete {p_select}", type="primary"):
                    conn = sqlite3.connect('mood_tracker.db')
                    conn.execute("DELETE FROM persons WHERE id=?", (p_edit['id'],))
                    conn.execute("DELETE FROM mood_entries WHERE person_id=?", (p_edit['id'],))
                    conn.commit(); conn.close(); st.rerun()

    if persons:
        st.divider()
        st.subheader("Mood Cycle Tool")
        c_p = st.selectbox("Apply to", [p['name'] for p in persons])
        c_type = st.selectbox("Type", list(CYCLE_PRESETS.keys()))
        c_date = st.date_input("Start Date", value=datetime.now())
        c_len = st.slider("Length", 21, 35, 28)
        c_ext = st.checkbox("Repeat 3x?")
        if st.button("Apply Cycle"):
            p_obj = next(p for p in persons if p['name'] == c_p)
            apply_cycle_logic(p_obj['id'], c_date, c_len, c_ext, c_type)
            st.rerun()

# --- 5. Calendar Helper ---
def render_day(date_obj):
    ds = date_obj.strftime('%Y-%m-%d')
    with st.container(border=True):
        st.markdown(f"**{date_obj.day}**")
        if ds in mood_data:
            for p in persons:
                if p['id'] in mood_data[ds]:
                    entry = mood_data[ds][p['id']]
                    st.markdown(f"<div style='font-size:0.8em; color:{p['color']}; font-weight:bold;'>● {entry['mood']}</div>", unsafe_allow_html=True)
                    if entry['notes']:
                        st.caption(f"📝 {entry['notes'][:15]}...")
        
        if persons:
            with st.popover("Edit", use_container_width=True):
                for p in persons:
                    st.markdown(f"**{p['name']}**")
                    cols =
