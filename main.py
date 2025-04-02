import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import json
from _calendar import get_calendar_events, calendar_ui, calendar_options


st.set_page_config(page_icon="🐾")

# load event table for the first time
if "event_table" not in ss:
    ss.event_table = pd.read_excel("events.xlsx")

# load config for the first time
if "config" not in ss:
    with open("config.json", "rt") as fh:
        ss.config = json.load(fh)


# keep site updated and rerun if important changes
@st.fragment(run_every="1s")
def update_event_table():
    new_event_table = pd.read_excel("events.xlsx")

    needs_update = False  # there is a change in the event table
    needs_rerun = False  # the user is looking at outdated information -> rerun
    # compare each event
    for old_event, new_event in zip(ss.event_table.iterrows(), new_event_table.iterrows()):

        if not old_event[1].equals(new_event[1]):
            needs_update = True
            if ss.selected_event_title == old_event[1]["title"]:
                needs_rerun = True

    if needs_update:
        ss.event_table = new_event_table
    if needs_rerun:
        st.rerun(scope="app")

st.title("Paw Scheduler")

update_event_table()

ev = get_calendar_events(ss.event_table, ss.config)
selected_calendar_event = calendar_ui(ev)
st.caption("Click on an event to see details and available shifts")

if selected_calendar_event is None:
    # no event selected
    ss.selected_event_title = ""

else:
    # get Series from calendar selection
    ss.selected_event_title = selected_calendar_event["title"]
    selected_event_index = ss.event_table.index[ss.event_table["title"] == ss.selected_event_title].tolist()[0]
    selected_event = ss.event_table.iloc[selected_event_index]

    # ### HEADER ###
    st.header(selected_event.title)
    if selected_event.subtitle:
        st.subheader(selected_event.subtitle)
    room_name = ss.config["resourceName"][selected_event.room]
    st.caption(f"by {selected_event.host} ({selected_event.contact}) at {room_name}")

    st.subheader("Timetable", divider="grey")

    # ### TIMETABLE ###
    time_tab_col, crew_position_col = st.columns(2)

    with time_tab_col:
        timetable = pd.DataFrame(
            [
                selected_event.setup_start[-8:-3],
                selected_event.event_start[-8:-3],
                selected_event.event_end[-8:-3],
                selected_event.teardown_end[-8:-3]
            ],
            index=["Setup Start", "Show Begin", "Show End", "Teardown Finished"],
            columns=["Time (24-hour)"]
        )

        st.dataframe(timetable, use_container_width=False, width=250)

    with crew_position_col:
        positions = ss.config["available_positions"]
        col_config = {}
        assigned_crew_member = {}
        for position in positions:
            assigned_crew_member[position] = selected_event[position]
            if selected_event[position] == "-":
                col_config[position] = st.column_config.TextColumn(
                    position,
                    disabled=True
                )
            else:
                col_config[position] = st.column_config.SelectboxColumn(
                    position,
                    options=ss.config["crew_members"]
                )

        crew_positions = pd.DataFrame(
            columns=positions,
            data=assigned_crew_member,
            index=[selected_event_index]
        )

        new_crew_positions = st.data_editor(
            crew_positions,
            column_config=col_config,
            hide_index=True
        )
        st.caption("Don't forget to scroll to the right or switch to fullscreen"
                   " (:material/fullscreen: in top right corner of the table)")
        st.caption('Click on "None" or an already filled in name to edit it.')

        if not crew_positions.equals(new_crew_positions):
            # crew positions edited
            update_event_table()
            ss.event_table.replace(np.nan, "$unassignedcrewpositions$", inplace=True)
            replacement_data = new_crew_positions.iloc[0].tolist()
            ss.event_table.loc[selected_event_index, positions] = replacement_data
            ss.event_table.replace("$unassignedcrewpositions$", np.nan, inplace=True)
            ss.event_table.to_excel("events.xlsx", index=False)

    # ### SETUP ###
    st.subheader("Setup", divider="grey")
    layout_col, required_eq_col, private_eq_col = st.columns(3)
    with layout_col:
        st.markdown("##### Layout:")
        st.text(selected_event.room_layout)

    with required_eq_col:
        st.markdown("##### Required Equipment:")
        equipment = selected_event.required_equipment.replace(", ", "\n* ")
        st.markdown(f"* {equipment}")

    with private_eq_col:
        st.markdown("##### Private Equipment:")
        equipment = selected_event.private_equipment.replace(", ", "\n* ")
        st.markdown(f"* {equipment}")

    # ### GENERAL INFO ###
    st.subheader("General Info", divider="grey")
    abstract_col, description_col, tags_col = st.columns(3)

    with abstract_col:
        st.markdown("##### Technical Description:")
        st.text(selected_event.technical_description)

        st.markdown("##### Abstract:")
        st.text(selected_event.abstract)

    with description_col:
        st.markdown("##### Description:")
        st.text(selected_event.description)

    with tags_col:
        tags_text_body = ""
        for tag in ss.config["event_tags"]:
            if selected_event[tag[0]]:
                tags_text_body += f"{tag[1]}<br>"

        st.markdown(f'<font color="#d35365">{tags_text_body}</font>', unsafe_allow_html=True)
