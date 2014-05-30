import arrow
import codecs
import collections
import json
import os
import sys

from jinja2 import Template, Environment, FileSystemLoader

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(CUR_DIR, 'data')
JSON_DIR = os.path.join(CUR_DIR, 'output/json')
HTML_DIR = os.path.join(CUR_DIR, 'output/html')

# Set up the Jinja template engine
env = Environment()
env.loader = FileSystemLoader(os.path.join(CUR_DIR, 'templates'))

### Part 1: Filesystem Setup ###

# Make sure the output directories exist
for dir_name in ['json/events', 'json/severities', 'json/states', 'json/detail', 'html']:
    if not os.path.exists(os.path.join(CUR_DIR, 'output/%s' % dir_name)):
        os.makedirs(os.path.join(CUR_DIR, 'output/%s' % dir_name))


### Part 2: Load up the data from JSON files ###

# Load the full alerts data
alerts_json_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
with codecs.open(alerts_json_filepath, 'r', 'utf-8') as f:
    full_alert_data = json.loads(f.read())
    full_alerts = full_alert_data['alerts']

# Get the alerts (lite) data
alerts_json_filepath = os.path.join(JSON_DIR, 'alerts.json')
with codecs.open(alerts_json_filepath, 'r', 'utf-8') as f:
    alert_data = json.loads(f.read())
    alerts = alert_data['alerts']

# Get the events data
events_json_filepath = os.path.join(DATA_DIR, 'events.json')
with codecs.open(events_json_filepath, 'r', encoding='UTF-8') as f:
    events_data = json.loads(f.read())

# Remove "skippable" events that we don't want to include in the output
omitted_events = ["911 Telephone Outage", "Child Abduction Emergency", "Law Enforcement Warning", \
    "Test"]
for omitted_event in omitted_events:
    events_data.remove(omitted_event)

# Get the severity data
severities_json_filepath = os.path.join(DATA_DIR, 'severities.json')
with codecs.open(severities_json_filepath, 'r', encoding='UTF-8') as f:
    severities_data = json.loads(f.read())

# Get the states data
states_json_filepath = os.path.join(DATA_DIR, 'states.json')
with codecs.open(states_json_filepath, 'r', encoding='UTF-8') as f:
    states_data = json.loads(f.read())

### Part 4: Write static data files for event types ###

# Create a page for every alert event
events_dict = {}
for event in events_data:
    filtered_alerts = [a for a in alerts if a['event'] == event]
    output_dict = {
        "created_utc": alert_data['created_utc'],
        "next_update_utc": alert_data['next_update_utc'],
        "alerts_count": len(filtered_alerts),
        "alerts": filtered_alerts,
    }
    events_dict[event] = len(filtered_alerts)
    filename = event.lower().replace(" ", "_")
    filepath = os.path.join(JSON_DIR, 'events/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out a static list of all event types with counts
filepath = os.path.join(JSON_DIR, 'events.json')
ordered_events = collections.OrderedDict(sorted(events_dict.items()))
output_dict = {
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "events": ordered_events,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))


### Part 5: Write static data files for severities ###

# Create a page for every alert severity
severities_dict = {}
for severity in severities_data:
    filtered_alerts = [a for a in alerts if a['severity'] == severity]
    output_dict = {
        "created_utc": alert_data['created_utc'],
        "next_update_utc": alert_data['next_update_utc'],
        "alerts_count": len(filtered_alerts),
        "alerts": filtered_alerts,
    }
    severities_dict[severity] = len(filtered_alerts)
    filename = severity.lower().replace(" ", "_")
    filepath = os.path.join(JSON_DIR, 'severities/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out a static list of all severities with counts
filepath = os.path.join(JSON_DIR, 'severities.json')
ordered_severities = collections.OrderedDict(sorted(severities_dict.items()))
output_dict = {
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "serverities": ordered_severities,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))


### Part 6: Write static data files for states ###

# Create a page for every alert state
states_dict = {}
for state in states_data:
    filtered_alerts = [a for a in alerts if state['name'] in a['states']]
    output_dict = {
        "created_utc": alert_data['created_utc'],
        "next_update_utc": alert_data['next_update_utc'],
        "alerts_count": len(filtered_alerts),
        "alerts": filtered_alerts,
    }
    states_dict[state['name']] = len(filtered_alerts)
    filename = state['name'].lower().replace(" ", "_")
    filepath = os.path.join(JSON_DIR, 'states/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out the states dict
filepath = os.path.join(JSON_DIR, 'states.json')
ordered_states = collections.OrderedDict(sorted(states_dict.items()))
output_dict = {
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "states": ordered_states,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))


### Part 7: Write static data file for locations
filepath = os.path.join(JSON_DIR, 'locations.json')

# We have to reach into the full alerts to get the counties for each 
# alert and then the centroid lat/lng for each county
located_alerts = []
for alert in full_alerts:
    located_alerts.append({
        "detail_url": "http://wxalerts.org/json/detail/%s.json" % alert['uuid'],
        "sender": alert['sender'],
        "event": alert['event'],
        "severity": alert['severity'],
        "expires": alert['expires'],
        "states": alert['states'],
        "coordinates": [(c['lng'], c['lat']) for c in alert['counties']],
    })

output_dict = {
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "alerts": located_alerts,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))


### Part 8: Write static HTML file for alerts

# Load the state abbreviations
states = {}
for state_dict in states_data:
    states[state_dict['abbr']] = state_dict['name']

# Write out the events html file
template = env.get_template('events.tpl.html')
created_utc = arrow.get(alert_data['created_utc'])
output = template.render(alerts=full_alerts, written_at_utc=created_utc, written_at_utc_ts=created_utc.timestamp)

output_filepath = os.path.join(HTML_DIR, 'events.html')
with codecs.open(output_filepath, 'w', 'utf-8') as f:
    f.write(output)


### Part 9: Write static HTML file for states

# Loop through the alerts and get the state(s) it applies to.
# Keep a list, by state, of all the alerts.
alerts_by_state = {}
for alert in full_alerts:
    # First we need to get a set of all the states this alert
    # applies to. We can create an array and then run a set operation
    # to remove duplicates.
    state_abbrs = []
    for county in alert['counties']:
        state_abbrs.append(county['state'])
    # Now that we have a unique list of states, we need to look up the full
    # state name. That will be the key that we store the alerts by.
    for abbr in list(set(state_abbrs)):
        state_name = states[abbr]
        if not alerts_by_state.has_key(state_name):
            alerts_by_state[state_name] = []
        # Add the alert to each state it applies to.
        alerts_by_state[state_name].append(alert)

template = env.get_template('states.tpl.html')
created_utc = arrow.get(alert_data['created_utc'])
output = template.render(states=alerts_by_state, written_at_utc=created_utc,
    written_at_utc_ts=created_utc.timestamp)

output_filepath = os.path.join(HTML_DIR, 'states.html')
with codecs.open(output_filepath, 'w', 'utf-8') as f:
    f.write(output)
