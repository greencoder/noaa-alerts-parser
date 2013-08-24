import os
import json
import codecs
import datetime
import pytz

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

regions = {
    'Northeast': ['ME','NH','VT','MA','RI','CT'],
    'Mid-Atlantic': ['NY','PA','MD','DE','DC','NJ','WV','VA'],
    'Southeast': ['NC','SC','TN','AR','LA','MS','FL','GA','AL'],
    'Midwest': ['WI','MI','IL','IN','OH','MO','ND','SD','NE','KS','MN','IA','KY'],
    'Southwest': ['OK','TX','NM','AZ','UT','CO'],
    'West': ['CA','NV'],
    'Northwest': ['WY','MT','ID','OR','WA'],
    'Pacific': ['AK','HI'],
}

states_dict = {}
for region in regions.keys():
    for state in regions[region]:
        if states_dict.has_key(state):
            print "here", state
        states_dict[state] = region

json_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
f = codecs.open(json_filepath, 'r', 'utf-8')
contents = f.read()
f.close()
alert_data = json.loads(contents)

alerts = alert_data['alerts']

severities = {}
states = {}
events = {}
regions = {}

for alert in alerts:
    
    severity = alert['severity']
    event = alert['event']

    for state in set([c['state'] for c in alert['counties']]):
        if state in states.keys():
            states[state] += 1
        else:
            states[state] = 1
    
    if event in events.keys():
        events[event] += 1
    else:
        events[event] = 1

    if severity in severities.keys():
        severities[severity] += 1
    else:
        severities[severity] = 1

for state in states.keys():
    region = states_dict[state]
    alert_count = states[state]
    if regions.has_key(region):
        regions[region] += alert_count
    else:
        regions[region] = alert_count

output_dict = {
    'updated': datetime.datetime.now(pytz.utc).isoformat(),
    'count': len(alerts), 
    'events': events, 
    'severities': severities, 
    'states': states,
    'regions': regions,
}

output_json = json.dumps(output_dict, indent=4)

output_filepath = os.path.join(CUR_DIR, 'output/counts.json')
f = codecs.open(output_filepath, 'w', 'utf-8')
f.write(output_json)
f.close()
