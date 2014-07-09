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
from lxml import etree as ET
from dateutil import parser
from shapely.geometry import box, Polygon, Point

NOAA_URL = "http://alerts.weather.gov/cap/us.php?x=1"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
CAP_NS = "{urn:oasis:names:tc:emergency:cap:1.1}"

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(CUR_DIR, 'data')
LOGS_DIR = os.path.join(CUR_DIR, 'output/logs/')
JSON_DIR = os.path.join(CUR_DIR, 'output/json/')

if __name__ == "__main__":

    # Make sure the output directories exist
    for dir_name in ['json', 'json/detail', 'logs']:
        if not os.path.exists(os.path.join(CUR_DIR, 'output/%s' % dir_name)):
            os.makedirs(os.path.join(CUR_DIR, 'output/%s' % dir_name))

    # Load states and counties
    states_filepath = os.path.join(DATA_DIR, 'states.json')
    f = codecs.open(states_filepath, 'r', 'utf-8')
    states_list = json.loads(f.read())
    f.close()

    counties_filepath = os.path.join(DATA_DIR, 'counties.json')
    f = codecs.open(counties_filepath, 'r', 'utf-8')
    counties_list = json.loads(f.read())
    f.close()

    # Load UGC Zones
    ugc_filepath = os.path.join(DATA_DIR, 'ugc_zones.json')
    f = codecs.open(ugc_filepath, 'r', 'utf-8')
    ugc_zones_list = json.loads(f.read())
    f.close()

    states_dict = {}
    for state in states_list:
        states_dict[state['fips']] = state

    counties_dict = {}
    for county in counties_list:
        counties_dict[county['fips']] = county

    state_abbrs_dict = {}
    for state in states_list:
        state_abbrs_dict[state['abbr']] = state

    ugc_zones_dict = {}
    for ugc in ugc_zones_list:
        zone = ugc['state'] + "Z" + ugc['zone']
        ugc_zones_dict[zone] = ugc

    # Class Methods
    def log(message):
        now_utc = datetime.datetime.now(pytz.utc)
        log_filepath = os.path.join(LOGS_DIR, 'log.txt')
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\t%s\n" % (now_utc, message))
        f.close()

    def log_missing_fips(fips_code):
        log_filepath = os.path.join(LOGS_DIR, 'missing_fips.txt')
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\n" % fips_code)
        f.close()

    def log_missing_ugc(ugc_code):
        log_filepath = os.path.join(LOGS_DIR, 'missing_ugc.txt')
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\n" % ugc_code)
        f.close()

    def log_error(message):
        now_utc = datetime.datetime.now(pytz.utc)
        log_filepath = os.path.join(LOGS_DIR, 'errors.txt')
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\t%s\n" % (now_utc, message))
        f.close()

    def log_special_statement(message):
        now_utc = datetime.datetime.now(pytz.utc)
        log_filepath = os.path.join(LOGS_DIR, 'missing_sws.txt')
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\t%s\n\n" % (now_utc, message))
        f.close()

    def save_bad_xml(file_contents):
        now_utc = datetime.datetime.now(pytz.utc)
        time_str = now_utc.strftime('%Y%m%d_%H%M%S')
        log_filepath = os.path.join(LOGS_DIR, 'bad_alert_%s.xml' % time_str)
        f = codecs.open(log_filepath, 'a', 'utf-8')
        f.write("%s\t%s\n\n" % (now_utc, message))
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

    # Grab the URL
    f = urllib2.urlopen(NOAA_URL, timeout=5)
    request_data = f.read()
    
    try:
        tree = ET.fromstring(request_data)
        entries_list = tree.findall(ATOM_NS + 'entry')
        log("Requesting alerts feed. %d entries found." % len(entries_list))
    except lxml.etree.XMLSyntaxError:
        log_error("Bad XML Received. Aborting.")
        log_bad_xml(request_data)
        sys.exit()

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

        # Some events are not weather related so we don't show them
        skippable_events = (
           '911 telephone outage emergency',
           '911 telephone outage',
           'child abduction emergency',
           'local area emergency',
           'test',
        )

        # Create a list of events to skip.
        if alert['event'].lower() in skippable_events:
            log("Skipping event: %s" % alert['event'])
            continue

        # If the event is 'Special Weather Statement', try to figure out what it's
        # pertaining to
        if alert['event'] == "Special Weather Statement":

            # We don't know what kind of capitalization might be used
            summary = alert['summary'].lower()

            if "tornado" in summary:
                alert['event'] = 'Special Weather Statement (Tornado)'
            elif "hail" in summary:
                alert['event'] = 'Special Weather Statement (Hail)'
            elif "thunderstorm" in summary:
                alert['event'] = 'Special Weather Statement (Thunderstorms)'
            elif "snow" in summary:
                alert['event'] = 'Special Weather Statement (Snow)'
            elif "flooding" in summary:
                alert['event'] = 'Special Weather Statement (Flooding)'
            elif 'water level' in summary:
                alert['event'] = 'Special Weather Statement (Flooding)'
            else:
                log_special_statement(summary)

        # Create a unique hash from the ID
        h = hashlib.new('ripemd160')
        h.update(alert['id'])
        alert['uuid'] = h.hexdigest()

        # Polygons come formatted as a string, but we transform it into
        # a valid GeoJSON coordinate array. Valid means we have to turn around
        # the coordinates to lng,lat
        if alert['polygon']:
            verticies_list = []
            for item in [v.split(",") for v in alert['polygon'].split(" ")]:
                verticies_list.append([float(item[1]), float(item[0])])
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
        alert['ugc_zones_list'] = []
        alert['counties_list'] = []
        alert['states_list'] = []

        # Find the 'geocode' node and check the valueName elements
        # for UGC or FIPS6
        for item in entry_el.findall(CAP_NS + 'geocode'):
            for value_name_el in item.findall(ATOM_NS + 'valueName'):
                if value_name_el.text == "FIPS6":
                    value_el = value_name_el.getnext()
                    if value_el is not None and value_el.text:
                        alert['fips_list'].extend(value_el.text.split(" "))
                elif value_name_el.text == "UGC":
                    value_el = value_name_el.getnext()
                    if value_el is not None and value_el.text:
                        # We are only interested in zones right now
                        if value_el.text[2:3] == "Z":
                            alert['ugc_zones_list'].extend(value_el.text.split(" "))

        # If there is a polygon in the alert, it might cover a county
        # that was not included in the FIPS list. We will turn the string
        # into a Shapely polygon, then compare it against every county to
        # find matches.

        # Sometimes the polygon has bad values, so we need to do some sanity
        # checking on the values. If it contains a value of "0" or "-0", exit.
        # If the distance between any two verticies is greater than 25 units,
        # exit.

        if alert['polygon']:

            verticies_list = []
            found_error = False

            for item in [v.split(",") for v in alert['polygon'].split(" ")]:
                # Make sure bad values aren't present
                if '0' in item or '-0' in item:
                    log_error("A '0' or '-0' was found in polygon %s" % alert['polygon'])
                    found_error = True
                    break
                else:
                    # NWS coordinates come in lat,long - we need long,lat
                    verticies_list.append((float(item[1]), float(item[0])))

            for point in verticies_list:
                first_point = Point(verticies_list[0][0],verticies_list[0][1])
                cur_point = Point(point[0], point[1])
                distance = first_point.distance(cur_point)
                if distance > 25:
                    log_Error("Distance between points was %f in polygon (%s)" % (distance, alert['polygon']))
                    found_error = True

            # If we got this far and don't have an error, we can safely compare
            # polygons
            if not found_error:
                alert_polygon = Polygon(verticies_list)
                for county in counties_list:
                    bbox = county['bbox']
                    county_polygon = box(bbox[0], bbox[1], bbox[2], bbox[3])
                    if county_polygon.intersects(alert_polygon):
                        alert['fips_list'].append(county['fips'])

        # Loop through all the ugc zones and get the associated counties
        for ugc_code in alert['ugc_zones_list']:
            try:
                ugc_zone = ugc_zones_dict[ugc_code]
                for fips in ugc_zone['fips']:
                    if fips not in alert['fips_list']:
                        alert['fips_list'].append(fips)
            except KeyError:
                log("Could not find UGC Zone Code: %s" % ugc_code)
                log_missing_ugc(ugc_code)

        # Make sure there are no duplicates
        alert['fips_list'] = list(set(alert['fips_list']))
        alert['ugc_zones_list'] = list(set(alert['ugc_zones_list']))

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
                abbr = county['state']
                state = state_abbrs_dict[abbr]
                if state not in alert['states_list']:
                    alert['states_list'].append(state)

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
                    alert['region'] = old_alert['region']
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

            # We get the region from the name that is in parenthesis in the sender value
            # e.g. "NWS Reno (Western Nevada)" We also have to make sure the first character is
            # upper cased.
            start_index = alert['sender'].find("(")
            end_index = alert['sender'].find(")")
            if (start_index > 0) and (end_index > 0):
                region = alert['sender'][start_index+1:end_index]
                alert['region'] = region[0].upper() + region[1:]
            else:
                alert['region'] = "Unknown"

            # If the region is "Storm Prediction Center - Norman, Oklahoma", that doesn't
            # really describe the region that is affected, so change it.
            if alert['region'] == "Storm Prediction Center - Norman, Oklahoma":
                if len(alert['states_list']) > 0:
                    alert['region'] = ", ".join([state['name'] for state in alert['states_list']])
                else:
                    alert['region'] = "Unknown"

        ### Final Sanitization Step - Clean up outliers ###

        if len(alert['severity']) == 0 or not alert['severity']:
            alert['severity'] = "Unspecified"

        alerts_list.append(alert)

