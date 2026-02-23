import streamlit as st
import calendar
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

# Initialize session state
if 'persons' not in st.session_state:
    st.session_state.persons = []
    
if 'mood_data' not in st.session_state:
    st.session_state.mood_data = {}
    
if 'cycle_phases' not in st.session_state:
    st.session_state.cycle_phases = [
        {'name': 'Menstrual', 'start_day': 1, 'end_day': 5, 'mood': 'Menstruation'},
        {'name': 'Follicular', 'start_day': 6, 'end_day': 8, 'mood': 'Follicular Phase'},
        {'name': 'Fertile', 'start_day': 9, 'end_day': 14, 'mood': 'Fertile'},
        {'name': 'Beware', 'start_day': 10, 'end_day': 14, 'mood': 'Beware'},
        {'name': 'Ovulation', 'start_day': 14, 'end_day': 14, 'mood': 'Ovulation'},
        {'name': 'Luteal', 'start_day': 15, 'end_day': 28, 'mood': 'Luteal Phase'}
    ]

# Function to add a new person
def add_person(name, color, moods):
    person = {
        'name': name,
        'color': color,
        'moods': moods,
        'id': len(st.session_state.persons)
    }
    st.session_state.persons.append(person)

# Function to update mood data
def update_mood_data(date, person_id, mood):
    date_str = date.strftime('%Y-%m-%d')
    if date_str not in st.session_state.mood_data:
        st.session_state.mood_data[date_str] = {}
    st.session_state.mood_data[date_str][person_id] = mood

# Function to apply mood to future dates
def apply_future_moods(start_date, person_id, mood, frequency, occurrences):
    current_date = start_date
    applied_dates = []
    
    for _ in range(occurrences):
        update_mood_data(current_date, person_id, mood)
        applied_dates.append(current_date)
        
        if frequency == 'daily':
            current_date += timedelta(days=1)
        elif frequency == 'weekly':
            current_date += timedelta(weeks=1)
        elif frequency == 'monthly':
            current_date += relativedelta(months=1)
    
    return applied_dates

# Function to apply menstrual cycle moods
def apply_menstrual_cycle(person_id, start_date, cycle_length):
    applied_dates = []
    current_date = start_date
    
    # Apply moods for 3 cycles
    for _ in range(3):
        # Apply phase moods for each day in cycle
        for day in range(cycle_length):
            cycle_day = day + 1
            
            # Find matching phase
            applied = False
            for phase in st.session_state.cycle_phases:
                if phase['start_day'] <= cycle_day <= phase['end_day']:
                    update_mood_data(current_date, person_id, phase['mood'])
                    applied_dates.append(current_date)
                    applied = True
                    break
            
            # Default mood if no phase matches
            if not applied:
                update_mood_data(current_date, person_id, "Normal")
                applied_dates.append(current_date)
            
            current_date += timedelta(days=1)
    
    return applied_dates

# UI Setup
st.title("👥 Multi-Person Mood Tracker")
st.markdown("Track moods for multiple people with personalized color themes")

