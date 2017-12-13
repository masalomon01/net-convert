import xml.etree.cElementTree as cElementTree
import csv

folder = 'D:/Will/GIS Data/Raw OSM Data/new york/'
raw_osm_file = folder + 'NY_February_2016.osm'
writer = csv.writer(open(folder+'trunk_names.csv','wb'))
writer.writerow(['osmid','name'])

context = cElementTree.iterparse(raw_osm_file, events=("start", "end"))
context = iter(context)
event, root = next(context)

for event, elem in context:
    if event == 'end' and elem.tag == 'way':
        iterator = iter(elem)
        highway = None
        name = None
        for child in iterator:
            if child.get('k') == 'highway':
                highway = child.get('v')
            elif child.get('k') == 'ref':
                name = child.get('v')
        if highway == 'trunk' and name is not None and len(name) > 1:
            osm_id = elem.get('id')
            writer.writerow([osm_id,name])
        root.clear()
    else:
        root.clear()