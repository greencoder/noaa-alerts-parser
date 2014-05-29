import os
import sys
import json
import codecs

from jinja2 import Template, Environment, FileSystemLoader

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

# Make sure the directories exist
for dir_name in ['events', 'severities', 'states']:
    if not os.path.exists(os.path.join(CUR_DIR, 'output/pages/%s' % dir_name)):
        os.makedirs(os.path.join(CUR_DIR, 'output/pages/%s' % dir_name))

# Get the alerts data
alerts_json_filepath = os.path.join(CUR_DIR, 'output/alerts-lite.json')
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
    filepath = os.path.join(CUR_DIR, 'output/pages/events/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out the events dict
filepath = os.path.join(CUR_DIR, 'output/pages/events.json')
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
    filepath = os.path.join(CUR_DIR, 'output/pages/severities/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out the severities dict
filepath = os.path.join(CUR_DIR, 'output/pages/severities.json')
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
    filtered_alerts = [a for a in alerts if state['fips'] in a['states']]
    output_dict = {
        "created_utc": alert_data['created_utc'],
        "next_update_utc": alert_data['next_update_utc'],
        "alerts_count": len(filtered_alerts),
        "alerts": filtered_alerts,
    }
    states_dict[state['name']] = len(filtered_alerts)
    filename = state['name'].lower().replace(" ", "_")
    filepath = os.path.join(CUR_DIR, 'output/pages/states/%s.json' % filename)
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        f.write(json.dumps(output_dict, indent=4))

# Write out the states dict
filepath = os.path.join(CUR_DIR, 'output/pages/states.json')
output_dict = { 
    "created_utc": alert_data['created_utc'],
    "next_update_utc": alert_data['next_update_utc'],
    "states": states_dict,
}
with codecs.open(filepath, 'w', encoding='UTF-8') as f:
    f.write(json.dumps(output_dict, indent=4))
