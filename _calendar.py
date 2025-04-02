import pandas as pd
import streamlit as st
from streamlit_calendar import calendar
from pandas import DataFrame


def get_calendar_events(events: DataFrame, config: dict) -> list[dict]:
    """
    Convert a pd.DataFrame with events to a list with calendar events
    :param events: Table with events in rows and event specific data in columns
    :param config: Dict with room color and room notation
    :return: list[dict]
    """
    calendar_events = []
    for index, event_series in events.iterrows():
        # iterate over every event
        event_series.fillna("", inplace=True)

        # build event dict
        calendar_event = {
            "title": event_series["title"],
            "start": event_series["setup_start"],
            "end": event_series["teardown_end"],
            "resourceId": event_series["room"],
            "backgroundColor": config["resourceColor"][event_series["room"]],
            "borderColor": config["resourceColor"][event_series["room"]]
        }

        # delete already used information
        # and append all other information for optional later use
        event_series.drop(["title", "room", "setup_start", "teardown_end"], inplace=True)
        calendar_event.update(dict(event_series))

        if event_series["nsfw"]:
            # overwrite border Color if event is NSFW
            calendar_event["borderColor"] = "red"

        calendar_events.append(calendar_event)

    return calendar_events


# general settings of the calendar
calendar_options = {
        "editable": False,
        "navLinks": True,
        "initialView": "timeGridWeek",
        "resourceGroupField": "building",
        "resources": [
            {"id": "MS", "building": "Wimberger", "title": "Main Stage"},
            {"id": "P1", "building": "Wimberger", "title": "Panel Room 1"},
            {"id": "P2", "building": "Flemmings", "title": "Panel Room 2"}
        ],
        "selectable": "false",
        "headerToolbar": {
            "left": "today prev,next",
            "right": "timeGridWeek,resourceTimeGridDay",
        },
    }


def calendar_ui(events: list[dict]):
    """
    Shows an interactive streamlit calendar with the provided events
    :param events: streamlit-calendar compatible list of event dicts
    :return: selected event data (None if no selection)
    """
    # show calendar
    calendar_return = calendar(
        events=events,
        options=calendar_options,
        key='calendar'
        )

    # filter event selection returns
    if "callback" in calendar_return:
        if calendar_return["callback"] == "eventClick":
            event = calendar_return["eventClick"]["event"]
            return event
