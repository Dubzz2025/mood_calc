import streamlit as st
import calendar
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta

# --- Database Management ---
def init_db():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS persons
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, moods TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mood_entries
                 (date TEXT, person_id INTEGER, mood TEXT, notes TEXT,
                  PRIMARY KEY (date, person_id))''')
    conn.commit()
    conn.close()

def update_person_db(p_id, name, color, moods):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE persons SET name=?, color=?, moods=? WHERE id=?",
              (name, color, json.dumps(moods), p_id))
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

def add_person_db(name, color, moods):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO persons (name, color, moods) VALUES (?, ?, ?)",
              (name, color, json.dumps(moods)))
    conn.commit()
    conn.close()

def get_mood_data():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    try:
        df = pd.read_sql_query("SELECT * FROM mood_entries", conn)
        data = {}
        for _, row in df.iterrows():
            data.setdefault(row['date'], {})[row['person_id']] = {
                'mood': row['mood'],
                'notes': row['notes'] or ""
            }
        return data
    except: return {}
    finally: conn.close()

def update_mood_entry(date_str, person_id, mood, notes=None):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    if notes is None: # Preserve existing notes if only updating mood
        c.execute("SELECT notes FROM mood_entries WHERE date=? AND person_id=?", (date_str, person_id))
        res = c.fetchone()
        notes = res[0] if res else ""
    
    c.execute("INSERT OR REPLACE INTO mood_entries (date, person_id, mood, notes) VALUES (?, ?, ?, ?)",
              (date_str, person_id, mood, notes))
    conn.commit()
    conn.close()

def update_notes_only(date_str, person_id, notes):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    # Find existing mood or default to "Neutral" if adding notes first
    c.execute("SELECT mood FROM mood_entries WHERE date=? AND person_id=?", (date_str, person_id))
    res = c.fetchone()
    mood = res[0] if res else "😐 Neutral"
    
    c.execute("INSERT OR REPLACE INTO mood_entries (date, person_id, mood, notes) VALUES (?, ?, ?, ?)",
              (date_str, person_id, mood, notes))
    conn.commit()
    conn.close()

# --- App Logic ---
init_db()
st.set_page_config(layout="wide", page_title="Mood Calendar", page_icon="📝")

persons = get_persons()
mood_data = get_mood_data()
DEFAULT_MOODS = ["😊 Happy", "😢 Sad", "😠 Angry", "😴 Tired", "💪 Energetic", "😐 Neutral", "🩸 Flow", "⚡ PMT"]

# --- Calendar Cell ---
def render_day_cell(date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    with st.container(border=True):
        st.markdown(f"<div style='text-align: center; font-weight: bold;'>{date_obj.day}</div>", unsafe_allow_html=True)
        
        if date_str in mood_data:
            for p in persons:
                if p['id'] in mood_data[date_str]:
                    entry = mood_data[date_str][p['id']]
                    st.markdown(f"<div style='font-size: 0.75em; color:{p['color']}; font-weight: 600;'>● {entry['mood']}</div>", unsafe_allow_html=True)
                    if entry['notes']:
                        st.markdown(f"<div style='font-size: 0.65em; font-style: italic; color: #666;'>“{entry['notes'][:20]}...”</div>", unsafe_allow_html=True)
        
        if persons:
            with st.popover("➕", use_container_width=True):
                for p in persons:
                    st.subheader(f"{p['name']}")
                    cols = st.columns(3)
                    for i, m_opt in enumerate(p['moods']):
                        if cols[i % 3].button(m_opt, key=f"btn_{date_str}_{p['id']}_{i}"):
                            update_mood_entry(date_str, p['id'], m_opt)
                            st.rerun()
                    
                    # Notes Field
                    existing_notes = mood_data.get(date_str, {}).get(p['id'], {}).get('notes', "")
                    new_note = st.text_area("Notes", value=existing_notes, key=f"note_{date_str}_{p['id']}", height=80)
                    if st.button("Save Note", key=f"save_note_{date_str}_{p['id']}"):
                        update_notes_only(date_str, p['id'], new_note)
                        st.rerun()
                    st.divider()

# --- Sidebar ---
with st.sidebar:
    st.title("Vibe Control")
    view_mode = st.radio("View", ["Monthly", "Weekly"])
    
    # --- Edit Profiles ---
    with st.expander("⚙️ Edit Profiles / Add Person"):
        tab1, tab2 = st.tabs(["Edit Existing", "Add New"])
        
        with tab1:
            if persons:
                edit_name = st.selectbox("Select Profile", [p['name'] for p in persons])
                p_to_edit = next(p for p in persons if p['name'] == edit_name)
                
                new_name = st.text_input("Name", value=p_to_edit['name'])
                new_color = st.color_picker("Color", value=p_to_edit['color'])
                new_moods = st.multiselect("Mood Options", DEFAULT_MOODS, default=p_to_edit['moods'])
                
                if st.button("Update Profile"):
                    update_person_db(p_to_edit['id'], new_name, new_color, new_moods)
                    st.rerun()
            else: st.info("No profiles to edit.")

        with tab2:
            with st.form("new_p"):
                name = st.text_input("Name")
                color = st.color_picker("Color", "#FF4B4B")
                moods = st.multiselect("Moods", DEFAULT_MOODS, default=DEFAULT_MOODS[:6])
                if st.form_submit_button("Create"):
                    add_person_db(name, color, moods)
                    st.rerun()

    # --- Export ---
    st.divider()
    if st.button("Prepare Export"):
        conn = sqlite3.connect('mood_tracker.db')
        df = pd.read_sql_query("SELECT date, mood, notes FROM mood_entries", conn)
        st.download_button("Download CSV", df.to_csv(index=False), "export.csv", "text/csv")

# --- Render Calendar (Shared Logic) ---
if 'current_date' not in st.session_state: st.session_state.current_date = datetime.now()

# Navigation & Header
c1, c2, c3 = st.columns([1, 4, 1])
if c1.button("◀"): st.session_state.current_date -= relativedelta(months=1); st.rerun()
c2.header(st.session_state.current_date.strftime('%B %Y'))
if c3.button("▶"): st.session_state.current_date += relativedelta(months=1); st.rerun()

# Calendar Grid
cal = calendar.monthcalendar(st.session_state.current_date.year, st.session_state.current_date.month)
header_cols = st.columns(7)
for i, d in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']): header_cols[i].write(f"**{d}**")

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            with cols[i]:
                render_day_cell(datetime(st.session_state.current_date.year, st.session_state.current_date.month, day))
