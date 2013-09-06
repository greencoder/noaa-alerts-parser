import os
import sys
import json
import codecs
import time
import datetime
import pytz
from operator import itemgetter

from jinja2 import Template, Environment, FileSystemLoader

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

json_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
f = codecs.open(json_filepath, 'r', 'utf-8')
contents = f.read()
f.close()

alert_data = json.loads(contents)
alerts = alert_data['alerts']

# Prepare to render the alerts
env = Environment()
env.loader = FileSystemLoader(os.path.join(CUR_DIR, 'templates'))

now_utc = datetime.datetime.now(pytz.utc).astimezone(pytz.utc)
now_utc_ts = int(time.mktime(datetime.datetime.now().utctimetuple()))

template = env.get_template('detail.tpl.html')
output = template.render(alerts=alerts, written_at_utc=now_utc, 
    written_at_utc_ts=now_utc_ts)

output_filepath = os.path.join(CUR_DIR, 'output/detail.html')
f = codecs.open(output_filepath, 'w', 'utf-8')
f.write(output)
f.close()

