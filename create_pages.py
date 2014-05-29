import arrow
import codecs
import json
import os
import sys

from jinja2 import Template, Environment, FileSystemLoader

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

# Set up the Jinja templates
env = Environment()
env.loader = FileSystemLoader(os.path.join(CUR_DIR, 'templates'))

# Make sure the directories exist
for dir_name in ['events', 'severities', 'states']:
    if not os.path.exists(os.path.join(CUR_DIR, 'output/%s' % dir_name)):
        os.makedirs(os.path.join(CUR_DIR, 'output/%s' % dir_name))

# Get the alerts data
alerts_json_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
with codecs.open(alerts_json_filepath, 'r', 'utf-8') as f:
    alert_data = json.loads(f.read())
    alerts = alert_data['alerts']

# Get the events data
events_json_filepath = os.path.join(CUR_DIR, 'data/events.json')
with codecs.open(events_json_filepath, 'r', encoding='UTF-8') as f:
    events_data = json.loads(f.read())

# Get the severity data
severities_json_filepath = os.path.join(CUR_DIR, 'data/severities.json')
with codecs.open(severities_json_filepath, 'r', encoding='UTF-8') as f:
    severities_data = json.loads(f.read())

# Get the states data
states_json_filepath = os.path.join(CUR_DIR, 'data/states.json')
with codecs.open(states_json_filepath, 'r', encoding='UTF-8') as f:
    states_data = json.loads(f.read())

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
    filepath = os.path.join(CUR_DIR, 'output/events/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out the events dict
filepath = os.path.join(CUR_DIR, 'output/events.json')
output_dict = { 
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "events": events_dict,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))

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
    filepath = os.path.join(CUR_DIR, 'output/severities/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out the severities dict
filepath = os.path.join(CUR_DIR, 'output/severities.json')
output_dict = { 
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "serverities": severities_dict,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))

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
    filepath = os.path.join(CUR_DIR, 'output/states/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out the states dict
filepath = os.path.join(CUR_DIR, 'output/states.json')
output_dict = { 
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "states": states_dict,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))


# Create the HTML files (These need the full alerts data)

# Load the full alerts data
alerts_json_filepath = os.path.join(CUR_DIR, 'output/alerts_complete.json')
with codecs.open(alerts_json_filepath, 'r', 'utf-8') as f:
    alert_data = json.loads(f.read())
    alerts = alert_data['alerts']

# Load the state abbreviations
states = {}
for state_dict in states_data:
    states[state_dict['abbr']] = state_dict['name']

# Write out the events html file
template = env.get_template('events.tpl.html')
created_utc = arrow.get(alert_data['created_utc'])
output = template.render(alerts=alerts, written_at_utc=created_utc, written_at_utc_ts=created_utc.timestamp)

output_filepath = os.path.join(CUR_DIR, 'output/events.html')
with codecs.open(output_filepath, 'w', 'utf-8') as f:
    f.write(output)

# Create the states html file

# Loop through the alerts and get the state(s) it applies to.
# Keep a list, by state, of all the alerts.
alerts_by_state = {}
for alert in alerts:
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

output_filepath = os.path.join(CUR_DIR, 'output/states.html')
with codecs.open(output_filepath, 'w', 'utf-8') as f:
    f.write(output)