# Sidebar for person management
with st.sidebar:
    st.header("🧑 Person Management")
    
    with st.form("add_person_form"):
        name = st.text_input("Person Name", "Person 1")
        color = st.color_picker("Theme Color", "#FF0000")
        moods = st.text_area("Moods (comma separated)", "Happy, Sad, Neutral, Excited, Menstruation, Follicular Phase, Fertile, Beware, Ovulation, Luteal Phase").split(',')
        moods = [m.strip() for m in moods if m.strip()]
        
        if st.form_submit_button("Add Person"):
            add_person(name, color, moods)
    
    st.divider()
    st.subheader("Manage Persons")
    
    for i, person in enumerate(st.session_state.persons):
        with st.expander(f"{person['name']} Settings"):
            new_name = st.text_input("Name", person['name'], key=f"name_{i}")
            new_color = st.color_picker("Color", person['color'], key=f"color_{i}")
            
            current_moods = ', '.join(person['moods'])
            new_moods = st.text_area("Moods", current_moods, key=f"moods_{i}").split(',')
            new_moods = [m.strip() for m in new_moods if m.strip()]
            
            if st.button("Update", key=f"update_{i}"):
                st.session_state.persons[i]['name'] = new_name
                st.session_state.persons[i]['color'] = new_color
                st.session_state.persons[i]['moods'] = new_moods
                st.experimental_rerun()
                
            if st.button("❌ Delete", key=f"delete_{i}"):
                del st.session_state.persons[i]
                st.experimental_rerun()
    
    st.divider()
    st.subheader("🔁 Recurring Moods")
    
    if st.session_state.persons:
        with st.form("recurring_form"):
            person = st.selectbox("Person", [p['name'] for p in st.session_state.persons])
            person_id = [p['id'] for p in st.session_state.persons if p['name'] == person][0]
            
            mood = st.selectbox("Mood", st.session_state.persons[person_id]['moods'])
            
            start_date = st.date_input("Start Date", datetime.now())
            frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"])
            occurrences = st.number_input("Occurrences", min_value=1, max_value=365, value=7)
            
            if st.form_submit_button("Apply to Future Dates"):
                applied_dates = apply_future_moods(
                    start_date, person_id, mood, frequency, occurrences
                )
                st.success(f"Applied '{mood}' to {len(applied_dates)} future dates!")
    else:
        st.warning("Add people first!")
    
    st.divider()
    st.subheader("🌸 Menstrual Cycle Tracking")
    
    if st.session_state.persons:
        with st.form("cycle_form"):
            person = st.selectbox("Person for Cycle", [p['name'] for p in st.session_state.persons])
            person_id = [p['id'] for p in st.session_state.persons if p['name'] == person][0]
            
            start_date = st.date_input("Cycle Start Date", datetime.now())
            cycle_length = st.slider("Cycle Length (days)", min_value=21, max_value=40, value=28)
            
            if st.form_submit_button("Apply Menstrual Cycle"):
                applied_dates = apply_menstrual_cycle(
                    person_id, start_date, cycle_length
                )
                st.success(f"Applied {len(applied_dates)} days of menstrual cycle tracking!")
                st.info(f"Using {len(st.session_state.cycle_phases)} custom phases")
    else:
        st.warning("Add people first!")
    
    st.divider()
    st.subheader("⚙️ Cycle Phase Configuration")
    
    with st.expander("Customize Cycle Phases"):
        # Add new phase form
        with st.form("add_phase_form"):
            st.markdown("**Add New Phase**")
            phase_name = st.text_input("Phase Name")
            col1, col2 = st.columns(2)
            with col1:
                start_day = st.number_input("Start Day", min_value=1, max_value=31, value=1)
            with col2:
                end_day = st.number_input("End Day", min_value=1, max_value=31, value=5)
            mood = st.text_input("Associated Mood", "New Mood")
            
            if st.form_submit_button("Add Phase"):
                if end_day < start_day:
                    st.error("End day must be after start day!")
                else:
                    st.session_state.cycle_phases.append({
                        'name': phase_name,
                        'start_day': start_day,
                        'end_day': end_day,
                        'mood': mood
                    })
                    st.success(f"Added '{phase_name}' phase!")
        
        st.divider()
        st.markdown("**Existing Phases**")
        
        # List and edit existing phases
        for i, phase in enumerate(st.session_state.cycle_phases):
            with st.expander(f"{phase['name']} (Days {phase['start_day']}-{phase['end_day']})"):
                new_name = st.text_input("Name", phase['name'], key=f"phase_name_{i}")
                
                col1, col2 = st.columns(2)
                with col1:
                    new_start = st.number_input("Start Day", value=phase['start_day'], 
                                              min_value=1, max_value=31, key=f"phase_start_{i}")
                with col2:
                    new_end = st.number_input("End Day", value=phase['end_day'], 
                                            min_value=1, max_value=31, key=f"phase_end_{i}")
                
                new_mood = st.text_input("Associated Mood", phase['mood'], key=f"phase_mood_{i}")
                
                if st.button("Update", key=f"update_phase_{i}"):
                    st.session_state.cycle_phases[i] = {
                        'name': new_name,
                        'start_day': new_start,
                        'end_day': new_end,
                        'mood': new_mood
                    }
                    st.success("Phase updated!")
                
                if st.button("❌ Delete", key=f"delete_phase_{i}"):
                    del st.session_state.cycle_phases[i]
                    st.experimental_rerun()

