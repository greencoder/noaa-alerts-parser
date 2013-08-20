noaa-alerts-parser
==================

Parses the NOAA severe weather alerts XML feed into JSON, adding related information and cleaning up dates.

#Why does this project exist?#

NOAA provides severe weather alerts for the United States in XML format: <http://alerts.weather.gov/cap/us.php?x=1>. They do not provide a JSON feed.

There is a more serious problem with NOAA's feed: They provide the US Counties that an alert applies to but it isn't always complete; sometimes a geographic polygon is provided that represents an additional geographic alert area. This project looks at those polygons and matches up US counties underneath them, making sure those additional counties are represented in the feed.

#Requirements#

The following Python packages are required:
* Shapely (and you must install the GEOS package)
* pytz
* dateutils

All are easily installed via pip. GEOS is available through many package managers or from source at <http://trac.osgeo.org/geos/>.

#Usage#

`$ python parse.py`

This will output an `alerts.json` file in the `output` directory.

According to NOAA, the alerts feed is updated no more than every five minutes, so keep that in mind when making requests.

#Enhancements/To Do#
* Make the output location customizable via command-line.
* Optionally gzip the output file.
