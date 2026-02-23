import streamlit as st
import calendar
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
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
    if mood is None: # Logic for deleting/clearing
        c.execute("DELETE FROM mood_entries WHERE date=? AND person_id=?", (date_str, person_id))
    else:
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

# --- 3. App Initialization ---
st.set_page_config(layout="wide", page_title="Vibe Calendar")
init_db()

if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

persons = get_persons()
mood_data = load_mood_data()
MASTER_MOOD_BANK = ["😊 Happy", "😢 Sad", "😠 Angry", "😴 Tired", "💪 Energetic", "😐 Neutral", "🩸 Flow", "⚡ PMT", "✨ Fertile", "🥚 Ovulation", "🧘 Calm", "🍕 Cravings"]

# --- 4. Sidebar ---
with st.sidebar:
    st.title("Vibe Control")
    app_mode = st.radio("App Section", ["Calendar View", "Analytics Tab"])
    view_mode = st.selectbox("View Scale", ["Monthly", "Weekly"])
    
    with st.expander("👤 Manage People"):
        t1, t2 = st.tabs(["Edit/Delete", "Add New"])
        with t2:
            with st.form("add_p"):
                name = st.text_input("Name")
                color = st.color_picker("Color", "#00FFAA")
                moods = st.multiselect("Mood Buttons", MASTER_MOOD_BANK, default=MASTER_MOOD_BANK[:6])
                if st.form_submit_button("Create"):
                    conn = sqlite3.connect('mood_tracker.db')
                    conn.execute("INSERT INTO persons (name, color, moods) VALUES (?, ?, ?)", (name, color, json.dumps(moods)))
                    conn.commit(); conn.close(); st.rerun()
        with t1:
            if persons:
                p_select = st.selectbox("Who?", [p['name'] for p in persons])
                p_obj = next(p for p in persons if p['name'] == p_select)
                with st.form(f"edit_{p_obj['id']}"):
                    new_n = st.text_input("Name", p_obj['name'])
                    new_c = st.color_picker("Color", p_obj['color'])
                    new_m = st.multiselect("Moods", MASTER_MOOD_BANK, default=p_obj['moods'])
                    if st.form_submit_button("Save"):
                        conn = sqlite3.connect('mood_tracker.db')
                        conn.execute("UPDATE persons SET name=?, color=?, moods=? WHERE id=?", (new_n, new_c, json.dumps(new_m), p_obj['id']))
                        conn.commit(); conn.close(); st.rerun()
                if st.button("🗑️ Delete Person"):
                    conn = sqlite3.connect('mood_tracker.db')
                    conn.execute("DELETE FROM persons WHERE id=?", (p_obj['id'],))
                    conn.execute("DELETE FROM mood_entries WHERE person_id=?", (p_obj['id'],))
                    conn.commit(); conn.close(); st.rerun()

# --- 5. Logic Helper Functions ---
def render_day_box(date_obj):
    ds = date_obj.strftime('%Y-%m-%d')
    is_today = date_obj.date() == datetime.now().date()
    
    with st.container(border=True):
        st.write(f"**{date_obj.day}**" + (" (Today)" if is_today else ""))
        if ds in mood_data:
            for p in persons:
                if p['id'] in mood_data[ds]:
                    entry = mood_data[ds][p['id']]
                    st.markdown(f"<span style='color:{p['color']}; font-weight:bold;'>● {entry['mood']}</span>", unsafe_allow_html=True)
                    if entry['notes']:
                        st.markdown(f"<small style='color:gray; display:block;'>{entry['notes'][:12]}...</small>", unsafe_allow_html=True)
        
        if persons:
            with st.popover("➕", use_container_width=True):
                for p in persons:
                    # Colored Name Header
                    st.markdown(f"<h3 style='color:{p['color']}; margin-bottom:0;'>{p['name']}</h3>", unsafe_allow_html=True)
                    
                    c1, c2 = st.columns([3, 1])
                    with c2: # Clear Button
                        if st.button("❌", key=f"clr_{ds}_{p['id']}", help="Clear mood"):
                            update_mood_entry(ds, p['id'], None); st.rerun()
                    
                    mood_cols = st.columns(3)
                    for i, m in enumerate(p['moods']):
                        if mood_cols[i % 3].button(m, key=f"bt_{ds}_{p['id']}_{i}"):
                            update_mood_entry(ds, p['id'], m); st.rerun()
                    
                    note_val = mood_data.get(ds, {}).get(p['id'], {}).get('notes', "")
                    new_note = st.text_input("Note", value=note_val, key=f"nt_{ds}_{p['id']}")
                    if st.button("Save Note", key=f"sv_{ds}_{p['id']}"):
                        cur_m = mood_data.get(ds, {}).get(p['id'], {}).get('mood', '😐 Neutral')
                        update_mood_entry(ds, p['id'], cur_m, new_note); st.rerun()
                    st.divider()

