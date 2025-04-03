import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import json
from _calendar import get_calendar_events, calendar_ui

# set page icon to paws
st.set_page_config(page_icon="🐾")

# load event table for the first time
if "event_table" not in ss:
    ss.event_table = pd.read_excel("events.xlsx")

# load config for the first time
if "config" not in ss:
    with open("config.json", "rt") as fh:
        ss.config = json.load(fh)


# keep event table updated and rerun site if important changes are detected
@st.fragment(run_every="1s")
def update_event_table():
    # read recent event table
    new_event_table = pd.read_excel("events.xlsx")

    needs_update = False  # there is a change in the event table
    needs_rerun = False  # the user is looking at outdated information -> rerun
    # compare each event of event table
    for old_event, new_event in zip(ss.event_table.iterrows(), new_event_table.iterrows()):
        if not old_event[1].equals(new_event[1]):
            # change for an event detected
            needs_update = True
            if ss.selected_event_title == old_event[1]["title"]:
                # user is currently looking at the changed event
                needs_rerun = True  # request rerun

    if needs_update:
        # update event in sessionstate
        ss.event_table = new_event_table
    if needs_rerun:
        # trigger rerun
        st.rerun(scope="app")


# website title
st.markdown('# <font color="#FFFFFF">Paw</font><font color="#d35365">Scheduler</font>', unsafe_allow_html=True)

if not ss.config["editable"]:
    # schedule has been locked
    st.badge("Locked", icon="⛔️", color="primary")

st.write(ss.event_table)

# start periodic updates of event table
update_event_table()

# show interactive calendar
ev = get_calendar_events(ss.event_table, ss.config)
selected_calendar_event = calendar_ui(ev)
st.caption("Click on an event to see details and available shifts")

# build further website if event is selected
if selected_calendar_event is None:
    # no event selected
    ss.selected_event_title = ""

else:
    # get pd.Series from calendar selection and index in event table
    ss.selected_event_title = selected_calendar_event["title"]
    selected_event_index = ss.event_table.index[ss.event_table["title"] == ss.selected_event_title].tolist()[0]
    selected_event = ss.event_table.iloc[selected_event_index]

    # ### EVENT TITLE ###
    st.header(selected_event.title)
    if selected_event.subtitle:
        # show subtitle if available
        st.subheader(selected_event.subtitle)
    room_name = ss.config["resourceName"][selected_event.room]
    st.caption(f"by {selected_event.host} ({selected_event.contact}) at {room_name}")

    # ### TIMETABLE ###
    st.subheader("Timetable", divider="grey")

    time_tab_col, crew_position_col = st.columns(2)

    with time_tab_col:
        # show setup, start, end and teardown_end times
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

        # display timetable as dataframe
        st.dataframe(timetable, use_container_width=False, width=250)

    with crew_position_col:
        # show interactive required positions of this event
        # build pd.Dataframe from positions and names
        positions = ss.config["available_positions"]  # required columns of event table
        col_config = {}  # columns of dataframe
        assigned_crew_member = {}  # values of dataframe
        for position in positions:
            # transfer crew shifts of this event from event table
            assigned_crew_member[position] = selected_event[position]
            if selected_event[position] == "-":
                # position not required
                col_config[position] = st.column_config.TextColumn(
                    position,
                    disabled=True
                )
            else:
                # interactive dropdown menu
                col_config[position] = st.column_config.SelectboxColumn(
                    position,
                    options=ss.config["crew_members"],  # list of crew members
                    disabled=not ss.config["editable"]  # locks table if set in config
                )

        if not ss.config["editable"]:
            # schedule has been locked
            st.badge("Locked", icon="⛔️", color="primary")

        # build dataframe
        crew_positions = pd.DataFrame(
            columns=positions,
            data=assigned_crew_member,
            index=[selected_event_index]
        )

        # show editable dataframe
        new_crew_positions = st.data_editor(
            crew_positions,
            column_config=col_config,
            hide_index=True
        )
        st.caption("Don't forget to scroll to the right or switch to fullscreen"
                   " (:material/fullscreen: in top right corner of the table)")
        st.caption('Click on "None" or an already filled in name to edit it.')

        # write to the event table and save as file
        update_event_table()  # reload recent event table
        replacement_data = new_crew_positions.iloc[0].tolist()  # format positions as list
        ss.event_table.loc[selected_event_index, positions] = replacement_data  # merge into event table
        ss.event_table.to_excel("events.xlsx", index=False)  # save to file

    # ### SETUP ###
    st.subheader("Setup", divider="grey")

    layout_col, required_eq_col, private_eq_col = st.columns(3)

    with layout_col:
        # show required room layout information
        st.markdown("##### Layout:")
        st.text(selected_event.room_layout)

    with required_eq_col:
        # show required equipment
        st.markdown("##### Required Equipment:")
        equipment = selected_event.required_equipment.replace(", ", "\n* ")
        st.markdown(f"* {equipment}")

    with private_eq_col:
        # show private equipment
        st.markdown("##### Private Equipment:")
        equipment = selected_event.private_equipment.replace(", ", "\n* ")
        st.markdown(f"* {equipment}")

    # ### GENERAL INFO ###
    st.subheader("General Info", divider="grey")

    abstract_col, description_col, tags_col = st.columns(3)

    with abstract_col:
        # show technical description
        st.markdown("##### Technical Description:")
        st.text(selected_event.technical_description)

        # show abstract
        st.markdown("##### Abstract:")
        st.text(selected_event.abstract)

    with description_col:
        # show detailed description
        st.markdown("##### Description:")
        st.text(selected_event.description)

    with tags_col:
        # show tags associated with this event
        tags_text_body = ""  # build string with formated tags
        for tag in ss.config["event_tags"]:
            # check every possible tag
            if selected_event[tag[0]]:
                tags_text_body += f"{tag[1]}<br>"

        # print formated tags of this event
        st.markdown(f'<font color="#d35365">{tags_text_body}</font>', unsafe_allow_html=True)
