import streamlit as st
import calendar
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta

# --- 1. Database & Self-Healing Logic ---
def init_db():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS persons
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, moods TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mood_entries
                 (date TEXT, person_id INTEGER, mood TEXT,
                  PRIMARY KEY (date, person_id))''')
    
    c.execute("PRAGMA table_info(mood_entries)")
    columns = [column[1] for column in c.fetchall()]
    if 'notes' not in columns:
        c.execute("ALTER TABLE mood_entries ADD COLUMN notes TEXT")
    
    conn.commit()
    conn.close()

def get_persons():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    try:
        df = pd.read_sql_query("SELECT * FROM persons", conn)
        return [{'id': r['id'], 'name': r['name'], 'color': r['color'], 
                 'moods': json.loads(r['moods'])} for _, r in df.iterrows()]
    except: return []
    finally: conn.close()

def load_mood_data():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    try:
        df_m = pd.read_sql_query("SELECT * FROM mood_entries", conn)
        processed_data = {}
        for _, row in df_m.iterrows():
            note_val = row.get('notes', "") 
            if pd.isna(note_val): note_val = ""
            processed_data.setdefault(row['date'], {})[row['person_id']] = {
                'mood': row['mood'],
                'notes': note_val
            }
        return processed_data
    except: return {}
    finally: conn.close()

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

def update_person_full(p_id, name, color, moods):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE persons SET name=?, color=?, moods=? WHERE id=?", 
              (name, color, json.dumps(moods), p_id))
    conn.commit()
    conn.close()

def delete_person_db(p_id):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM persons WHERE id=?", (p_id,))
    c.execute("DELETE FROM mood_entries WHERE person_id=?", (p_id,))
    conn.commit()
    conn.close()

# --- 2. Cycle Tool Logic ---
CYCLE_PRESETS = {
    "Standard Cycle": [
        {'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'start': 14, 'end': 14, 'mood': '🥚 Ovulation'},
        {'start': 20, 'end': 28, 'mood': '⚡ PMT'}
    ],
    "Fertility Focus": [
        {'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'start': 10, 'end': 16, 'mood': '✨ Fertile'},
        {'start': 14, 'end': 14, 'mood': '🥚 Ovulation'},
        {'start': 24, 'end': 28, 'mood': '⚡ PMT'}
    ],
    "Symptom Heavy": [
        {'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'start': 6, 'end': 9, 'mood': '🩹 Post-Flow'},
        {'start': 14, 'end': 14, 'mood': '🥚 Ovulation'},
        {'start': 18, 'end': 23, 'mood': '🎈 Bloated'},
        {'start': 24, 'end': 28, 'mood': '⚡ PMT'}
    ]
}

def apply_cycle_logic(person_id, start_date, cycle_length, apply_future, preset_name):
    current_date_obj = start_date
    cycles = 3 if apply_future else 1
    template = CYCLE_PRESETS[preset_name]
    for _ in range(cycles):
        for day_idx in range(cycle_length):
            cycle_day = day_idx + 1
            for phase in template:
                if phase['start'] <= cycle_day <= phase['end']:
                    update_mood_entry(current_date_obj.strftime('%Y-%m-%d'), person_id, phase['mood'])
            current_date_obj += timedelta(days=1)

# --- 3. App Initialization ---
init_db()
st.set_page_config(layout="wide", page_title="Vibe Calendar", page_icon="🗓️")

if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

persons = get_persons()
mood_data = load_mood_data()
MASTER_MOOD_BANK = ["😊 Happy", "😢 Sad", "😠 Angry", "😴 Tired", "💪 Energetic", "😐 Neutral", "🩸 Flow", "⚡ PMT", "✨ Fertile", "🎈 Bloated", "🩹 Post-Flow", "🥚 Ovulation", "🧘 Calm", "🍕 Cravings"]

# --- 4. Sidebar UI ---
with st.sidebar:
    st.title("Vibe Control")
    view_mode = st.radio("Switch View", ["Monthly", "Weekly"])
    
    with st.expander("👤 Profile Settings"):
        tab_edit, tab_add = st.tabs(["Edit Moods/Color", "Add New Person"])
        
        with tab_add:
            with st.form("new_p"):
                name = st.text_input("Name")
                color = st.color_picker("Color", "#FF4B4B")
                moods = st.multiselect("Initial Moods", MASTER_MOOD_BANK, default=MASTER_MOOD_BANK[:6])
                if st.form_submit_button("Create"):
                    conn = sqlite3.connect('mood_tracker.db'); c = conn.cursor()
                    c.execute("INSERT INTO persons (name, color, moods) VALUES (?, ?, ?)", (name, color, json.dumps(moods)))
                    conn.commit(); conn.close(); st.rerun()
        
        with tab_edit:
            if persons:
                p_name = st.selectbox("Select Profile", [p['name'] for p in persons])
                p_to_edit = next(p for p in persons if p['name'] == p_name)
                
                # Edit Area
                with st.form(f"edit_form_{p_to_edit['id']}"):
                    upd_name = st.text_input("Name", p_to_edit['name'])
                    upd_color = st.color_picker("Color", p_to_edit['color'])
                    upd_moods = st.multiselect("Edit Mood List", MASTER_MOOD_BANK, default=p_to_edit['moods'])
                    
                    if st.form_submit_button("Save Changes"):
                        update_person_full(p_to_edit['id'], upd_name, upd_color, upd_moods)
                        st.rerun()
                
                st.divider()
                if st.button(f"🗑️ Delete {p_name}", type="primary"):
                    delete_person_db(p_to_edit['id']); st.rerun()
            else: st.info("No profiles yet.")

    if persons:
        st.divider()
        st.subheader("Mood Cycle Tool")
        target_p = st.selectbox("Apply to", [p['name'] for p in persons], key="cycle_p")
        p_obj = next(p for p in persons if p['name'] == target_p)
        cycle_choice = st.selectbox("Select Cycle Type", list(CYCLE_PRESETS.keys()))
        c_start = st.date_input("Start Date", value=datetime.now())
        c_len = st.slider("Cycle Length", 21, 35, 28)
        c_future = st.checkbox("Apply 3 cycles?", value=True)
        if st.button("Generate Cycle"):
            apply_cycle_logic(p_obj['id'], c_start, c_len, c_future, cycle_choice)
            st.success(f"{cycle_choice} Applied!"); st.rerun()

    st.divider()
    if st.button("Prepare Export"):
        conn = sqlite3.connect('mood_tracker.db')
        df_export = pd.read_sql_query("SELECT * FROM mood_entries", conn)
        st.download_button("Download CSV", df_export.to_csv(index=False), "mood_data.csv", "text/csv")

# --- 5. Calendar Rendering ---
def render_day_cell(date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    with st.container(border=True):
        st.markdown(f"**{date_obj.day}**")
        if date_str in mood_data:
            for p in persons:
                if p['id'] in mood_data[date_str]:
                    entry = mood_data[date_str][p['id']]
                    st.markdown(f"<div style='font-size:0.75em; color:{p['color']}; font-weight:bold;'>● {entry['mood']}</div>", unsafe_allow_html=True)
                    if entry['notes']:
                        st.markdown(f"<div style='font-size:0.7em; color:gray; font-style:italic;'>{entry['notes'][:15]}...</div>", unsafe_allow_html=True)
        
        if persons:
            with st.popover("➕", use_container_width=True):
                for p in persons:
                    st.subheader(p['name'])
                    cols = st.columns(3)
                    for i, m in enumerate(p['moods']):
                        if cols[i%3].button(m, key=f"btn_{date_str}_{p['id']}_{i}"):
                            update_mood_entry(date_str, p['id'], m); st.rerun()
                    
                    existing_note = mood_data.get(date_str, {}).get(p['id'], {}).get('notes', "")
                    note = st.text_input("Note", key=f"n_{date_str}_{p['id']}", value=existing_note)
                    if st.button("Save Note", key=f"s_{date_str}_{p['id']}"):
                        current_mood = mood_data.get(date_str, {}).get(p['id'], {}).get('mood', '😐 Neutral')
                        update_mood_entry(date_str, p['id'], current_mood, note); st.rerun()
                    st.divider()

# --- 6. Main View Switcher ---
c1, c2, c3 = st.columns([1, 4, 1])
if view_mode == "Monthly":
    if c
