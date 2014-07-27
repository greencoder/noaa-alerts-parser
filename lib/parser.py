import codecs
import datetime
import hashlib
import json
import lxml
import os
import pytz
import shapely.geometry
import sys
import urllib2

from lxml import etree as ET

class Parser():

    def __init__(self, root_dir):

        self.data_dir = os.path.join(root_dir, 'data')
        self.output_dir = os.path.join(root_dir, 'output')
        self.logs_dir = os.path.join(self.output_dir, 'logs/')
        self.json_dir = os.path.join(self.output_dir, 'json/')
        self.detail_dir = os.path.join(self.json_dir, 'detail/')

        # Make sure the output directories exist
        self.ensure_directory_exists(self.output_dir)
        self.ensure_directory_exists(self.logs_dir)
        self.ensure_directory_exists(self.json_dir)
        self.ensure_directory_exists(os.path.join(self.json_dir, 'detail'))
        self.ensure_directory_exists(os.path.join(self.json_dir, 'events'))
        self.ensure_directory_exists(os.path.join(self.json_dir, 'severities'))
        self.ensure_directory_exists(os.path.join(self.json_dir, 'states'))

        # Load states
        states_filepath = os.path.join(self.data_dir, 'states.json')
        self.states_list = self.load_json(states_filepath)
        self.states_dict = {}
        self.state_abbrs_dict = {}
        for state in self.states_list:
            self.states_dict[state['fips']] = state
            self.state_abbrs_dict[state['abbr']] = state

        # Load counties
        counties_filepath = os.path.join(self.data_dir, 'counties.json')
        self.counties_list = self.load_json(counties_filepath)
        self.counties_dict = {}
        for county in self.counties_list:
            self.counties_dict[county['fips']] = county

        # Load UGC Zones
        ugc_filepath = os.path.join(self.data_dir, 'ugc_zones.json')
        self.ugc_zones_list = self.load_json(ugc_filepath)
        self.ugc_zones_dict = {}
        for ugc in self.ugc_zones_list:
            zone = ugc['state'] + "Z" + ugc['zone']
            self.ugc_zones_dict[zone] = ugc

        # Load Special Weather Statement replacements
        special_filepath = os.path.join(self.data_dir, 'special.json')
        self.special_replacements_list = self.load_json(special_filepath)
        
        # Load Events to be Skipped
        skippable_events_filepath = os.path.join(self.data_dir, 'skippable_events.json')
        self.skippable_events_list = self.load_json(skippable_events_filepath)

    ### Custom Objects ###
    
    class Alert():
        pass

    ### Custom Exceptions ###

    class XMLError(Exception):
        def __init__(self, value):
            self.value = value
        def __str__(self):
            return repr(self.value)

    class GeometryError(Exception):
        def __init__(self, value):
            self.value = value
        def __str__(self):
            return repr(self.value)

    ### Logging Methods ###
    
    def log(self, message):
        now_utc = datetime.datetime.now(pytz.utc)
        log_filepath = os.path.join(self.logs_dir, 'log.txt')
        log_msg = "%s\t%s\n" % (now_utc, message)
        print log_msg.strip()
        with codecs.open(log_filepath, 'a', 'UTF-8') as f:
            f.write(log_msg)

    def log_missing_fips(self, fips_code):
        log_filepath = os.path.join(self.logs_dir, 'missing_fips.txt')
        with codecs.open(log_filepath, 'a', 'UTF-8') as f:
            f.write("%s\n" % fips_code)

    def log_missing_ugc(self, ugc_code):
        log_filepath = os.path.join(self.logs_dir, 'missing_ugc.txt')
        with codecs.open(log_filepath, 'a', 'UTF-8') as f:
            f.write("%s\n" % ugc_code)

    def log_error(self, message):
        now_utc = datetime.datetime.now(pytz.utc)
        log_filepath = os.path.join(self.logs_dir, 'errors.txt')
        with codecs.open(log_filepath, 'a', 'UTF-8') as f:
            f.write("%s\t%s\n" % (now_utc, message))

    def log_special_statement(self, message):
        now_utc = datetime.datetime.now(pytz.utc)
        log_filepath = os.path.join(self.logs_dir, 'missing_sws.txt')
        with codecs.open(log_filepath, 'a', 'UTF-8') as f:
            f.write("%s\t%s\n\n" % (now_utc, message))
    
    ### File Handling Methods ###
    
    def load_json(self, filepath):

        # Make sure file exists
        if not os.path.exists(filepath):
            msg = "Error: Could not load file: %s" % filepath
            self.log_error(msg)
            sys.exit(msg)

        # Read the file
        with codecs.open(filepath, 'r', 'UTF-8') as f:
            contents = f.read()

        # Deserialize the JSON
        try:
            data = json.loads(contents)
            return data
        except ValueError:
            msg = "JSON error loading file: \'%s\'" % filepath
            self.log_error(msg)
            sys.exit(msg)

    def save_bad_xml(self, file_contents):
        now_utc = datetime.datetime.now(pytz.utc)
        time_str = now_utc.strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(self.logs_dir, 'bad_alert_%s.xml' % time_str)
        with codecs.open(log_filepath, 'a', 'UTF-8') as f:
            f.write("%s\t%s\n\n" % (now_utc, message))
    
    def write_contents_to_filepath(self, contents, filepath):
        with codecs.open(filepath, 'w', 'UTF-8') as f:
           f.write(contents)

    def ensure_directory_exists(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

    ### XML Parsing Methods ###

    def get_element_text(self, element, name, default_value=''):
        el = element.find(name)
        if el is not None and el.text:
            return el.text.strip()
        else:
            return default_value

    def get_element_attr(self, element, name, attr_name, default_value=''):
        el = element.find(name)
        if el is not None and el.attrib.has_key(attr_name):
            return el.attrib[attr_name].strip()
        else:
            return default_value

    def load_xml_from_url(self, url):
        f = urllib2.urlopen(url, timeout=10)
        request_data = f.read()
        try:
            tree = ET.fromstring(request_data)
            return tree
        except lxml.etree.XMLSyntaxError:
            raise self.XMLError("Error Loading XML from URL: %s" % url)

    ### Geographic Methods ###

    def create_polygon_coords(self, verticies_string):
        verticies_list = []
        verticies_tuple = [v.split(",") for v in verticies_string.split(" ")]
        for item in verticies_tuple:
            verticies_list.append([float(item[1]), float(item[0])])
        # We need to make sure that the verticies don't have a bad point in them
        if not self.check_verticies_for_errors(verticies_list):
            return verticies_list
        else:
            self.log_error("Distance between points was %f in polygon (%s)" % (distance, alert['polygon']))
            raise GeometryError("A bad point was present in the polygon")
    
    def check_verticies_for_errors(self, verticies_list):
        # Sometimes there is a bad point in the verticies list, this often happens 
        # when a point of 0.0 appears. We check to see if there is a distance of more 
        # than 25 miles between points. If so, we assume an error.
        for point in verticies_list:
            first_point = shapely.geometry.Point(verticies_list[0][0],verticies_list[0][1])
            cur_point = shapely.geometry.Point(point[0], point[1])
            distance = first_point.distance(cur_point)
            if distance > 25:
                return True
        return False

    ### Other Methods ###

    def refine_special_weather_statement(self, description):
        print "DEBUG: Need to work on refine_special_weather_statement"
        return

    def get_counties_by_fips(self, county_fips_list):
        matched_counties = []
        for fips_code in county_fips_list:
            # For some reason, 'ant' shows up occasionally in the list of county FIPS codes. Ignore it.
            if fips_code == 'ant':
                self.log("FIPS6 list includes 'ant' entry (%s). Skipping." % ", ".join(county_fips_list))
                continue
            try:
                county = self.counties_dict[fips_code]
                matched_counties.append(county)
            except KeyError:
                self.log("Could Not Find County FIPS: %s" % fips_code)
                self.log_missing_fips(fips_code)
        return matched_counties

    def get_zones_by_code(self, ugc_zone_codes_list):
        matched_zones = []
        for zone_code in ugc_zone_codes_list:
            try:
                ugc_zone = self.ugc_zones_dict[zone_code]
                matched_zones.append(ugc_zone)
            except KeyError:
                self.log("Count Not Find UGC Zone: %s" % zone_code)
                self.log_missing_ugc(zone_code)
        return matched_zones

    def get_states_by_ugc_codes(self, ugc_zone_codes_list):
        matched_states = []
        for ugc_code in ugc_zone_codes_list:
            try:
                ugc_zone = self.ugc_zones_dict[ugc_code]
                state_abbr = ugc_zone['state']
                state = self.state_abbrs_dict[state_abbr]
                matched_states.append(state)
            except KeyError:
                self.log("Could not find UGC Zone Code: %s" % ugc_code)
                self.log_missing_ugc(ugc_code)
        return matched_states

    def get_states_by_county_fips(self, county_fips_list):
        matched_states = []
        for fips_code in county_fips_list:
            # For some reason, 'ant' shows up occasionally in the list of county FIPS codes. Ignore it.
            try:
                county = self.counties_dict[fips_code]
                abbr = county['state']
                state = self.state_abbrs_dict[abbr]
                matched_states.append(state)
            except KeyError:
                pass
        return matched_states

    def get_county_fips_for_ugc_zones(self, ugc_zones_list):
        additional_fips = []
        for ugc_code in ugc_zones_list:
            try:
                ugc_zone = self.ugc_zones_dict[ugc_code]
                for fips in ugc_zone['fips']:
                    additional_fips.append(fips)
            except KeyError:
                self.log("Could not find UGC Zone Code: %s" % ugc_code)
                self.log_missing_ugc(ugc_code)
        return additional_fips

    def create_unique_identifier(self, string_to_hash):
        h = hashlib.new('ripemd160')
        h.update(string_to_hash)
        return h.hexdigest()

    def get_timezone_from_title(self, title):
        # This is a little hacky-hack, but it's the only way of knowing for sure what the
        # timezone was without some really nasty work.
        if "until" in title:
            local_tz_start = title.index(' until') - 4
            local_tz_end = title.index('until')
            return title[local_tz_start:local_tz_end].strip()
        elif "by NWS" in title:
            local_tz_start = title.index(' by NWS') - 4
            local_tz_end = title.index('by NWS')
            return title[local_tz_start:local_tz_end].strip()
        else:
            return ""

    def find_previous_alert_by_uuid(self, uuid, timestamp):
        for old_alert_dict in self.previous_alerts_list:
            if old_alert_dict['uuid'] == uuid:
                # If we find the alert, make sure it's the same age
                if old_alert_dict['updated'] == timestamp.isoformat():
                    return old_alert_dict
        return None

    def refine_weather_statement(self, description):
        """
        We use this method to look inside the description of a Special
        Weather Statement. We are trying to find keywords that we can 
        use to apply extra words to the kind of event.
        """
        
        # We don't know what kind of capitalization might be used
        description = description.lower().replace("\n", " ")

        # We will append any of the keywords we find to the event
        matched_suffixes = []
        
        # Loop over the list of special replacements
        for [key, value] in self.special_replacements_list:
            
            # The key might be a single string or an array
            if type(key) == unicode:
                if key in description:
                    matched_suffixes.append(value)
            elif type(key) == list:
                # Check to make sure all items in the list are present
                for item in key:
                    all_matched = True
                    if not item in description:
                        all_matched = False
                # If all items in the list key were present, we have a match
                if all_matched:
                    matched_suffixes.append(value)

        # Add all the unique suffixes to the event
        if matched_suffixes:
            unique_suffixes = list(set(matched_suffixes))
            sorted_suffixes = sorted(unique_suffixes)
            suffixes_string = ", ".join(sorted_suffixes)
            self.log("Added Keywords to Special Weather Statement: %s" % suffixes_string)
            return "Special Weather Statement (%s)" % suffixes_string
        else:
            self.log("Found Special Weather Statement That Did Not Match Available Keywords")
            self.log_special_statement(description)
            return "Special Weather Statement"

    def get_region_from_sender(self, sender):
        # Sender will look like this: "NWS Reno (Western Nevada)" so 
        # we need to find what is between the parentheses
        start_index = sender.find("(")
        end_index = sender.find(")")
        if (start_index > 0) and (end_index > 0):
            region = sender[start_index+1:end_index]
            # Make sure the region is capitalized properly
            region = region[0].upper() + region[1:]
        else:
            region = None
        # The storm prediction center in Norman, OK might have published this
        # even if the area has nothing to do with Oklahoma, so check it
        if "Norman, Oklahoma" in region:
            region = None

        return region

if __name__ == "__main__":
    pass
