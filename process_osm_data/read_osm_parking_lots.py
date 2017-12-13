import xml.etree.cElementTree as cElementTree
import csv

folder = 'D:/Will/GIS Data/Raw OSM Data/EP/'
raw_osm_file = folder + 'arizona_8-12-2016.osm'
outfile = folder + 'parking_lots.csv'

writer = csv.writer(open(outfile,'wb'))
writer.writerow(['OSMID'])

context = cElementTree.iterparse(raw_osm_file, events=("start", "end"))
context = iter(context)
event, root = next(context)

for event, elem in context:
    if event == 'end' and elem.tag == 'way':
        is_parking = False
        iterator = iter(elem)
        for child in iterator:
            if child.get('k') == 'service' and (child.get('v') == 'parking_aisle' or child.get('v') == 'parking'):
                is_parking = True
            if child.get('k') == 'amenity' and child.get('v') == 'parking':
                is_parking = True

        if is_parking:
            writer.writerow([elem.get('id')])
    root.clear()