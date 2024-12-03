import json
from datetime import datetime
import pytz
import requests
from cachetools import LRUCache
from sd_core.cache import cache_user_credentials

host = "http://localhost:7600/api"

cache = LRUCache(maxsize=100)
events_cache = LRUCache(maxsize=2000)

events_cache_key = "event_cache"
cache_key = "settings"

def credentials():
    creds = cache_user_credentials("SD_KEYS")
    return creds


def get_events():
    print("Working")
    # Check if there's an existing cached event to set start_time_utc
    current_utc_date = datetime.utcnow().date()

    # Check if there is an existing cached event to set start_time_utc
    cached_events = events_cache.get(events_cache_key)
    if cached_events and len(cached_events) > 0:
        # Get the end time of the last event in the cache as start_time_utc
        start_time_utc = datetime.strptime(
            cached_events[-1]['end'], "%Y-%m-%dT%H:%M:%SZ"
        )
    else:
        # If no cached event exists, set the start time to the beginning of the current UTC day
        start_time_utc = datetime(current_utc_date.year, current_utc_date.month, current_utc_date.day)

    # Set the current UTC time as end_time_utc
    end_time_utc = datetime.utcnow()

    print(start_time_utc, end_time_utc)

    creds = credentials()
    if not creds:
        print("No credentials found")
        return

    sundial_token = creds['token']
    response = requests.get(
        f"{host}/0/dashboard/events?start={start_time_utc}&end={end_time_utc}",
        headers={"Authorization": sundial_token}
    )

    if response.status_code != 200:
        print(f"Error fetching events: {response.status_code}")
        return

    event_data = response.json()
    new_events = []
    if event_data and len(event_data) > 0:
        new_events = event_data['events']
        # Process the new events using listView
        formatted_events = listView(new_events)
    else:
        formatted_events = []

    # Append new events or handle cache logic as needed
    if cached_events:
        last_cached_event = cached_events[-1]
        last_new_event = new_events[-1] if new_events else None

        if last_new_event and last_cached_event['id'] == last_new_event['id']:
            # Replace the last cached event if IDs match
            cached_events[-1] = formatted_events[-1]
        else:
            # Append formatted new events to the cache
            cached_events.extend(formatted_events)
            events_cache[events_cache_key] = cached_events
    else:
        # Initialize cache if empty
        events_cache[events_cache_key] = formatted_events

    # Clear the cache if the current date has passed
    if formatted_events and datetime.now().date() > datetime.strptime(formatted_events[-1]['end'], "%Y-%m-%dT%H:%M:%SZ").date():
        events_cache.clear()
        print("Cache cleared as the day has passed.")

    print("stored events ==> " + str(events_cache.get(events_cache_key)))

    return events_cache.get(events_cache_key)

def listView( events):
    list_view_events = []
    local_tz = datetime.now().astimezone().tzinfo

    for event in events:
        start_time_utc = datetime.strptime(event['start'], "%Y-%m-%dT%H:%M:%SZ")
        end_time_utc = datetime.strptime(event['end'], "%Y-%m-%dT%H:%M:%SZ")

        start_time_local = start_time_utc.replace(tzinfo=pytz.utc).astimezone(local_tz).strftime("%H:%M:%S")
        end_time_local = end_time_utc.replace(tzinfo=pytz.utc).astimezone(local_tz).strftime("%H:%M:%S")
        # time_difference = end_time_local - start_time_local

        time_format = "%H:%M:%S"

        start_time = datetime.strptime(start_time_local, time_format)
        end_time = datetime.strptime(end_time_local, time_format)

        time_difference = end_time - start_time
        difference_str = str(time_difference)

        formatted_event = {
            'time': difference_str,
            'app': event['application_name'],  # Using 'application_name' as specified in your data
            'id': event['event_id'],           # Using 'event_id' as the unique identifier
            'end': event['end']                # Including 'end' for cache clearing checks
        }
        list_view_events.append(formatted_event)

    return list_view_events


def add_settings(key, value):
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    data = json.dumps({"code": key, "value": value})
    settings = requests.post(host + "/0/settings", data=data, headers=headers)
    print(settings.json())
    cache[cache_key] = settings.json()

def retrieve_settings():
    creds = credentials()
    sundail_token = ""
    cached_settings = cache.get(cache_key)
    if cached_settings:
        print("---------->",cached_settings)
        return cached_settings
    else:
        if creds:
            sundail_token = creds["token"] if creds['token'] else None
        try:
            sett = requests.get(host + "/0/getallsettings",
                                headers={"Authorization": sundail_token})
            settings = sett.json()
            print(settings)
        except:
            settings = {}
        return settings