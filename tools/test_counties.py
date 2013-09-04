import os
import codecs
import json
import sys

from shapely.geometry import box, Polygon, Point

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(CUR_DIR, '../data/')
FILEPATH = os.path.join(DATA_DIR, 'counties.json')

f = codecs.open(FILEPATH, 'r', 'utf-8')
contents = f.read()
f.close()

bad_record_count = 0
counties = json.loads(contents)

for county in counties:

    bbox = county['bbox']
    lat = county['lat']
    lng = county['lng']
    
    point = Point(lng, lat)
    polygon = box(bbox[0], bbox[1], bbox[2], bbox[3])

    if not polygon.contains(point):
        print county
        bad_record_count += 1

print bad_record_count
print len(counties)