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
    view_mode = st.selectbox("View Mode", ["Monthly", "Weekly"])
    
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
                    conn.commit(); conn.close(); st.rerun()

    if persons:
        st.divider()
        st.subheader("Menstrual Cycle Tool")
        c_pers = st.selectbox("Apply to", [p['name'] for p in persons], key="cycle_p")
        c_type = st.selectbox("Cycle Type", list(CYCLE_PRESETS.keys()))
        c_date = st.date_input("Start Date")
        c_len = st.slider("Length", 21, 35, 28)
        c_ext = st.checkbox("Repeat 3 Months?")
        if st.button("Apply Cycle"):
            p_target = next(p for p in persons if p['name'] == c_pers)
            apply_cycle_logic(p_target['id'], c_date, c_len, c_ext, c_type)
            st.rerun()

# --- 5. Calendar Grid Logic ---
def render_day_box(date_obj):
    ds = date_obj.strftime('%Y-%m-%d')
    with st.container(border=True):
        st.write(f"**{date_obj.day}**")
        if ds in mood_data:
            for p in persons:
                if p['id'] in mood_data[ds]:
                    entry = mood_data[ds][p['id']]
                    st.markdown(f"<span style='color:{p['color']}; font-weight:bold;'>● {entry['mood']}</span>", unsafe_allow_html=True)
                    if entry['notes']:
                        st.markdown(f"<small style='color:gray;'>{entry['notes'][:10]}...</small>", unsafe_allow_html=True)
        
        if persons:
            with st.popover("➕", use_container_width=True):
                for p in persons:
                    st.write(f"**{p['name']}**")
                    c1, c2, c3 = st.columns(3)
                    for i, m in enumerate(p['moods']):
                        target_col = [c1, c2, c3][i % 3]
                        if target_col.button(m, key=f"bt_{ds}_{p['id']}_{i}"):
                            update_mood_entry(ds, p['id'], m); st.rerun()
                    
                    note_val = mood_data.get(ds, {}).get(p['id'], {}).get('notes', "")
                    new_note = st.text_input("Note", value=note_val, key=f"nt_{ds}_{p['id']}")
                    if st.button("Save Note", key=f"sv_{ds}_{p['id']}"):
                        current_mood = mood_data.get(ds, {}).get(p['id'], {}).get('mood', '😐 Neutral')
                        update_mood_entry(ds, p['id'], current_mood, new_note); st.rerun()

# --- 6. Main View Rendering ---
nav_left, nav_mid, nav_right = st.columns([1, 3, 1])

if view_mode == "Monthly":
    if nav_left.button("◀ Previous"): st.session_state.current_date -= relativedelta(months=1); st.rerun()
    if nav_right.button("Next ▶"): st.session_state.current_date += relativedelta(months=1); st.rerun()
    nav_mid.header(st.session_state.current_date.strftime('%B %Y'))
    
    # Days Header
    cols = st.columns(7)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, d in enumerate(days): cols[i].write(f"**{d}**")
    
    # Month Grid
    cal = calendar.monthcalendar(st.session_state.current_date.year, st.session_state.current_date.month)
    for week in cal:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with week_cols[i]:
                    render_day_box(datetime(st.session_state.current_date.year, st.session_state.current_date.month, day))
else:
    if nav_left.button("◀ Week