# Calendar View
st.header("📅 Mood Calendar")

# Month/Year selection
col1, col2 = st.columns(2)
with col1:
    month = st.selectbox("Month", list(calendar.month_name[1:]), index=datetime.now().month-1)
with col2:
    year = st.selectbox("Year", range(2020, 2031), index=datetime.now().year-2020)

month_num = list(calendar.month_name).index(month)
cal = calendar.monthcalendar(year, month_num)

# Create calendar display
st.markdown("### " + month + " " + str(year))
weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
cols = st.columns(7)

for i, col in enumerate(cols):
    col.markdown(f"**{weekdays[i]}**")

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.write("")
            else:
                current_date = datetime(year, month_num, day)
                date_str = current_date.strftime('%Y-%m-%d')
                
                st.markdown(f"**{day}**")
                
                # Mood selection for each person
                for person in st.session_state.persons:
                    current_mood = ""
                    if date_str in st.session_state.mood_data:
                        if person['id'] in st.session_state.mood_data[date_str]:
                            current_mood = st.session_state.mood_data[date_str][person['id']]
                    
                    mood = st.selectbox(
                        f"{person['name']}",
                        options=[""] + person['moods'],
                        index=person['moods'].index(current_mood)+1 if current_mood in person['moods'] else 0,
                        key=f"mood_{date_str}_{person['id']}",
                        label_visibility="collapsed"
                    )
                    
                    if mood:
                        update_mood_data(current_date, person['id'], mood)
                    
                    # Display colored circle next to name
                    st.markdown(
                        f"<span style='display:inline-block; width:10px; height:10px; "
                        f"border-radius:50%; background-color:{person['color']}; "
                        f"margin-right:5px;'></span>",
                        unsafe_allow_html=True
                    )

# Mood Summary View
st.header("📊 Mood Summary")
if st.session_state.persons:
    # Create date range for the month
    start_date = datetime(year, month_num, 1)
    end_date = datetime(year, month_num, calendar.monthrange(year, month_num)[1])
    date_range = pd.date_range(start_date, end_date)
    
    # Create summary dataframe
    summary_data = []
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        for person in st.session_state.persons:
            mood = st.session_state.mood_data.get(date_str, {}).get(person['id'], "No entry")
            summary_data.append({
                'Date': date.date(),
                'Day': date.strftime('%A'),
                'Person': person['name'],
                'Mood': mood,
                'Color': person['color']
            })
    
    df = pd.DataFrame(summary_data)
    
    # Display summary table with colors
    st.dataframe(
        df.style.apply(lambda row: [f"background-color: {row['Color']}" for _ in row], axis=1),
        hide_index=True,
        height=600
    )
    
    # Mood statistics
    st.subheader("📈 Mood Statistics")
    mood_counts = df.groupby(['Person', 'Mood']).size().unstack(fill_value=0)
    st.bar_chart(mood_counts)
    
    # Phase statistics
    st.subheader("🌙 Cycle Phase Statistics")
    cycle_moods = [phase['mood'] for phase in st.session_state.cycle_phases]
    cycle_df = df[df['Mood'].isin(cycle_moods)]
    if not cycle_df.empty:
        phase_counts = cycle_df.groupby('Mood').size()
        st.bar_chart(phase_counts)
    else:
        st.info("No cycle phase data recorded this month")
else:
    st.warning("Add people to start tracking moods!")
