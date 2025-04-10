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
    for index, event in events.iterrows():
        # iterate over every event
        event.fillna("", inplace=True)

        # build event dict
        calendar_event = {
            "title": event.title,
            "start": event.setup_start,
            "end": event.teardown_end,
            "resourceId": event.room,
            "backgroundColor": config["resourceColor"][event.room],
            "borderColor": config["resourceColor"][event.room]
        }

        # delete already used information
        # and append all other information for optional later use
        event.drop(["title", "room", "setup_start", "teardown_end"], inplace=True)
        calendar_event.update(dict(event))

        if event.nsfw:
            # overwrite border Color if event is NSFW
            calendar_event["borderColor"] = "red"

        calendar_events.append(calendar_event)

    return calendar_events


def calendar_ui(events: list[dict], calendar_options: dict):
    """
    Shows an interactive streamlit calendar with the provided events
    :param events: streamlit-calendar compatible list of event dicts
    :param calendar_options: streamlit-calendar compatible dict with all options
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