# Write out the alerts
# Prepare to render the alerts
env = Environment()
env.loader = FileSystemLoader(os.path.join(CUR_DIR, 'templates'))

def jinja_escape_js(val):
    return json.dumps(str(val))

env.filters['escape_json'] = jinja_escape_js
template_full = env.get_template('alerts_full.tpl.json')
template_lite = env.get_template('alerts.tpl.json')
template_detail = env.get_template('alert_detail.tpl.json')
template_count = env.get_template('counts.tpl.json')

now = datetime.datetime.now(pytz.utc).astimezone(pytz.utc)
now_utc = parser.parse(now.strftime("%Y-%m-%d %H:%M:%S %Z"))
next_update_utc = now_utc + datetime.timedelta(minutes=5)

# Write out the full file
output_full_filepath = os.path.join(CUR_DIR, 'output/alerts.json')
output_full = template_full.render(alerts=alerts_list, written_at_utc=now_utc,
    next_update_utc=next_update_utc)
with codecs.open(output_full_filepath, 'w', 'utf-8') as f:
    f.write(output_full)

# Write out the regular file
output_lite_filepath = os.path.join(JSON_DIR, 'alerts.json')
output_lite = template_lite.render(alerts=alerts_list, written_at_utc=now_utc,
    next_update_utc=next_update_utc)
with codecs.open(output_lite_filepath, 'w', 'utf-8') as f:
    f.write(output_lite)

# Write out the count file
count_filepath = os.path.join(JSON_DIR, 'counts.json')
count_output = template_count.render(alerts=alerts_list, written_at_utc=now_utc,
    next_update_utc=next_update_utc)
with codecs.open(count_filepath, 'w', 'utf-8') as f:
    f.write(count_output)

# Make sure output detail directory exists
if not os.path.exists(os.path.join(CUR_DIR, 'output/detail')):
    os.makedirs(os.path.join(CUR_DIR, 'output/detail'))

# Loop through all the alerts and write out individual detail pages
for alert in alerts_list:
    output_detail = template_detail.render(alert=alert, written_at_utc=now_utc)
    output_detail_filepath = os.path.join(JSON_DIR, 'detail/%s.json' % alert['uuid'])
    with codecs.open(output_detail_filepath, 'w', 'utf-8') as f:
        f.write(output_detail)
