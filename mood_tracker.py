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

def get_persons():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    try:
        df = pd.read_sql_query("SELECT * FROM persons", conn)
        return [{'id': r['id'], 'name': r['name'], 'color': r['color'], 
                 'moods': json.loads(r['moods'])} for _, r in df.iterrows()]
    except: return []
    finally: conn.close()

def delete_person_db(p_id):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM persons WHERE id=?", (p_id,))
    c.execute("DELETE FROM mood_entries WHERE person_id=?", (p_id,))
    conn.commit()
    conn.close()

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

def apply_cycle(person_id, start_date, cycle_length, apply_future):
    current_date_obj = start_date
    cycles = 3 if apply_future else 1
    # Custom template based on your previous request
    template = [
        {'name': 'Flow', 'start': 1, 'end': 5, 'mood': '🩸 Flow'},
        {'name': 'PMT', 'start': 20, 'end': 28, 'mood': '⚡ PMT'},
        {'name': 'Ovulation', 'start': 14, 'end': 14, 'mood': '🥚 Ovulation'}
    ]
    for _ in range(cycles):
        for day_idx in range(cycle_length):
            cycle_day = day_idx + 1
            for phase in template:
                if phase['start'] <= cycle_day <= phase['end']:
                    update_mood_entry(current_date_obj.strftime('%Y-%m-%d'), person_id, phase['mood'])
            current_date_obj += timedelta(days=1)

# --- App Init ---
init_db()
st.set_page_config(layout="wide", page_title="Mood Tracker", page_icon="🗓️")

if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

persons = get_persons()
# Load mood data into a dict for easy access
conn = sqlite3.connect('mood_tracker.db')
df_m = pd.read_sql_query("SELECT * FROM mood_entries", conn)
mood_data = {}
for _, row in df_m.iterrows():
    mood_data.setdefault(row['date'], {})[row['person_id']] = {'mood': row['mood'], 'notes': row['notes'] or ""}
conn.close()

DEFAULT_MOODS = ["😊 Happy", "😢 Sad", "😠 Angry", "😴 Tired", "💪 Energetic", "😐 Neutral", "🩸 Flow", "⚡ PMT"]

# --- Sidebar ---
with st.sidebar:
    st.title("Vibe Control")
    view_mode = st.radio("Switch View", ["Monthly", "Weekly"])
    
    with st.expander("👤 Manage Profiles"):
        tab_edit, tab_add = st.tabs(["Edit/Delete", "Add New"])
        with tab_add:
            with st.form("new_p"):
                name = st.text_input("Name")
                color = st.color_picker("Color", "#FF4B4B")
                moods = st.multiselect("Moods", DEFAULT_MOODS, default=DEFAULT_MOODS[:6])
                if st.form_submit_button("Create"):
                    conn = sqlite3.connect('mood_tracker.db'); c = conn.cursor()
                    c.execute("INSERT INTO persons (name, color, moods) VALUES (?, ?, ?)", (name, color, json.dumps(moods)))
                    conn.commit(); conn.close(); st.rerun()
        
        with tab_edit:
            if persons:
                p_name = st.selectbox("Select Profile", [p['name'] for p in persons])
                p_to_edit = next(p for p in persons if p['name'] == p_name)
                if st.button(f"🗑️ Delete {p_name}", type="primary"):
                    delete_person_db(p_to_edit['id'])
                    st.rerun()
            else: st.info("No profiles yet.")

    if persons:
        st.divider()
        st.subheader("Mood Cycle Tool")
        target_p = st.selectbox("Apply to", [p['name'] for p in persons], key="cycle_p")
        p_obj = next(p for p in persons if p['name'] == target_p)
        c_start = st.date_input("Start Date", value=datetime.now())
        c_len = st.slider("Cycle Length", 21, 35, 28)
        c_future = st.checkbox("Apply 3 cycles?", value=True)
        if st.button("Generate Cycle"):
            apply_cycle(p_obj['id'], c_start, c_len, c_future)
            st.success("Cycle Generated!"); st.rerun()

# --- Calendar Logic ---
def render_day_cell(date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    with st.container(border=True):
        st.markdown(f"**{date_obj.day}**")
        if date_str in mood_data:
            for p in persons:
                if p['id'] in mood_data[date_str]:
                    entry = mood_data[date_str][p['id']]
                    st.markdown(f"<div style='font-size:0.75em; color:{p['color']};'>● {entry['mood']}</div>", unsafe_allow_html=True)
        
        if persons:
            with st.popover("➕", use_container_width=True):
                for p in persons:
                    st.caption(f"Log for {p['name']}")
                    cols = st.columns(3)
                    for i, m in enumerate(p['moods']):
                        if cols[i%3].button(m, key=f"{date_str}_{p['id']}_{i}"):
                            update_mood_entry(date_str, p['id'], m); st.rerun()
                    note = st.text_input("Note", key=f"n_{date_str}_{p['id']}", value=mood_data.get(date_str, {}).get(p['id'], {}).get('notes', ""))
                    if st.button("Save Note", key=f"s_{date_str}_{p['id']}"):
                        update_mood_entry(date_str, p['id'], mood_data.get(date_str, {}).get(p['id'], {}).get('mood', '😐 Neutral'), note)
                        st.rerun()

# --- Main View ---
c1, c2, c3 = st.columns([1, 4, 1])
if view_mode == "Monthly":
    if c1.button("◀"): st.session_state.current_date -= relativedelta(months=1); st.rerun()
    c2.header(st.session_state.current_date.strftime('%B %Y'))
    if c3.button("▶"): st.session_state.current_date += relativedelta(months=1); st.rerun()
    
    cal = calendar.monthcalendar(st.session_state.current_date.year, st.session_state.current_date.month)
    cols = st.columns(7)
    for i, d in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']): cols[i].write(f"**{d}**")
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]: render_day_cell(datetime(st.session_state.current_date.year, st.session_state.current_date.month, day))

else: # Weekly View
    if c1.button("◀ Week"): st.session_state.current_date -= timedelta(days=7); st.rerun()
    c2.header(f"Week of {st.session_state.current_date.strftime('%b %d, %Y')}")
    if c3.button("Week ▶"): st.session_state.current_date += timedelta(days=7); st.rerun()
    
    start_of_week = st.session_state.current_date - timedelta(days=st.session_state.current_date.weekday())
    cols = st.columns(7)
    for i in range(7):
        day = start_of_
