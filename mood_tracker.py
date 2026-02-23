import streamlit as st
import calendar
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
from dateutil.relativedelta import relativedelta

# Initialize session state
if 'persons' not in st.session_state:
    st.session_state.persons = []
    
if 'mood_data' not in st.session_state:
    st.session_state.mood_data = {}
    
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Monthly"
    
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

# Predefined mood options
DEFAULT_MOODS = ["😊 Happy", "😢 Sad", "😠 Angry", "😨 Anxious", "😴 Tired", "💪 Energetic", "😐 Neutral"]

# Predefined cycle templates
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

# Function to update mood data
def update_mood_data(date, person_id, mood):
    date_str = date.strftime('%Y-%m-%d')
    if date_str not in st.session_state.mood_data:
        st.session_state.mood_data[date_str] = {}
    st.session_state.mood_data[date_str][person_id] = mood

# Function to apply menstrual cycle
def apply_menstrual_cycle(person_id, start_date, cycle_template, cycle_length, apply_future):
    applied_dates = []
    current_date = start_date
    cycles = 3 if apply_future else 1
    
    for _ in range(cycles):
        # Apply phase moods for each day in cycle
        for day in range(cycle_length):
            cycle_day = day + 1
            
            # Find matching phase
            applied = False
            for phase in cycle_template:
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

