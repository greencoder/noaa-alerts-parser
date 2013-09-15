import os
import json
import codecs
import datetime
import pytz

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":

    # Load master list of metadata
    metadata_filepath = os.path.join(CUR_DIR, 'data/metadata.json')

    if os.path.exists(metadata_filepath):
        f = codecs.open(metadata_filepath, 'r', 'utf-8')
        contents = f.read()
        data = json.loads(contents)
        events_list = data['events']
        severities_list = data['severities']
        f.close()
    else:
        events_list = []
        severities_list = []

    # Open up the alerts list
    json_filepath = os.path.join(CUR_DIR, 'output/alerts.json')

    f = codecs.open(json_filepath, 'r', 'utf-8')
    contents = f.read()
    f.close()

    alert_data = json.loads(contents)
    alerts = alert_data['alerts']

    for alert in alerts:
        
        severity = alert['severity']
        event = alert['event']
        
        if severity not in severities_list:
            if severity not in ("Unspecified", ""):
                severities_list.append(severity)
        
        if event not in events_list:
            if event not in ('Test',):
                events_list.append(event)

# Sort and write out the metadata file
events_list.sort()
severities_list.sort()
output_dict = {
    'updated': datetime.datetime.now(pytz.utc).isoformat(),
    'events': events_list, 
    'severities': severities_list,
}

metadata_filepath = os.path.join(CUR_DIR, 'data/metadata.json')
f = codecs.open(metadata_filepath, 'w', 'utf-8')
f.write(json.dumps(output_dict, indent=4))
f.close()
