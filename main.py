import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import json
from _calendar import get_calendar_events, calendar_ui
from datetime import datetime


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


def query_lock(parameter: str, value: str, error_message: str) -> None:
    """
    Disables the website if the URL query differs from the required one.
    :param parameter: unique required query parameter
    :param value: value of the query parameter
    :param error_message: displayed error message if the query differs from the set one
    :return: None
    """
    if parameter not in st.query_params:
        st.error(error_message)
        st.stop()
    if st.query_params[parameter] != value:
        st.error(error_message)
        st.stop()


def show_locked_badge() -> None:
    """
    Shows a badge with "Locked" if "editable" is set to false in config
    :return: None
    """
    if not ss.config["editable"]:
        # schedule has been locked
        st.badge("Locked", icon="⛔️", color="primary")


def show_calendar() -> dict:
    """
    Shows an interactive calendar
    :return: selected calendar event as dict
    """
    events = get_calendar_events(ss.event_table, ss.config)
    selection = calendar_ui(events)

    cal_capt_col1, _, cal_capt_col2 = st.columns([4, 1, 3])

    with cal_capt_col1:
        st.caption("Click on an event to see details and available shifts")

    with cal_capt_col2:
        st.caption("Red bordered events are tagged as NSFW")

    return selection


def get_selected_event_series() -> tuple[pd.Series, int]:
    """
    Returns a pandas series from the selected event title in session state
    :return: tuple of (selected event as pandas series, index of selected event)
    """
    sel_event_index = ss.event_table.index[ss.event_table["title"] == ss.selected_event_title].tolist()[0]
    return ss.event_table.iloc[sel_event_index], sel_event_index


def show_event_header(event: pd.Series, short: bool = False) -> None:
    """
    Shows the header information about a given event
    :param event: event as pd.Series
    :param short: if False (default) displays three line form, if True displays two line form
    :return:
    """
    st.header(event.title)

    if short:
        # display two line form
        room_name = ss.config["resourceName"][event.room]
        if event.subtitle:
            # show subtitle if available
            second_line_text = (f'{event.subtitle} <font color="#a3a3a4">by {event.host} '
                                f'({event.contact}) at {room_name}</font>')
        else:
            second_line_text = f'<font color="#a3a3a4">by {event.host} ({event.contact}) at {room_name} </font>'
        st.markdown(second_line_text, unsafe_allow_html=True)
    else:
        # display three line form
        if event.subtitle:
            # show subtitle if available
            st.subheader(event.subtitle)

        room_name = ss.config["resourceName"][event.room]
        st.caption(f"by {event.host} ({event.contact}) at {room_name}")


def show_timetable(event: pd.Series) -> None:
    """
    Shows timetable with setup, event start, event end and teardown end times
    :param event: event as pd.Series
    :return: None
    """
    timetable = pd.DataFrame(
        [
            event.setup_start[-8:-3],
            event.event_start[-8:-3],
            event.event_end[-8:-3],
            event.teardown_end[-8:-3]
        ],
        index=["Setup Start", "Show Begin", "Show End", "Teardown Finished"],
        columns=["Time (24-hour)"]
    )

    # display timetable as dataframe
    st.dataframe(timetable, use_container_width=False, width=250)


def build_interactive_dataframe(event: pd.Series, event_index: int) -> tuple[pd.DataFrame, dict]:
    """
    Builds a pandas dataframe and streamlit columns config for use in a streamlit data editor
    :param event: event as pd.Series
    :param event_index: event index in event table as int
    :return: tuple of (pd.Dataframe with available positions and assigned crew members, column config dict)
    """
    # build pd.Dataframe from positions and names
    positions = ss.config["available_positions"]  # required columns of event table
    col_config = {}  # columns of dataframe
    assigned_crew_member = {}  # values of dataframe
    for position in positions:
        # transfer crew shifts of this event from event table
        assigned_crew_member[position] = event[position]
        if event[position] == "-":
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

    # build dataframe
    crew_positions = pd.DataFrame(
        columns=positions,
        data=assigned_crew_member,
        index=[event_index]
    )
    
    return crew_positions, col_config


def save_to_event_table(new_crew_positions: pd.DataFrame, event_index: int) -> None:
    """
    Merges the new crew position with event table and saves the event table in it's corresponding file
    :param new_crew_positions: pd.DataFrame with the edited crew positions
    :param event_index: event index in event table as int
    :return: None
    """
    # reload recent event table
    update_event_table()

    # format positions as list
    replacement_data = new_crew_positions.iloc[0].tolist()

    # merge into event table
    positions = ss.config["available_positions"]
    ss.event_table.loc[event_index, positions] = replacement_data

    # save to file
    ss.event_table.to_excel("events.xlsx", index=False)


def show_interactive_position_selections_col(event: pd.Series, event_index: int) -> None:
    """
    Shows the interactive table with available crew positions for the selected event
    and saves changes to the event table file
    :param event: event as pd.Series
    :param event_index: event index in event table as int
    :return: None
    """
    # build dataframe and column config
    crew_positions, col_config = build_interactive_dataframe(event, event_index)

    show_locked_badge()

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
    save_to_event_table(new_crew_positions, event_index)


def show_setup_info(event: pd.Series) -> None:
    """
    Shows setup relevant info of the event: Room Layout, Required Equipment, Private Equipment
    :param event: event as pd.Series
    :return: None
    """
    layout_col, required_eq_col, private_eq_col = st.columns(3)

    with layout_col:
        # show required room layout information
        st.markdown("##### Layout:")
        st.text(event.room_layout)

    with required_eq_col:
        # show required equipment
        st.markdown("##### Required Equipment:")
        equipment = event.required_equipment.replace(", ", "\n* ")
        st.markdown(f"* {equipment}")

    with private_eq_col:
        # show private equipment
        st.markdown("##### Private Equipment:")
        equipment = event.private_equipment.replace(", ", "\n* ")
        st.markdown(f"* {equipment}")


