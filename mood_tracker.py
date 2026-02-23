import streamlit as st
import calendar
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
from dateutil.relativedelta import relativedelta

# --- Database Functions ---
def init_db():
    conn = sqlite3.connect('mood_tracker.db')
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS persons
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, moods TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS mood_entries
                 (date TEXT, person_id INTEGER, mood TEXT,
                  PRIMARY KEY (date, person_id))''')
    conn.commit()
    conn.close()

def get_persons():
    conn = sqlite3.connect('mood_tracker.db')
    try:
        df = pd.read_sql_query("SELECT * FROM persons", conn)
        persons = []
        for _, row in df.iterrows():
            persons.append({
                'id': row['id'],
                'name': row['name'],
                'color': row['color'],
                'moods': json.loads(row['moods'])
            })
        return persons
    except:
        return []
    finally:
        conn.close()

def add_person_db(name, color, moods):
    conn = sqlite3.connect('mood_tracker.db')
    c = conn.cursor()
    c.execute("INSERT INTO persons (name, color, moods) VALUES (?, ?, ?)",
              (name, color, json.dumps(moods)))
    conn.commit()
    conn.close()

def delete_person_db(person_id):
    conn = sqlite3.connect('mood_tracker.db')
    c = conn.cursor()
    c.execute("DELETE FROM persons WHERE id = ?", (person_id,))
    c.execute("DELETE FROM mood_entries WHERE person_id = ?", (person_id,))
    conn.commit()
    conn.close()

def get_mood_data():
    conn = sqlite3.connect('mood_tracker.db')
    try:
        df = pd.read_sql_query("SELECT * FROM mood_entries", conn)
        mood_data = {}
        for _, row in df.iterrows():
            if row['date'] not in mood_data:
                mood_data[row['date']] = {}
            mood_data[row['date']][row['person_id']] = row['mood']
        return mood_data
    except:
        return {}
    finally:
        conn.close()

def update_mood_entry(date_str, person_id, mood):
    conn = sqlite3.connect('mood_tracker.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO mood_entries (date, person_id, mood) VALUES (?, ?, ?)",
              (date_str, person_id, mood))
    conn.commit()
    conn.close()

def delete_mood_entry(date_str, person_id):
    conn = sqlite3.connect('mood_tracker.db')
    c = conn.cursor()
    c.execute("DELETE FROM mood_entries WHERE date = ? AND person_id = ?", (date_str, person_id))
    conn.commit()
    conn.close()

# --- Initialize ---
init_db()

# Initialize session state configuration
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Monthly"
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

# Load data from DB
persons = get_persons()
mood_data = get_mood_data()

# Predefined mood options
DEFAULT_MOODS = ["😊 Happy", "😢 Sad", "😠 Angry", "😨 Anxious", "😴 Tired", "💪 Energetic", "😐 Neutral"]

CYCLE_PRESETS = {
    "Standard 28-day": [
        {'name': 'Menstrual', 'start_day': 1, 'end_day': 5, 'mood': 'Menstruation'},
        {'name': 'Follicular', 'start_day': 6, 'end_day': 13, 'mood': 'Follicular'},
        {'name': 'Ovulation', 'start_day': 14, 'end_day': 14, 'mood': 'Ovulation'},
        {'name': 'Luteal', 'start_day': 15, 'end_day': 28, 'mood': 'Luteal'}
    ],
    "Fertility Focused": [
        {'name': 'Menstrual', 'start_day': 1, 'end_day': 5, 'mood': 'Menstruation'},
        {'name': 'Pre-Ovulation', 'start_day': 6, 'end_day': 10, 'mood': 'Pre-Ovulation'},
        {'name': 'Fertile Window', 'start_day': 11, 'end_day': 17, 'mood': 'Fertile'},
        {'name': 'Post-Ovulation', 'start_day': 18, 'end_day': 28, 'mood': 'Post-Ovulation'}
    ],
    "Symptom Tracking": [
        {'name': 'Bleeding', 'start_day': 1, 'end_day': 5, 'mood': 'Bleeding'},
        {'name': 'Beware PMS', 'start_day': 20, 'end_day': 28, 'mood': 'Beware'},
        {'name': 'Ovulation', 'start_day': 14, 'end_day': 14, 'mood': 'Ovulation'},
        {'name': 'Normal', 'start_day': 6, 'end_day': 13, 'mood': 'Normal'},
        {'name': 'Normal', 'start_day': 15, 'end_day': 19, 'mood': 'Normal'}
    ]
}

def apply_menstrual_cycle(person_id, start_date, cycle_template, cycle_length, apply_future):
    current_date_obj = start_date
    cycles = 3 if apply_future else 1
    
    for _ in range(cycles):
        for day in range(cycle_length):
            cycle_day = day + 1
            applied = False
            for phase in cycle_template:
                if phase['start_day'] <= cycle_day <= phase['end_day']:
                    update_mood_entry(current_date_obj.strftime('%Y-%m-%d'), person_id, phase['mood'])
                    applied = True
                    break
            if not applied:
                update_mood_entry(current_date_obj.strftime('%Y-%m-%d'), person_id, "Normal")
            
            current_date_obj += timedelta(days=1)

# --- Views ---
def render_day_cell(date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    day_num = date_obj.day
    
    # Check if today
    today_style = "border: 2px solid #ff4b4b; border-radius: 5px;" if date_obj.date() == datetime.now().date() else ""
    
    # Outer container
    with st.container(border=True):
        st.markdown(f"<div style='text-align: center; margin-bottom: 5px; font-weight: bold; {today_style}'>{day_num}</div>", unsafe_allow_html=True)
        
        # 1. Existing Moods
        if date_str in mood_data:
            for person in persons:
                if person['id'] in mood_data[date_str]:
                    mood = mood_data[date_str][person['id']]
                    st.markdown(
                        f"<div style='display:flex; align-items:center; margin-bottom: 2px; font-size: 0.8em;'>"
                        f"<span style='background:{person['color']}; width:8px; height:8px; border-radius:50%; margin-right:4px;'></span>"
                        f"{mood}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        # 2. Add/Edit Popover
        if persons:
            with st.popover("➕", use_container_width=True):
                st.caption(f"Edit {date_str}")
                for person in persons:
                    st.markdown(f"**{person['name']}**")
                    
                    # Current status
                    current_mood = mood_data.get(date_str, {}).get(person['id'], None)
                    if current_mood:
                        st.info(f"Current: {current_mood}")
                        if st.button("🗑️ Clear", key=f"del_{date_str}_{person['id']}"):
                            delete_mood_entry(date_str, person['id'])
                            st.rerun()

                    # Mood Buttons
                    cols = st.columns(3)
                    for i, mood_opt in enumerate(person['moods']):
                        if cols[i % 3].button(mood_opt, key=f"btn_{date_str}_{person['id']}_{i}"):
                            update_mood_entry(date_str, person['id'], mood_opt)
                            st.rerun()
                    st.divider()

def show_monthly_view():
    st.header(f"{st.session_state.current_date.strftime('%B %Y')}")
    
    cal = calendar.monthcalendar(
        st.session_state.current_date.year,
        st.session_state.current_date.month
    )
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ Prev"):
            st.session_state.current_date -= relativedelta(months=1)
            st.rerun()
    with col2:
        st.caption("Navigate Months")
    with col3:
        if st.button("Next ▶"):
            st.session_state.current_date += relativedelta(months=1)
            st.rerun()
    
    # Calendar Header
    cols = st.columns(7)
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, col in enumerate(cols):
        col.markdown(f"**{weekdays[i]}**")
    
    # Grid
    for week in cal:
        week_cols = st.columns(len(week))
        for i, day in enumerate(week):
            with week_cols[i]:
                if day == 0:
                    st.write("")
                else:
                    current_date = datetime(
                        st.session_state.current_date.year,
                        st.session_state.current_date.month,
                        day
                    )
                    render_day_cell(current_date)

def show_weekly_view():
    st.header(f"Week of {st.session_state.current_date.strftime('%b %d')}")
    
    # Start of week (Monday)
    start_date = st.session_state.current_date - timedelta(days=st.session_state.current_date.weekday())
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ Prev Week"):
            st.session_state.current_date -= timedelta(weeks=1)
            st.rerun()
    with col3:
        if st.button("Next Week ▶"):
            st.session_state.current_date += timedelta(weeks=1)
            st.rerun()
            
    # Weekly Grid
    cols = st.columns(7)
    days = [start_date + timedelta(days=i) for i in range(7)]
    
    for i, date_obj in enumerate(days):
        with cols[i]:
            st.markdown(f"**{date_obj.strftime('%a')}**")
            render_day_cell(date_obj)

def show_yearly_view():
    st.header(f"{st.session_state.current_date.year} Overview")
    
    heatmap_data = []
    year = st.session_state.current_date.year
    
    # Process data for heatmap
    # Use direct query logic as mood_data is already dict
    for date_str, entries in mood_data.items():
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d')
            if d.year == year:
                heatmap_data.append({
                    'Date': d,
                    'Month': d.strftime('%B'),
                    'Day': d.day,
                    'Count': len(entries)
                })
        except:
            pass

    if heatmap_data:
        df = pd.DataFrame(heatmap_data)
        fig = px.density_heatmap(
            df, x='Day', y='Month', z='Count',
            histfunc="sum",
            category_orders={"Month": list(calendar.month_name)[1:]},
            color_continuous_scale='Blues',
            title="Activity Heatmap"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data for this year.")
        
    # Stats
    all_moods = []
    for entries in mood_data.values():
        all_moods.extend(entries.values())
    
    if all_moods:
        mood_series = pd.Series(all_moods)
        fig_pie = px.pie(names=mood_series.unique(), values=mood_series.value_counts(), title="Overall Mood Distribution")
        st.plotly_chart(fig_pie, use_container_width=True)

# --- App Layout ---
st.set_page_config(layout="wide", page_title="Mood Tracker", page_icon="😊")

with st.sidebar:
    st.title("Settings")
    
    # View Switcher
    view = st.radio("View", ["Monthly", "Weekly", "Yearly"])
    st.session_state.current_view = view
    
    st.divider()
    
    # Add Person
    st.subheader("Add Person")
    with st.form("new_person"):
        name = st.text_input("Name")
        color = st.color_picker("Color", "#FF0000")
        moods = st.multiselect("Moods", DEFAULT_MOODS, default=DEFAULT_MOODS[:3])
        if st.form_submit_button("Add"):
            if name:
                add_person_db(name, color, moods)
                st.rerun()
    
    st.divider()
    
    # Manage People
    st.subheader("Manage People")
    if persons:
        for p in persons:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"<span style='color:{p['color']}'>●</span> {p['name']}", unsafe_allow_html=True)
            with col2:
                if st.button("🗑️", key=f"del_person_{p['id']}"):
                    delete_person_db(p['id'])
                    st.rerun()
    else:
        st.info("No people yet.")
        
    st.divider()
    
    # Menstrual Cycle
    st.subheader("Menstrual Cycle Tool")
    if persons:
        s_person_name = st.selectbox("Person", [p['name'] for p in persons])
        s_person = next(p for p in persons if p['name'] == s_person_name)
        
        s_date = st.date_input("Start Date")
        s_len = st.slider("Cycle Length", 21, 35, 28)
        s_type = st.selectbox("Template", list(CYCLE_PRESETS.keys()))
        s_future = st.checkbox("Future Cycles?", value=True)
        
        if st.button("Apply Cycle"):
            apply_menstrual_cycle(s_person['id'], s_date, CYCLE_PRESETS[s_type], s_len, s_future)
            st.success("Cycle Applied!")
            st.rerun()

# --- Main Render ---
if st.session_state.current_view == "Monthly":
    show_monthly_view()
elif st.session_state.current_view == "Weekly":
    show_weekly_view()
else:
    show_yearly_view()
