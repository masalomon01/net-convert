import xml.etree.cElementTree as cElementTree
import csv


folder = 'D:/Will/GIS Data/Raw OSM Data/El Paso/'
raw_osm_file = folder + 'elpaso_juarez_cruces.osm'
outfile = folder + 'alleys.csv'

writer = csv.writer(open(outfile, 'wb'))
writer.writerow(['OSMID'])

context = cElementTree.iterparse(raw_osm_file, events=("start", "end"))
context = iter(context)
event, root = next(context)

for event, elem in context:
    if event == 'end' and elem.tag == 'way':
        is_alley = False
        iterator = iter(elem)
        for child in iterator:
            if child.get('k') == 'service' and (child.get('v') == 'alley'):
                is_alley = True

        if is_alley:
            writer.writerow([elem.get('id')])
    root.clear()