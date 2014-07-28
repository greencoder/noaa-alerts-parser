import datetime
import dateutil.parser
import jinja2
import json
import os
import pytz
import shapely.geometry
import sys
import time
import urllib2

from lib.parser import Parser

if __name__ == "__main__":

    CUR_DIR = os.path.dirname(os.path.realpath(__file__))

    # Namespaces for XML
    ATOM_NS = "{http://www.w3.org/2005/Atom}"
    CAP_NS = "{urn:oasis:names:tc:emergency:cap:1.1}"

    # Instantiate the parser
    parser = Parser(CUR_DIR)

    # Try to load the previous alerts
    previous_alerts_filepath = os.path.join(parser.output_dir, 'alerts.json')
    if os.path.exists(previous_alerts_filepath):
        previous_alerts_dict = parser.load_json(previous_alerts_filepath)
        parser.previous_alerts_list = previous_alerts_dict['alerts']
    else:
        parser.previous_alerts_list = []

    # Parse the XML
    try:
        noaa_url = "http://alerts.weather.gov/cap/us.php?x=1"
        f = urllib2.urlopen(noaa_url, timeout=10)
        request_data = f.read()
        tree = parser.load_xml_from_url_contents(request_data)
        entries_list = tree.findall(ATOM_NS + 'entry')
        parser.log("Requesting alerts feed. %d entries found." % len(entries_list))
    except Parser.XMLError:
        parser.log_error("Bad XML Received. Aborting.")
        parser.save_bad_xml(request_data)
        sys.exit("Bad XML")

    # We will keep all the alerts we parse in a list
    alerts_list = []

    # Loop through all the 'entry' nodes we found
    for entry_el in entries_list[0:2]:

        # Alert is just a lightweight object wrapper to keep the code clean (cleaner syntax
        # than using a dictionary)
        alert = Parser.Alert()

        # Find the unique ID and create a unique identifier
        alert.id = parser.get_element_text(entry_el, ATOM_NS + 'id')
        alert.uuid = parser.create_unique_identifier(alert.id)

        # Find the updated time (we need this to look for a previous alert)
        updated_dtstr = parser.get_element_text(entry_el, ATOM_NS + 'updated')
        alert.updated = dateutil.parser.parse(updated_dtstr).astimezone(pytz.utc).isoformat()
        
        # Before we call out to NOAA for additional info, see if we already have this information
        # from the last time we saved the file. This can save us lots of URL requests and time.
        previous_alert_dict = parser.find_previous_alert_by_uuid(alert.uuid, alert.updated)

        # If it was found, just use the last one
        if previous_alert_dict:
            parser.set_properties_from_dict(alert, previous_alert_dict)
            alerts_list.append(alert)
            continue

        # If this alert was not found in the output of our earlier runs, then we need to parse it
        if not previous_alert_dict:

            alert.updated_datestr = parser.get_element_text(entry_el, ATOM_NS + 'updated')
            alert.published_datestr = parser.get_element_text(entry_el, ATOM_NS + 'published')
            alert.effective_datestr = parser.get_element_text(entry_el, CAP_NS + 'effective')
            alert.expires_datestr = parser.get_element_text(entry_el, CAP_NS + 'expires')
            alert.author = parser.get_element_text(entry_el, ATOM_NS + 'author/' + ATOM_NS + 'name')
            alert.title = parser.get_element_text(entry_el, ATOM_NS + 'title')
            alert.link = parser.get_element_attr(entry_el, ATOM_NS + 'link', 'href')
            alert.summary = parser.get_element_text(entry_el, ATOM_NS + 'summary')
            alert.status = parser.get_element_text(entry_el, CAP_NS + 'status')
            alert.message_type = parser.get_element_text(entry_el, CAP_NS + 'msgType')
            alert.event = parser.get_element_text(entry_el, CAP_NS + 'event')
            alert.category = parser.get_element_text(entry_el, CAP_NS + 'category')
            alert.urgency = parser.get_element_text(entry_el, CAP_NS + 'urgency')
            alert.severity = parser.get_element_text(entry_el, CAP_NS + 'severity')
            alert.certainty = parser.get_element_text(entry_el, CAP_NS + 'certainty')
            alert.area_description = parser.get_element_text(entry_el, CAP_NS + 'areaDesc')
            alert.polygon_string = parser.get_element_text(entry_el, CAP_NS + 'polygon')

            # See if the event is something we want to skip
            if alert.event.lower() in parser.skippable_events_list:
                parser.log("Skipping event: %s" % alert.event)
                continue

            # If the alert severity is missing, apply a default value
            if len(alert.severity) == 0 or alert.severity == "":
                alert.severity = "Unspecified"

            # Try to find the timezone title
            alert.timezone = parser.get_timezone_from_title(alert.title)

            # Convert the date strings to dates
            alert.published_local = dateutil.parser.parse(alert.published_datestr)
            alert.expires_local = dateutil.parser.parse(alert.expires_datestr)
            alert.updated_local = dateutil.parser.parse(alert.updated_datestr)
            alert.effective_local = dateutil.parser.parse(alert.effective_datestr)

            # Convert the dates to UTC strings in ISO format
            alert.published = alert.published_local.astimezone(pytz.utc).isoformat()
            alert.expires = alert.expires_local.astimezone(pytz.utc).isoformat()
            alert.updated = alert.updated_local.astimezone(pytz.utc).isoformat()
            alert.effective = alert.effective_local.astimezone(pytz.utc).isoformat()

            # Load and parse the CAP XML
            try:
                parser.log("Requesting CAP URL for UUID: %s" % alert.uuid)
                parser.log("URL: %s" % alert.link)
                f = urllib2.urlopen(alert.link, timeout=10)
                request_data = f.read()
                cap_tree = parser.load_xml_from_url_contents(request_data)
                # Pause for a half second to keep from overwhelming NOAA's servers
                time.sleep(0.5)
            except Parser.XMLError:
                parser.log_error("Bad CAP XML Received. Skipping.")
                parser.save_bad_xml(request_data)
                cap_tree = ET.Element('')

            # Get the extended elements we need
            alert.sender = parser.get_element_text(cap_tree, CAP_NS + 'info/' + CAP_NS + 'senderName')
            alert.instruction = parser.get_element_text(cap_tree, CAP_NS + 'info/' + CAP_NS + 'instruction')
            alert.description = parser.get_element_text(cap_tree, CAP_NS + 'info/' + CAP_NS + 'description')
            alert.note = parser.get_element_text(cap_tree, CAP_NS + 'note')

            # If the sender is blank, label it "Unknown"
            if len(alert.sender) == 0 or alert.sender == "":
                parser.log("Missing Sender for Alert %s" % alert.uuid)
                alert.sender = "Unknown"

            # We try to get the region name from the sender value
            alert.region = parser.get_region_from_sender(alert.sender)

            # If the alert contains a polygon string, we need to turn it into a valid
            # cooridnate array by flipping the verticies from lat/long to long/lat
            if alert.polygon_string:
                try:
                    alert.polygon = parser.create_polygon_coords(alert.polygon_string)
                except Parser.GeometryError:
                    alert.polygon = []
            else:
                alert.polygon = []

            # Find all the counties for this alert
            alert.county_fips_list = []
            for item in entry_el.findall(CAP_NS + 'geocode'):
                for value_name_el in item.findall(ATOM_NS + 'valueName'):
                    if value_name_el.text == "FIPS6":
                        value_el = value_name_el.getnext()
                        if value_el is not None and value_el.text:
                            codes = value_el.text.split(" ")
                            alert.county_fips_list.extend(codes)

            # Find all the UGC zones and counties for this alert
            alert.ugc_codes_list = []
            for item in entry_el.findall(CAP_NS + 'geocode'):
                for value_name_el in item.findall(ATOM_NS + 'valueName'):
                    if value_name_el.text == "UGC":
                        value_el = value_name_el.getnext()
                        if value_el is not None and value_el.text:
                            codes = value_el.text.split(" ")
                            alert.ugc_codes_list.extend(codes)

            # The ugc_codes_list will contain both zone and county codes
            additional_counties = parser.get_county_fips_for_ugc_codes(alert.ugc_codes_list)
            alert.county_fips_list.extend(additional_counties)

            # Make sure the lists are unique
            alert.county_fips_list = list(set(alert.county_fips_list))
            alert.ugc_codes_list = list(set(alert.ugc_codes_list))

            # Find the counties and states associated with the fips code list
            alert.counties = parser.get_counties_by_fips(alert.county_fips_list)
            alert.states = parser.get_states_by_county_fips(alert.county_fips_list)
            alert.ugc_zones = parser.get_zones_by_code(alert.ugc_codes_list)

            # Find the states associated with the UGC Zones and append them
            extra_states = parser.get_states_by_ugc_codes(alert.ugc_codes_list)
            alert.states.extend(extra_states)

            # Make the lists of counties, states, and zones unique
            alert.counties = {c['fips']:c for c in alert.counties}.values()
            alert.ugc_zones = {z['code']:z for z in alert.ugc_zones}.values()
            alert.states = list(set([s['name'] for s in alert.states]))

            # If we cannot find a region, use the list of states
            if alert.region == None:
                if len(alert.states) > 0:
                    alert.region = ", ".join(alert.states)
                else:
                    alert.region = "Unknown"

            # If the alert event is "Special Weather Statement" or "Severe Weather Statement", 
            # see if we can identify elements in the description to make it more clear. This will
            # become a new element we call "event_title"
            if alert.event == "Special Weather Statement" or alert.event == "Severe Weather Statement":
                alert.event_title = parser.refine_weather_statement(alert.description)
            else:
                # If it's not "Special Weather Statement", just use the event type as the event title
                alert.event_title = alert.event

            # We are done with this alert, so append it to the list
            alerts_list.append(alert)

    ### File Writing ###

    # Prepare the template engine 
    env = jinja2.Environment()
    env.loader = jinja2.FileSystemLoader(os.path.join(CUR_DIR, 'templates'))

    # Add a custom filter to the template engine
    def jinja_escape_js(val):
        if type(val) == str or type(val) == unicode:
            return json.dumps(str(val))
        else:
            return json.dumps(val)

    env.filters['escape_json'] = jinja_escape_js

    # Load the template files
    template_full = env.get_template('alerts_full.tpl.json')
    template_lite = env.get_template('alerts.tpl.json')
    template_detail = env.get_template('alert_detail.tpl.json')
    template_count = env.get_template('counts.tpl.json')

    # Prepare the values we will need for the templates
    dt_now = datetime.datetime.now(pytz.utc).astimezone(pytz.utc)
    now = dt_now.isoformat()
    next_update = (dt_now + datetime.timedelta(minutes=5)).isoformat()

    # Write out the full file
    filepath_full = os.path.join(parser.output_dir, 'alerts.json')
    output_full = template_full.render(alerts=alerts_list, created=now, next_update=next_update)
    parser.write_contents_to_filepath(output_full, filepath_full)

    # Write out the regular file
    filepath_lite = os.path.join(parser.json_dir, 'alerts.json')
    output_lite = template_lite.render(alerts=alerts_list, created=now, next_update=next_update)
    parser.write_contents_to_filepath(output_lite, filepath_lite)

    # Write out the count file
    filepath_count = os.path.join(parser.json_dir, 'counts.json')
    output_count = template_count.render(alerts=alerts_list, created=now, next_update=next_update)
    parser.write_contents_to_filepath(output_count, filepath_count)

    # Loop through all the alerts and write out individual detail pages
    for alert in alerts_list:
        output_detail = template_detail.render(alert=alert, created=now)
        filepath_detail = os.path.join(parser.detail_dir, '%s.json' % alert.uuid)
        parser.write_contents_to_filepath(output_detail, filepath_detail)