def build_tags_string(event: pd.Series) -> str:
    """
    Builds an HTML formated string with all tags of the event
    :param event: event as pd.Series
    :return:
    """
    tags_text_body = ""  # build string with formated tags

    for tag in ss.config["event_tags"]:
        # check every possible tag
        if event[tag[0]]:
            # add tag to the string
            tags_text_body += f"{tag[1]}<br>"

    return tags_text_body


def show_general_event_info(event: pd.Series) -> None:
    """
    Shows general info of the event: Technical Description, Abstract, Description, Tags
    :param event: event as pd.Series
    :return: None
    """
    abstract_col, description_col, tags_col = st.columns(3)

    with abstract_col:
        # show technical description
        st.markdown("##### Technical Description:")
        st.text(event.technical_description)

        # show abstract
        st.markdown("##### Abstract:")
        st.text(event.abstract)

    with description_col:
        # show detailed description
        st.markdown("##### Description:")
        st.text(event.description)

    with tags_col:
        # show tags associated with this event
        tags_text_body = build_tags_string(event)

        # print formated tags of this event
        st.markdown(f'<font color="#d35365">{tags_text_body}</font>', unsafe_allow_html=True)


def show_calendar_tab() -> None:
    """
    Shows the site with an interactive calendar and event details including shift selection
    :return: None
    """
    # show interactive calendar
    selected_calendar_event = show_calendar()

    # build further website if event is selected
    if selected_calendar_event is None:
        # no event selected
        ss.selected_event_title = ""

    else:
        ss.selected_event_title = selected_calendar_event["title"]
        # get pd.Series from calendar selection and index in event table
        selected_event, selected_event_index = get_selected_event_series()

        # ### EVENT TITLE ###
        show_event_header(selected_event)

        # ### TIMETABLE ###
        st.subheader("Timetable", divider="grey")

        time_tab_col, crew_position_col = st.columns(2)

        with time_tab_col:
            # show setup, start, end and teardown_end times
            show_timetable(selected_event)

        with crew_position_col:
            # show interactive required positions of this event
            show_interactive_position_selections_col(selected_event, selected_event_index)

        # ### SETUP ###
        st.subheader("Setup", divider="grey")

        show_setup_info(selected_event)

        # ### GENERAL INFO ###
        st.subheader("General Info", divider="grey")

        show_general_event_info(selected_event)


def show_open_shifts_event_cell(event: pd.Series, num_of_open_positions: int, expand_all: bool):
    with st.expander(f"[{num_of_open_positions}] - {event.title}", expanded=expand_all):
        # event title
        show_event_header(event, short=True)

        time_tab_col, crew_position_col = st.columns(2)

        with time_tab_col:
            # show weekday
            event_start_time = datetime.strptime(event.setup_start, "%Y-%m-%dT%H:%M:%S")
            st.code(event_start_time.strftime("%A"), language=None)

            # show timetable
            show_timetable(event)

        with crew_position_col:
            # build pd.Dataframe from positions and names
            positions = ss.config["available_positions"]  # required columns of event table
            assigned_crew_member = []  # values of dataframe
            for position in positions:
                # transfer crew shifts of this event from event table
                assigned_crew_member.append(event[position])

            # build dataframe
            crew_positions = pd.DataFrame(
                index=positions,
                data=assigned_crew_member,
                columns=["Names"]
            )

            st.dataframe(crew_positions)

            st.caption("Switch to calendar view to edit")


def show_open_shifts_tab() -> None:
    refresh_warning_col, _, expander_settings = st.columns([2, 2, 1])
    with refresh_warning_col:
        # warn user that this list won't update automatically
        with st.expander(":primary[Refresh - Info]"):
            st.warning("This list does not update automatically.\n\n"
                       "Press 🅁 to refresh.")

    with expander_settings:
        # provide option to expand all events
        expand_all = st.checkbox("expand all")

    sorted_event_table = ss.event_table.sort_values(by="setup_start")

    for event_index, event in sorted_event_table.iterrows():
        open_positions = event.isin([np.nan])
        has_open_positions = np.any(open_positions)
        num_of_open_positions = np.sum(open_positions)

        if not has_open_positions:
            # scip event if there are no open positions
            continue

        show_open_shifts_event_cell(event, int(num_of_open_positions), expand_all)


def show_your_shifts_tab() -> None:
    st.info("Coming soon...")


# set page icon to paws
st.set_page_config(page_icon="🐾")

#query_lock("awoo", "2025", "Forbidden")

# load event table for the first time
if "event_table" not in ss:
    ss.event_table = pd.read_excel("events.xlsx")

# load config for the first time
if "config" not in ss:
    with open("config.json", "rt") as fh:
        ss.config = json.load(fh)


# website title
st.markdown('# <font color="#FFFFFF">Paw</font><font color="#d35365">Scheduler</font>', unsafe_allow_html=True)

show_locked_badge()

# start periodic updates of event table
update_event_table()

calendar_tab, open_shifts_tab, your_shifts_tab = st.tabs(["Calendar", "Open Shifts", "Your Shifts"])

with calendar_tab:
    show_calendar_tab()

with open_shifts_tab:
    show_open_shifts_tab()

with your_shifts_tab:
    show_your_shifts_tab()
