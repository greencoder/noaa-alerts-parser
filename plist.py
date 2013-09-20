import os
import json
import codecs
import plistlib
import argparse

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='Input File', required=True)
    parser.add_argument('-o', help='Output File', required=True)
    args = vars(parser.parse_args())

    if not os.path.exists(args['i']):
        sys.exit("Input file not found: %s" % args['i'])

    # Open up the alerts list
    json_filepath = os.path.join(CUR_DIR, args['i'])

    f = codecs.open(json_filepath, 'r', 'utf-8')
    contents = f.read()
    f.close()

    alerts_dict = json.loads(contents)
    
    plistlib.writePlist(alerts_dict, args['o'])
    
    print "Done."