import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

# Load datasets
mentors = pd.read_csv("Mentor.csv")  # Columns: Name, Sector 1, Sector 2, Sector 3, Index
startups = pd.read_csv("Startups - Sheet1.csv")  # Columns: Name, Sector, Contacts, Index

# Initialize time slots
start_time = datetime.strptime("11:00 AM", "%I:%M %p")
end_time = datetime.strptime("2:00 PM", "%I:%M %p")
time_slots = []
slot_duration = timedelta(minutes=15)
gap_duration = timedelta(minutes=5)

while start_time + slot_duration <= end_time:
    time_slots.append(start_time.strftime("%I:%M %p"))
    start_time += slot_duration + gap_duration

# Get current time
current_time = datetime.now().strftime("%I:%M %p")

# Helper function to schedule mentoring sessions
def schedule_mentoring_sessions(mentors, startups, time_slots, excluded_mentors=[], excluded_startups=[]):
    mentor_preferences = {
        mentor["Name"]: [mentor["Sector 1"], mentor["Sector 2"], mentor["Sector 3"]]
        for _, mentor in mentors.iterrows()
        if mentor["Name"] not in excluded_mentors
    }

    mentor_schedule = {mentor["Name"]: [] for _, mentor in mentors.iterrows() if mentor["Name"] not in excluded_mentors}
    startup_counts = {startup["Name"]: 0 for _, startup in startups.iterrows() if startup["Name"] not in excluded_startups}

    unassigned_startups = set(startup_counts.keys())

    for time_slot in time_slots:
        for mentor_name in mentor_schedule.keys():
            preferences = mentor_preferences[mentor_name]
            weights = [40, 30, 30]

            if unassigned_startups:
                available_startups = startups[startups["Name"].isin(unassigned_startups)]
            else:
                available_startups = startups[(startups["Name"].map(startup_counts) < 4) & 
                                              (~startups["Name"].isin(excluded_startups))]

            if available_startups.empty:
                continue

            selected_startup = None
            if available_startups["Sector"].isin(preferences).any():
                chosen_sector = random.choices(preferences, weights=weights, k=1)[0]
                sector_startups = available_startups[available_startups["Sector"] == chosen_sector]
                if not sector_startups.empty:
                    selected_startup = sector_startups.sample(1).iloc[0]
            if selected_startup is None:
                selected_startup = available_startups.sample(1).iloc[0]

            startup_name = selected_startup["Name"]
            startup_sector = selected_startup["Sector"]
            startup_contact = selected_startup["Contacts"]  # Fetch startup contact

            mentor_schedule[mentor_name].append({
                "Name": startup_name,
                "Sector": startup_sector,
                "Time Slot": time_slot,
                "Contacts": startup_contact
            })
            startup_counts[startup_name] += 1
            if startup_name in unassigned_startups:
                unassigned_startups.remove(startup_name)

    return mentor_schedule, startup_counts

# Streamlit UI
st.set_page_config(layout="wide")  # Expand window size
st.title("Mentoring Schedule")
st.subheader("Search for a Mentor or Toggle Availability")

# Initialize session state for excluded mentors and startups
if "excluded_mentors" not in st.session_state:
    st.session_state["excluded_mentors"] = []
if "excluded_startups" not in st.session_state:
    st.session_state["excluded_startups"] = []

# Ensure the session state is a list (fixes 'remove' method error)
if isinstance(st.session_state["excluded_mentors"], str):
    st.session_state["excluded_mentors"] = st.session_state["excluded_mentors"].split(",")
if isinstance(st.session_state["excluded_startups"], str):
    st.session_state["excluded_startups"] = st.session_state["excluded_startups"].split(",")

# Schedule sessions
schedule, startup_counts = schedule_mentoring_sessions(
    mentors, startups, time_slots, st.session_state["excluded_mentors"], st.session_state["excluded_startups"]
)

mentor_search = st.text_input("Enter mentor name").strip().lower()

col_main, col_stats = st.columns([6, 4])

with col_main:
    for _, mentor in mentors.iterrows():
        mentor_name = mentor["Name"]
        preferences = f"({mentor['Sector 1']}, {mentor['Sector 2']}, {mentor['Sector 3']})"

        if mentor_search and mentor_search not in mentor_name.lower():
            continue

        col1, col2 = st.columns([4, 1])
        col1.markdown(f"### Mentor: {mentor_name} {preferences}")

        # Button to toggle mentor availability
        button_label = "Turn On" if mentor_name in st.session_state["excluded_mentors"] else "Turn Off"
        if col2.button(button_label, key=f"mentor_{mentor_name}"):
            if mentor_name in st.session_state["excluded_mentors"]:
                st.session_state["excluded_mentors"].remove(mentor_name)
            else:
                st.session_state["excluded_mentors"].append(mentor_name)
            
            # Persist the settings using query parameters
            st.query_params["excluded_mentors"] = ",".join(st.session_state["excluded_mentors"])
            st.rerun()

        col1.markdown("#### Scheduled Startups:")
        for idx, session in enumerate(schedule.get(mentor_name, [])):
            if session["Time Slot"] == current_time:
                color = "red"  # Current session in red
            elif idx > 0 and schedule.get(mentor_name, [])[idx - 1]["Time Slot"] == current_time:
                color = "green"  # Next session in green
            else:
                color = "black"

            col1.markdown(
                f"- <span style='color:{color}; font-weight:bold;'>"
                f"**{session['Name']}** ({session['Sector']}) at **{session['Time Slot']}**</span>",
                unsafe_allow_html=True
            )
        col1.markdown("---")

with col_stats:
    st.subheader("Mentoring Stats")

    for startup_name, session_count in startup_counts.items():
        startup_contact = startups.loc[startups["Name"] == startup_name, "Contacts"].values[0]
        
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{startup_name}:** {session_count} Sessions")
        col1.write(f"📞 Contact: {startup_contact}")

        button_label = "Turn On" if startup_name in st.session_state["excluded_startups"] else "Turn Off"
        if col2.button(button_label, key=f"stats_startup_{startup_name}"):
            if startup_name in st.session_state["excluded_startups"]:
                st.session_state["excluded_startups"].remove(startup_name)
            else:
                st.session_state["excluded_startups"].append(startup_name)
            
            # Persist the settings using query parameters
            st.query_params["excluded_startups"] = ",".join(st.session_state["excluded_startups"])
            st.rerun()

    st.markdown("---")