# --- 6. Main View Switcher ---
if app_mode == "Calendar View":
    nav_cols = st.columns([1, 1, 2, 1, 1])
    if nav_cols[0].button("◀ Previous"): 
        move = relativedelta(months=1) if view_mode == "Monthly" else timedelta(days=7)
        st.session_state.current_date -= move
        st.rerun()
    if nav_cols[1].button("Today"):
        st.session_state.current_date = datetime.now()
        st.rerun()
    if nav_cols[4].button("Next ▶"): 
        move = relativedelta(months=1) if view_mode == "Monthly" else timedelta(days=7)
        st.session_state.current_date += move
        st.rerun()

    if view_mode == "Monthly":
        nav_cols[2].header(st.session_state.current_date.strftime('%B %Y'))
        cols = st.columns(7)
        for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]): 
            cols[i].write(f"**{d}**")
        cal = calendar.monthcalendar(st.session_state.current_date.year, st.session_state.current_date.month)
        for week in cal:
            week_cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    with week_cols[i]: render_day_box(datetime(st.session_state.current_date.year, st.session_state.current_date.month, day))
    else:
        nav_cols[2].header(f"Week of {st.session_state.current_date.strftime('%d %b %Y')}")
        start_week = st.session_state.current_date - timedelta(days=st.session_state.current_date.weekday())
        week_cols = st.columns(7)
        for i in range(7):
            curr_day = start_week + timedelta(days=i)
            with week_cols[i]:
                st.write(f"**{curr_day.strftime('%a %d')}**")
                render_day_box(curr_day)

else: # Analytics Tab
    st.header("📊 Mood Analytics")
    conn = sqlite3.connect('mood_tracker.db')
    df_entries = pd.read_sql_query("SELECT * FROM mood_entries", conn)
    df_persons = pd.read_sql_query("SELECT id, name, color FROM persons", conn)
    conn.close()

    if not df_entries.empty and not df_persons.empty:
        df = df_entries.merge(df_persons, left_on='person_id', right_on='id')
        df['date'] = pd.to_datetime(df['date'])
        
        # 1. Mood Frequency Chart
        st.subheader("Mood Distribution")
        fig_pie = px.pie(df, names='mood', color='mood', hole=0.4, title="Overall Mood Breakdowns")
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # 2. Mood Timeline
        st.subheader("Mood Timeline")
        fig_line = px.scatter(df, x='date', y='name', color='mood', size_max=20, 
                             color_discrete_map={p['name']: p['color'] for _, p in df_persons.iterrows()},
                             title="Moods Over Time per Person")
        st.plotly_chart(fig_line, use_container_width=True)
        
        # 3. Data Table
        st.subheader("Raw Mood Log")
        st.dataframe(df[['date', 'name', 'mood', 'notes']].sort_values('date', ascending=False), use_container_width=True)
    else:
        st.info("Add some people and track some moods to see analytics!")
