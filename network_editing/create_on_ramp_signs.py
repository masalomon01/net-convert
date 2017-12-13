import pg8000 as pg
from collections import defaultdict
import unicodecsv as csv

def find_next_road(link):
    name = None
    cur_link = link
    while name is None:
        cur_link_to_node = link_to_node[cur_link]
        next_link = link_start[cur_link_to_node]
        if len(next_link) > 1:
            break
        if len(next_link) == 0:
            break
        next_link = next_link[0]
        name = link_name[next_link]
        cur_link = next_link
    return name

city = 'houston'
out_file = open('D:/Will/Metropia/Network Updates/Houston/{}_signs.csv'.format(city), 'wb')

conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
query = "CREATE TEMP TABLE ramps AS " \
        "SELECT gid, ST_AsText(ST_StartPoint(geom)) " \
        "FROM {} " \
        "WHERE highway='motorway_link' ".format(city)
cursor.execute(query)
query = "CREATE INDEX ON ramps (st_astext)"
cursor.execute(query)
print 'temp table created'

query = "SELECT from_link, to_link FROM {}_abbieger".format(city)
cursor.execute(query)
restrictions = set((row[0],row[1]) for row in cursor.fetchall())
print 'restrictions set built'

query = "SELECT gid, ST_AsText(ST_EndPoint(geom)) " \
        "FROM {0} " \
        "WHERE ST_AsText(ST_EndPoint(geom)) IN (SELECT st_astext FROM ramps) " \
        "AND highway != 'motorway' " \
        "AND highway != 'motorway_link' " \
        "AND gid NOT IN (SELECT source_link FROM {1}_signs);".format(city,city)
cursor.execute(query)
src_links1 = cursor.fetchall()
# at this point we now have a list of possible sign source links
print 'possible sign locations determined'
query = "SELECT gid, ST_AsText(ST_StartPoint(geom)), ST_AsText(ST_EndPoint(geom)), street_name " \
        "FROM {} " \
        "WHERE highway = 'motorway' " \
        "OR highway = 'motorway_link'".format(city)
cursor.execute(query)
results = cursor.fetchall()

# the following dicts have all link start/end points which we can use to look up predecessors and successors
# a link with startpoint X is the successor of all links with endpoint X
link_start = defaultdict(list)  # startpoint : [gid1,gid2...]  use to look up links connected to a point
link_end = defaultdict(list)  # endpoint : [gid1,gid2...]
link_from_node = defaultdict(list)  # use these two to look up a start/end node given a gid
link_to_node = defaultdict(list)
link_name = {}  # gid : name
for row in results:
    link_start[row[1]].append(row[0])
    link_end[row[2]].append(row[0])
    link_from_node[row[0]] = row[1]
    link_to_node[row[0]] = row[2]
    link_name[row[0]] = row[3]


# now lets loop through potential sign locations and create a set of tuples where each tuple
# consists of the source and destination links
# we will check the abbieger table to make sure it is not a restricted link pair
new_signs = []
writer = csv.writer(out_file)
writer.writerow(['source_link', 'destination_link', 'sign_text'])
for row in src_links1:
    # get the link successors, which we know are all ltype 3 from the sql query
    end_point = row[1]
    gid = row[0]
    try:
        successor = link_start[end_point]
    except:
        print 'BUG HERE: at id {}'.format(gid)
        continue

    if len(successor) > 1:
        print 'WARNING: link {0} has multiple ltype 3 successors...skipping...'.format(gid)
        continue
    try:
        successor = successor[0]
    except IndexError:
        print "AHHHHHH"
    if (gid,successor) in restrictions:
        # nobody will ever be routed on a restricted link pair so no need for a sign
        continue
    # at this point we have a valid sign location
    # since it is an on ramp sign we know everything except the road that it is being branched to

    next_name = find_next_road(successor)  # could pass the source link into this but saves time to pass the ramp
    if next_name is None:
        print 'WARNING: Could not find name after {0}'.format(gid)
        continue
    # now we have location of sign as well as the name of freeway that it is branching onto
    writer.writerow([str(gid), str(successor), next_name])