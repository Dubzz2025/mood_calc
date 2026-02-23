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
                 (date TEXT, person_id INTEGER, mood TEXT,
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

def add_person_db(name, color, moods):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO persons (name, color, moods) VALUES (?, ?, ?)",
              (name, color, json.dumps(moods)))
    conn.commit()
    conn.close()

def delete_person_db(person_id):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM persons WHERE id = ?", (person_id,))
    c.execute("DELETE FROM mood_entries WHERE person_id = ?", (person_id,))
    conn.commit()
    conn.close()

def get_mood_data():
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    try:
        df = pd.read_sql_query("SELECT * FROM mood_entries", conn)
        data = {}
        for _, row in df.iterrows():
            data.setdefault(row['date'], {})[row['person_id']] = row['mood']
        return data
    except: return {}
    finally: conn.close()

def update_mood_entry(date_str, person_id, mood):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO mood_entries (date, person_id, mood) VALUES (?, ?, ?)",
              (date_str, person_id, mood))
    conn.commit()
    conn.close()

def delete_mood_entry(date_str, person_id):
    conn = sqlite3.connect('mood_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM mood_entries WHERE date = ? AND person_id = ?", (date_str, person_id))
    conn.commit()
    conn.close()

# --- Cycle Logic ---
CYCLE_PRESETS = {
    "Mood Cycle": [
        {'name': 'Flow', 'start_day': 1, 'end_day': 5, 'mood': 'Flow'},
        {'name': 'PMT', 'start_day': 20, 'end_day': 28, 'mood': 'PMT'},
        {'name': 'Ovulation', 'start_day': 14, 'end_day': 14, 'mood': 'Ovulation'}
    ]
}

def apply_cycle(person_id, start_date, template_key, cycle_length, apply_future):
    current_date_obj = start_date
    cycles = 3 if apply_future else 1
    template = CYCLE_PRESETS[template_key]
    
    for _ in range(cycles):
        for day_idx in range(cycle_length):
            cycle_day = day_idx + 1
            for phase in template:
                if phase['start_day'] <= cycle_day <= phase['end_day']:
                    update_mood_entry(current_date_obj.strftime('%Y-%m-%d'), person_id, phase['mood'])
            current_date_obj += timedelta(days=1)

# --- App Logic ---
init_db()
st.set_page_config(layout="wide", page_title="Mood Calendar", page_icon="🗓️")

if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

persons = get_persons()
mood_data = get_mood_data()
DEFAULT_MOODS = ["😊 Happy", "😢 Sad", "😠 Angry", "😴 Tired", "💪 Energetic", "😐 Neutral", "🩸 Flow", "⚡ PMT"]

# --- UI Helper ---
def render_day_cell(date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    is_today = date_obj.date() == datetime.now().date()
    bg_color = "#fff4f4" if is_today else "transparent"
    
    with st.container(border=True):
        st.markdown(f"<div style='text-align: center; background-color:{bg_color}; border-radius:5px;'>{date_obj.day}</div>", unsafe_allow_html=True)
        
        if date_str in mood_data:
            for p in persons:
                if p['id'] in mood_data[date_str]:
                    m = mood_data[date_str][p['id']]
                    st.markdown(f"<div style='font-size: 0.75em; color:{p['color']};'>● {m}</div>", unsafe_allow_html=True)
        
        if persons:
            with st.popover("➕", use_container_width=True):
                for p in persons:
                    st.write(f"**Assign to {p['name']}**")
                    cols = st.columns(3)
                    for i, m_opt in enumerate(p['moods']):
                        if cols[i % 3].button(m_opt, key=f"{date_str}_{p['id']}_{i}"):
                            update_mood_entry(date_str, p['id'], m_opt)
                            st.rerun()
                    if date_str in mood_data and p['id'] in mood_data[date_str]:
                        st.button("❌ Clear", key=f"del_{date_str}_{p['id']}", 
                                  on_click=delete_mood_entry, args=(date_str, p['id']))

# --- Sidebar ---
with st.sidebar:
    st.title("Vibe Control")
    view_mode = st.radio("View", ["Monthly", "Weekly", "Yearly"])
    
    with st.expander("👤 Setup New Person"):
        with st.form("add_p"):
            name = st.text_input("Name")
            color = st.color_picker("Personal Color", "#FF4B4B")
            moods = st.multiselect("Available Moods", DEFAULT_MOODS, default=DEFAULT_MOODS[:6])
            if st.form_submit_button("Create Profile"):
                add_person_db(name, color, moods)
                st.rerun()

    if persons:
        st.divider()
        st.subheader("Manage People")
        for p in persons:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"<span style='color:{p['color']}'>●</span> {p['name']}", unsafe_allow_html=True)
            if c2.button("🗑️", key=f"sidebar_del_{p['id']}"):
                delete_person_db(p['id'])
                st.rerun()

        st.divider()
        st.subheader("Cycle Tool")
        target_name = st.selectbox("Assign to", [p['name'] for p in persons])
        target_p = next(p for p in persons if p['name'] == target_name)
        start_date = st.date_input("Start Date", value=datetime.now())
        if st.button("Apply Mood Cycle"):
            apply_cycle(target_p['id'], start_date, "Mood Cycle", 28, True)
            st.success("Cycle generated!")
            st.rerun()

    st.divider()
    st.subheader("Data Export")
    if st.button("Prepare CSV"):
        conn = sqlite3.connect('mood_tracker.db')
        export_df = pd.read_sql_query("""
            SELECT mood_entries.date, persons.name, mood_entries.mood 
            FROM mood_entries 
            JOIN persons ON mood_entries.person_id = persons.id
        """, conn)
        conn.close()
        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name="mood_export.csv", mime="text/csv")

# --- Render Calendar ---
if view_mode == "Monthly":
    col1, col2, col3 = st.columns([1, 4, 1])
    if col1.button("◀"): st.session_state.current_date -= relativedelta(months=1); st.rerun()
    col2.header(st.session_state.current_date.strftime('%B %Y'))
    if col3.button("▶"): st.session_state.current_date += relativedelta(months=1); st.rerun()
    
    cal = calendar.monthcalendar(st.session_state.current_date.year, st.session_state.current_date.month)
    cols = st.columns(7)
    for i, day in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']):
        cols[i].write(f"**{day}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]:
                    render_day_cell(datetime(st.session_state.current_date.year, st.session_state.current_date.month, day))

elif view_mode == "Weekly":
    start = st.session_state.current_date - timedelta(days=st.session_state.current_date.weekday())
    cols = st.columns(7)
    for i in range(7):
        day = start + timedelta(days=i)
        with cols[i]:
            st.write(f"**{day.strftime('%a %d')}**")
            render_day_cell(day)

elif view_mode == "Yearly":
    st.header(f"Overview {st.session_state.current_date.year}")
    # Simple pie chart of all logged moods
    flat_moods = [m for day in mood_data.values() for m in day.values()]
    if flat_moods:
        df = pd.DataFrame(flat_moods, columns=['Mood'])
        fig = px.pie(df, names='Mood', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig, use_container_width=True)
