import xml.etree.cElementTree as cElementTree
import pg8000 as pg

folder = 'D:/Will/GIS Data/Raw OSM Data/Tucson/2017/'
raw_osm_file = folder + 'tucson_1-4-2017.osm'
city_name = 'tucson'

conn = pg.connect(user='networkland',
                      password='M+gis>ptv',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
cursor = conn.cursor()
# check which nodes we already have in database
query = "SELECT osmid FROM {}_nodes".format(city_name)
cursor.execute(query)
results = cursor.fetchall()
already_in_database = {row[0] for row in results}

context = cElementTree.iterparse(raw_osm_file, events=("start", "end"))
context = iter(context)
event, root = next(context)

signal_nodes = {}  # osmid : (lat, lon)

for event, elem in context:
    if event == 'end' and elem.tag == 'node':
        is_signal = False
        iterator = iter(elem)
        for child in iterator:
            if child.get('k') == 'highway' and child.get('v') == 'traffic_signals':
                osmid = int(elem.get('id'))
                lat = float(elem.get('lat'))
                lon = float(elem.get('lon'))
                if osmid not in already_in_database:
                    signal_nodes[osmid] = (lat, lon)

    root.clear()

count = 0
for osmid, lat_lon in signal_nodes.items():
    query = "INSERT INTO {}_nodes (osmid, geom) VALUES ({}, ST_SetSRID(ST_MakePoint({}, {}), 4269))".format(city_name, osmid, lat_lon[1], lat_lon[0])
    try:
        cursor.execute(query)
        conn.commit()
        count += 1
        print(count)
    except Exception:
        # should add a more specifc exception - this is meant to handle pg8000 throwing an error when the node already exists
        pass
