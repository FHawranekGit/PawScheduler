import pandas as pd
import streamlit as st
from streamlit_calendar import calendar
from pandas import DataFrame


def get_calendar_events(events: DataFrame, config: dict):
    calendar_events = []
    for index, event_series in events.iterrows():
        event_series.fillna("", inplace=True)
        calendar_event = {
            "title": event_series["title"],
            "start": event_series["setup_start"],
            "end": event_series["teardown_end"],
            "resourceId": event_series["room"],
            "backgroundColor": config["resourceColor"][event_series["room"]],
            "borderColor": config["resourceColor"][event_series["room"]]
        }

        event_series.drop(["title", "room", "setup_start", "teardown_end"], inplace=True)
        calendar_event.update(dict(event_series))

        if event_series["nsfw"]:
            calendar_event["borderColor"] = "red"

        calendar_events.append(calendar_event)

    return calendar_events


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


def calendar_ui(events):
    calendar_events = [
        {
            "title": "Event 1",
            "start": "2025-04-01T08:30:00",
            "end": "2025-04-01T10:30:00",
            "resourceId": "a",
            "backgroundColor": "green",
            "borderColor": "green"
        },
        {
            "title": "Con",
            "start": "2025-04-01",
            "end": "2025-04-03",
        }
    ]

    calendar_return = calendar(
        events=events,
        options=calendar_options,
        key='calendar'
        )

    if "callback" in calendar_return:
        if calendar_return["callback"] == "eventClick":
            event = calendar_return["eventClick"]["event"]
            return event
