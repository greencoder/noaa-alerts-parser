import os
import sys
import json
import codecs
import time
import datetime
import random
import pytz
from operator import itemgetter

from jinja2 import Template, Environment, FileSystemLoader

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

# Load up the states data
json_filepath = os.path.join(CUR_DIR, 'data/states.json')
f = codecs.open(json_filepath, 'r', 'utf-8')
states_contents = f.read()
f.close()

states = {}
for state_dict in json.loads(states_contents):
    states[state_dict['abbr']] = state_dict['name']

# Now load the alerts data
json_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
f = codecs.open(json_filepath, 'r', 'utf-8')
alerts_contents = f.read()
f.close()

alert_data = json.loads(alerts_contents)
alerts = alert_data['alerts']

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

# Prepare to render the alerts
env = Environment()
env.loader = FileSystemLoader(os.path.join(CUR_DIR, 'templates'))

now_utc = datetime.datetime.now(pytz.utc).astimezone(pytz.utc)
now_utc_ts = int(time.mktime(datetime.datetime.now().utctimetuple()))

template = env.get_template('states.tpl.html')
output = template.render(states=alerts_by_state, written_at_utc=now_utc, 
    written_at_utc_ts=now_utc_ts)

output_filepath = os.path.join(CUR_DIR, 'output/states.html')
f = codecs.open(output_filepath, 'w', 'utf-8')
f.write(output)
f.close()

