import xml.etree.cElementTree as cElementTree
from datetime import datetime
import pg8000 as pg

folder = 'D:/Will/GIS Data/Raw OSM Data/Houston/'
city = 'houston'
raw_osm_file = folder + 'houston.osm'
time_last_update = datetime.strptime('2016-05-19', '%Y-%m-%d')
check_timestamp = False

print('reading data...')
conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()

# Need an XML parser that does not load everything into memory in order to handle bigger networks
# See http://effbot.org/zone/element-iterparse.htm for explanation of this parser
# Basically regular xml.parse() makes a tree of all data, which is an issue for big files
# This still makes a tree, but lets you remove and alter elements when iterating through
context = cElementTree.iterparse(raw_osm_file, events=("start", "end"))
context = iter(context)
event, root = next(context)

only_restrictions = []  # (from, to) is the only allowed turn at this location
no_restrictions = []  # (from, to) in this list is not allowed
nodes = {}  # osmid : (lat,lon)
for event, elem in context:
    if event == 'end' and elem.tag == 'node':
        osmid = int(elem.get('id'))
        lat = float(elem.get('lat'))
        lon = float(elem.get('lon'))
        nodes[osmid] = (lat,lon)
        root.clear()
    elif event == 'end' and elem.tag == 'way':
        root.clear()
    if event == 'end' and elem.tag == 'relation':
        timestamp = datetime.strptime(elem.get('timestamp'),'%Y-%m-%dT%H:%M:%SZ')  # see python docs for explanation of datetime arguments
        # if timestamp is older than the last update then skip this because we already got it in last update
        if check_timestamp and (timestamp < time_last_update):
            continue
        is_restriction = False
        restriction_type = None
        tags = elem.findall('tag')
        for t in tags:
            if t.get('k') == 'restriction':
                is_restriction = True
                restriction_type = t.get('v')
        if is_restriction and restriction_type is not None:

            members = elem.findall('member')
            from_way = None
            to_way = None
            through_node = None
            for member in members:
                if member.get('type') == 'way' and member.get('role') == 'from':
                    from_way = int(member.get('ref'))
                elif member.get('type') == 'way' and member.get('role') == 'to':
                    to_way = int(member.get('ref'))
                elif member.get('type') == 'node' and member.get('role') == 'via':
                    through_node = int(member.get('ref'))
            if from_way is not None and to_way is not None and through_node is not None:

                # now we have a valid restriction
                through_lat = nodes[through_node][0]
                through_lon = nodes[through_node][1]
                as_text = 'POINT({} {})'.format(through_lon, through_lat)
                query = "SELECT gid FROM {} WHERE osmid={} AND ST_AsText(ST_EndPoint(geom))='{}'".format(city, from_way, as_text)
                cursor.execute(query)
                results = cursor.fetchall()
                if len(results) != 1:  # if this is true then there is problem with restriction
                    print 'restrict {} via {} to {} has an issue'.format(from_way, through_node, to_way)
                    continue
                from_link = results[0][0]
                query = "SELECT gid FROM {} WHERE osmid={} AND ST_AsText(ST_StartPoint(geom))='{}'".format(city, to_way, as_text)
                cursor.execute(query)
                results = cursor.fetchall()
                if len(results) != 1: # if this is true then there is problem with restriction
                    continue
                to_link = results[0][0]

                if restriction_type[:2] == 'no':
                    no_restrictions.append((from_link,to_link))
                elif restriction_type[:4] == 'only':
                    only_restrictions.append((from_link,to_link))

        root.clear()

for row in no_restrictions:
    query = "SELECT * FROM {}_abbieger WHERE from_link={} AND to_link={}".format(city, row[0], row[1])
    cursor.execute(query)
    results = cursor.fetchall()
    if len(results) > 0:  # evaluates to true if we already have this restriction
        continue
    query = "INSERT INTO {}_abbieger VALUES ({},{})".format(city, row[0], row[1])
    cursor.execute(query)

for row in only_restrictions:
    from_link = row[0]
    dont_restrict = row[1]
    query = "SELECT gid FROM {} WHERE ST_StartPoint(geom)= (SELECT ST_EndPoint(geom) FROM {} WHERE gid={})".format(city, city, row[0])
    cursor.execute(query)
    results = cursor.fetchall()
    for row in results:
        if row[0] == dont_restrict:
            continue
        else:
            query = "SELECT * FROM {}_abbieger WHERE from_link={} AND to_link={}".format(city, from_link, row[0])
            cursor.execute(query)
            results = cursor.fetchall()
            if len(results) == 0:
                query = "INSERT INTO {}_abbieger VALUES({}, {})".format(city, from_link, row[0])
                cursor.execute(query)