# --- Calendar Views ---
def show_monthly_view():
    st.header(f"{st.session_state.current_date.strftime('%B %Y')}")
    
    cal = calendar.monthcalendar(
        st.session_state.current_date.year,
        st.session_state.current_date.month
    )
    
    # Navigation
    prev_month = st.session_state.current_date - relativedelta(months=1)
    next_month = st.session_state.current_date + relativedelta(months=1)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ Previous Month", use_container_width=True):
            st.session_state.current_date = prev_month
    with col2:
        st.caption(st.session_state.current_date.strftime("%B %Y"))
    with col3:
        if st.button("Next Month ▶", use_container_width=True):
            st.session_state.current_date = next_month
    
    # Create calendar grid
    cols = st.columns(7)
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, col in enumerate(cols):
        col.markdown(f"**{weekdays[i]}**")
    
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
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    # Day header
                    today_style = "border: 2px solid #ff4b4b; border-radius: 5px;" if current_date.date() == datetime.now().date() else ""
                    st.markdown(f"<div style='padding: 5px; margin-bottom: 5px; {today_style}'>"
                                f"<strong>{day}</strong></div>", 
                                unsafe_allow_html=True)
                    
                    # Mood entries
                    if date_str in st.session_state.mood_data:
                        for person in st.session_state.persons:
                            if person['id'] in st.session_state.mood_data[date_str]:
                                mood = st.session_state.mood_data[date_str][person['id']]
                                st.markdown(
                                    f"<div style='display:flex; align-items:center; margin-bottom: 3px;'>"
                                    f"<span style='background:{person['color']}; width:12px; height:12px; "
                                    f"border-radius:50%; margin-right:5px;'></span>"
                                    f"<span>{mood}</span>"
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                    
                    # Mood buttons
                    if st.session_state.persons:
                        with st.expander("+", expanded=False):
                            for person in st.session_state.persons:
                                st.markdown(f"**{person['name']}**")
                                cols = st.columns(4)
                                for i, mood in enumerate(person['moods']):
                                    if i % 4 == 0 and i > 0:
                                        cols = st.columns(4)
                                    if cols[i % 4].button(mood, key=f"btn_{date_str}_{person['id']}_{i}", 
                                                         use_container_width=True):
                                        update_mood_data(current_date, person['id'], mood)
                                        st.experimental_rerun()

def show_weekly_view():
    st.header(f"Week of {st.session_state.current_date.strftime('%b %d')}")
    
    # Get start of week (Monday)
    start_date = st.session_state.current_date - timedelta(days=st.session_state.current_date.weekday())
    days = [start_date + timedelta(days=i) for i in range(7)]
    
    # Navigation
    prev_week = st.session_state.current_date - timedelta(weeks=1)
    next_week = st.session_state.current_date + timedelta(weeks=1)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ Previous Week", use_container_width=True):
            st.session_state.current_date = prev_week
    with col2:
        st.caption(f"{days[0].strftime('%b %d')} - {days[6].strftime('%b %d')}")
    with col3:
        if st.button("Next Week ▶", use_container_width=True):
            st.session_state.current_date = next_week
    
    # Weekly grid
    cols = st.columns(7)
    for i, col in enumerate(cols):
        with col:
            date = days[i]
            date_str = date.strftime('%Y-%m-%d')
            
            # Day header
            day极速赛车开奖直播官网
_style = "border: 2px solid #ff4b4b;" if date.date() == datetime.now().date() else ""
            st.markdown(f"<div style='padding: 10px; margin-bottom: 10px; text-align: center; background: #f0f2f6; border-radius: 10px; {day_style}'>"
                        f"<strong>{date.strftime('%a')}</strong><br>{date.day}"
                        f"</div>", unsafe_allow_html=True)
            
            # Mood entries
            if date_str in st.session_state.mood_data:
                for person in st.session_state.persons:
                    if person['id'] in st.session_state.mood_data[date_str]:
                        mood = st.session_state.mood_data[date_str][person['id']]
                        st.markdown(
                            f"<div style='display:flex; align-items:center; margin-bottom: 5px; font-size: 0.9em;'>"
                            f"<span style极速赛车开奖直播官网
='background:{person['color']}; width:10px; height:10px; "
                            f"border-radius:50%; margin-right:5px;'></span>"
                            f"<span>{mood}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
            
            # Mood buttons
            if st.session_state.persons:
                with st.expander("+ Moods", expanded=False):
                    for person in st.session_state.persons:
                        st.markdown(f"**{person['name']}**")
                        cols = st.columns(4)
                        for i, mood in enumerate(person['moods']):
                            if i % 4 == 0 and i > 0:
                                cols = st.columns(4)
                            if cols[i % 4].button(mood, key=f"btn_{date_str}_{person['id']}_{i}", 
                                                 use_container_width=True):
                                update_mood_data(date, person['id'], mood)
                                st.experimental_rerun()

def show_yearly_view():
    st.header(f"{st.session_state.current_date.year} Mood Overview")
    
    # Navigation
    prev_year = st.session_state.current_date - relativedelta(years=1)
    next_year = st.session_state.current_date + relativedelta(years=1)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ Previous Year", use_container_width=True):
            st.session_state.current_date = prev_year
    with col2:
        st.caption(str(st.session_state.current_date.year))
    with col3:
        if st.button("Next Year ▶", use_container_width=True):
            st.session_state.current_date = next_year
    
    # Mood heatmap
    heatmap_data = []
    year = st.session_state.current_date.year
    
    for month in range(1, 13):
        days_in_month = calendar.monthrange(year, month)[1]
        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day)
            date_str = date.strftime('%Y-%m-%d')
            mood_count = len(st.session_state.mood_data.get(date_str, {}))
            heatmap_data.append({
                'Date': date,
                'Month': date.strftime('%B'),
                'Day': day,
                'Mood Count': mood_count
            })
    
    if heatmap_data:
        heatmap_df = pd.DataFrame(heatmap_data)
        
        # Create heatmap
        fig = px.density_heatmap(
            heatmap_df,
            x='Day',
            y='Month',
            z='Mood Count',
            histfunc="sum",
            category_orders={"Month": list(calendar.month_name)[1:]},
            color_continuous_scale='Blues',
            title="Mood Frequency Heatmap"
        )
        
        # Make clickable
        fig.update_layout(
            clickmode='event+select',
            yaxis={'categoryorder': 'array', 'categoryarray': list(calendar.month_name)[1:]}
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Drill-down on click
        if st.session_state.get('heatmap_click'):
            click_data = st.session_state.heatmap_click
            month_name = click_data['points'][0]['y']
            day = click_data['points'][0]['x']
            month_num = list(calendar.month_name).index(month_name)
            
            st.session_state.current_date = datetime(year, month_num, 1)
            st.session_state.current_view = "Monthly"
            st.experimental_rerun()
    else:
        st.info("No mood data recorded this year")
    
    # Mood statistics pie chart
    if st.session_state.mood_data:
        mood_counts = {}
        for date_data in st.session_state.mood_data.values():
            for mood in date_data.values():
                mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        mood_df = pd.DataFrame({
            'Mood': list(mood_counts.keys()),
            'Count': list(mood_counts.values())
        })
        
        fig = px.pie(mood_df, names='Mood', values='Count', title="Mood Distribution")
        st.plotly_chart(fig, use_container_width=True)

# --- Main App ---
st.set_page_config(layout="wide", page_title="Simple Mood Tracker", page_icon="😊")

# Sidebar
with st.sidebar:
    st.title("😊 Mood Tracker")
    
    # View selection
    view_option = st.radio("Calendar View", ["Monthly", "Weekly", "Yearly"], 
                          index=["Monthly", "Weekly", "Yearly"].index(st.session_state.current_view))
    st.session_state.current_view = view_option
    
    # Add person form
    st.divider()
    st.subheader("Add Person")
    with st.form("add_person_form"):
        name = st.text_input("Name")
        color = st.color_picker("Color", "#FF0000")
        moods = st.multiselect("Mood Options", DEFAULT_MOODS, DEFAULT_MOODS[:3])
        
        if st.form_submit_button("Add Person"):
            st.session_state.persons.append({
                'name': name,
                'color': color,
                'moods': moods,
                'id': len(st.session_state.persons)
            })
            st.success(f"Added {name}!")
    
    # Current persons
    st.divider()
    st.subheader("Your People")
    if st.session_state.persons:
        for person in st.session_state.persons:
            st.markdown(f"<span style='background:{person['color']}; width:12px; height:12px; border-radius:50%; display:inline-block; margin-right:8px;'></span> **{person['name']}**", unsafe_allow_html=True)
    else:
        st.info("No people added yet")
    
    # Menstrual cycle tracking
    st.divider()
    st.subheader("Menstrual Cycle")
    if st.session_state.persons:
        person = st.selectbox("For Person", [p['name'] for p in st.session_state.persons])
        person_id = [p['id'] for p in st.session_state.persons if p['name'] == person][0]
        
        start_date = st.date_input("Start Date", datetime.now())
        cycle_length = st.slider("Cycle Length", 21, 40, 28)
        
        # Cycle template selection
        selected_template = st.selectbox(
            "Cycle Template", 
            list(CYCLE_PRESETS.keys()),
            index=0
        )
        
        apply_future = st.checkbox("Apply to future cycles", True)
        
        if st.button("Apply Cycle", use_container_width=True):
            applied_dates = apply_menstrual_cycle(
                person_id, 
                start_date, 
                CYCLE_PRESETS[selected_template],
                cycle_length,
                apply_future
            )
            st.success(f"Applied to {len(applied_dates)} days!")
    else:
        st.info("Add people first")

# Main content
if st.session_state.current_view == "Monthly":
    show_monthly_view()
elif st.session_state.current_view == "Weekly":
    show_weekly_view()
else:
    show_yearly_view()



