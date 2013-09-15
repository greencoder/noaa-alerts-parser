import codecs
import datetime
import time
import pytz
import urllib2
import json
import os
import hashlib
import sys

from jinja2 import Template, Environment, FileSystemLoader
from xml.etree import ElementTree as ET
from dateutil import parser
from shapely.geometry import box, Polygon

NOAA_URL = "http://alerts.weather.gov/cap/us.php?x=1"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
CAP_NS = "{urn:oasis:names:tc:emergency:cap:1.1}"

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":

    # Load states and counties
    states_filepath = os.path.join(CUR_DIR, 'data/states.json')
    f = codecs.open(states_filepath, 'r', 'utf-8')
    contents = f.read()
    states_list = json.loads(contents)
    f.close()

    counties_filepath = os.path.join(CUR_DIR, 'data/counties.json')
    f = codecs.open(counties_filepath, 'r', 'utf-8')
    contents = f.read()
    counties_list = json.loads(contents)
    f.close()
    
    states_dict = {}
    for state in states_list:
        states_dict[state['fips']] = state

    counties_dict = {}
    for county in counties_list:
        counties_dict[county['fips']] = county

    def log(message):
        now_utc = datetime.datetime.now(pytz.utc)
        log_filepath = os.path.join(CUR_DIR, 'output/log.txt')
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\t%s\n" % (now_utc, message))
        f.close()

    def log_missing_fips(fips_code):
        log_filepath = os.path.join(CUR_DIR, 'output/missing_fips.txt')
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\n" % fips_code)
        f.close()

    def get_element_text(element, name, default_value=''):
        el = element.find(name)
        if el is not None and el.text:
            return el.text.strip()
        else:
            return default_value

    def get_element_attr(element, name, attr_name, default_value=''):
        el = element.find(name)
        if el is not None and el.attrib.has_key(attr_name):
            return el.attrib[attr_name].strip()
        else:
            return default_value

    # Try to load the last run of the alerts so we can skip having to 
    # call out for every URL when we don't have to.
    try:
        json_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
        f = codecs.open(json_filepath, 'r', 'utf-8')
        contents = f.read()
        f.close()
        previous_alerts_list = json.loads(contents)['alerts']
    except IOError:
        previous_alerts_list = []

    # Load up the new alerts
    alerts_list = []

    f = urllib2.urlopen(NOAA_URL, timeout=5)
    request_data = f.read()
    tree = ET.fromstring(request_data)
    entries_list = tree.findall(ATOM_NS + 'entry')
    
    log("Requesting alerts feed. %d entries found." % len(entries_list))

    for entry_el in entries_list:

        alert = {}

        alert['id'] = get_element_text(entry_el, ATOM_NS + 'id')
        alert['updated_datestr'] = get_element_text(entry_el, ATOM_NS + 'updated')
        alert['published_datestr'] = get_element_text(entry_el, ATOM_NS + 'published')
        alert['effective_datestr'] = get_element_text(entry_el, CAP_NS + 'effective')
        alert['expires_datestr'] = get_element_text(entry_el, CAP_NS + 'expires')
        alert['author'] = get_element_text(entry_el, ATOM_NS + 'author/' + ATOM_NS + 'name')
        alert['title'] = get_element_text(entry_el, ATOM_NS + 'title')
        alert['link'] = get_element_attr(entry_el, ATOM_NS + 'link', 'href')
        alert['summary'] = get_element_text(entry_el, ATOM_NS + 'summary')
        alert['status'] = get_element_text(entry_el, CAP_NS + 'status')
        alert['msg_type'] = get_element_text(entry_el, CAP_NS + 'msgType')
        alert['event'] = get_element_text(entry_el, CAP_NS + 'event')
        alert['category'] = get_element_text(entry_el, CAP_NS + 'category')
        alert['urgency'] = get_element_text(entry_el, CAP_NS + 'urgency')
        alert['severity'] = get_element_text(entry_el, CAP_NS + 'severity')
        alert['certainty'] = get_element_text(entry_el, CAP_NS + 'certainty')
        alert['area_desc'] = get_element_text(entry_el, CAP_NS + 'areaDesc')
        alert['polygon'] = get_element_text(entry_el, CAP_NS + 'polygon')

        # Create a unique hash from the ID
        h = hashlib.new('ripemd160')
        h.update(alert['id'])
        alert['uuid'] = h.hexdigest()

        # Polygons come formatted as a string, but we transform it into 
        # a valid GeoJSON coordinate array.
        if alert['polygon']:
            verticies_list = []
            for item in [v.split(",") for v in alert['polygon'].split(" ")]:
                verticies_list.append([float(item[0]), float(item[1])])
            alert['formatted_polygon'] = verticies_list
        else:
            alert['formatted_polygon'] = []

        # Parse the title to get the local timezone name. This is a little
        # hacky-hack, but it's the only way of knowing for sure what the 
        # timezone was without some really nasty work.
        if "until" in alert['title']:
            local_tz_start = alert['title'].index(' until') - 4
            local_tz_end = alert['title'].index('until')
            alert['timezone_abbr'] = alert['title'][local_tz_start:local_tz_end].strip()
        elif "by NWS" in alert['title']:
            local_tz_start = alert['title'].index(' by NWS') - 4
            local_tz_end = alert['title'].index('by NWS')
            alert['timezone_abbr'] = alert['title'][local_tz_start:local_tz_end].strip()
        else:
            alert['timezone_abbr'] = ""

        # Convert the date strings to dates
        alert['published'] = parser.parse(alert['published_datestr'])
        alert['expires'] = parser.parse(alert['expires_datestr'])
        alert['updated'] = parser.parse(alert['updated_datestr'])
        alert['effective'] = parser.parse(alert['effective_datestr'])
        
        # Convert the dates to UTC
        alert['published_utc'] = alert['published'].astimezone(pytz.utc)
        alert['expires_utc'] = alert['expires'].astimezone(pytz.utc)
        alert['updated_utc'] = alert['updated'].astimezone(pytz.utc)
        alert['effective_utc'] = alert['effective'].astimezone(pytz.utc)

        alert['fips_list'] = []
        alert['ugc_list'] = []
        alert['counties_list'] = []
        
        # Look for the 'geocode' element and find the FIPS and UGCs
        for item in entry_el.findall(CAP_NS + 'geocode'):
            item_val = item.find(ATOM_NS + 'value').text
            item_type = item.find(ATOM_NS + 'valueName').text
            if item_type == "FIPS6":
                alert['fips_list'].extend(item_val.split(" "))
            elif item_type == "UGC":
                alert['ugc_list'].extend(item_val.split(" "))

        # If there is a polygon in the alert, it might cover a county
        # that was not included in the FIPS list. We will turn the string 
        # into a Shapely polygon, then compare it against every county to 
        # find matches.
        if alert['polygon']:
            verticies_list = []
            for item in [v.split(",") for v in alert['polygon'].split(" ")]:
                # NWS coordinates come in lat,long - we need long,lat
                verticies_list.append((float(item[1]), float(item[0])))
            alert_polygon = Polygon(verticies_list)
            for county in counties_list:
                bbox = county['bbox']
                county_polygon = box(bbox[0], bbox[1], bbox[2], bbox[3])
                if county_polygon.intersects(alert_polygon):
                    alert['fips_list'].append(county['fips'])

        # Make sure there are no duplicates
        alert['fips_list'] = list(set(alert['fips_list']))
        alert['ugc_list'] = list(set(alert['ugc_list']))

        # Loop through all fips and get the associated counties
        for fips in alert['fips_list']:
            # For some reason, 'ant' shows up occasionally in the list 
            # of county FIPS codes. Ignore it.
            if fips == 'ant':
                log("FIPS6 list includes 'ant' entry (%s). Skipping." % ", ".join(alert['fips_list']))
                continue
            try:
                county = counties_dict[fips]
                if county not in alert['counties_list']:
                    alert['counties_list'].append(county)
            except KeyError:
                log("Could Not Find County FIPS: %s" % fips)
                log_missing_fips(fips)

        # Before we call out to NOAA for additional info, see if we already have this information
        # from the last time we saved the file. This can save us lots of URL requests and time.
        matched_last_record = False

        for old_alert in previous_alerts_list:
            if old_alert['uuid'] == alert['uuid']:
                if old_alert['updated'] == alert['updated_utc'].isoformat():
                    matched_last_record = True
                    # If it hasn't been updated, use these values
                    alert['sender'] = old_alert['sender']
                    alert['instruction'] = old_alert['instruction']
                    alert['description'] = old_alert['description']
                    alert['note'] = old_alert['note']
                break

        # If we didn't find the current alert from the data in our last run, we need 
        # to call the CAP URL and get it.
        if not matched_last_record:
            log("Requesting CAP URL for UUID: %s" % alert['uuid'])
            try:
                f = urllib2.urlopen(alert['link'], timeout=10)
                request_data = f.read()
                cap_tree = ET.fromstring(request_data)
            except urllib2.URLError, error:
                log("Error opening CAP URL. %s" % error)
                # We don't want to stop dead, so create an empty XML element
                # so our next few lines of code will execute and return blank.
                cap_tree = ET.Element('')

            alert['sender'] = get_element_text(cap_tree, CAP_NS + 'info/' + CAP_NS + 'senderName')
            alert['instruction'] = get_element_text(cap_tree, CAP_NS + 'info/' + CAP_NS + 'instruction')
            alert['description'] = get_element_text(cap_tree, CAP_NS + 'info/' + CAP_NS + 'description')
            alert['note'] = get_element_text(cap_tree, CAP_NS + 'note')

        ### Final Sanitization Step ###

        if alert['severity'] == "":
            alert['severity'] == "Unspecified"            

        alerts_list.append(alert)

# Write out the alerts
# Prepare to render the alerts
env = Environment()
env.loader = FileSystemLoader(os.path.join(CUR_DIR, 'templates'))

def jinja_escape_js(val):
    return json.dumps(str(val))

env.filters['escape_json'] = jinja_escape_js
template = env.get_template('alerts.tpl.json')

now_utc = datetime.datetime.now(pytz.utc).astimezone(pytz.utc)
now_utc_ts = int(time.mktime(datetime.datetime.now().utctimetuple()))

output = template.render(alerts=alerts_list, written_at_utc=now_utc, 
    written_at_utc_ts=now_utc_ts)

output_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
f = codecs.open(output_filepath, 'w', 'utf-8')
f.write(output)
f.close()
