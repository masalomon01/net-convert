import pg8000 as pg

city = "tucson"
conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
query = "SELECT gid, ST_StartPoint(geom), ST_EndPoint(geom), ST_Length(geom) FROM {}".format(city)
cursor.execute(query)
results = cursor.fetchall()
print 'results fetched'

nodes_gid = {}  # (fromnode, tonode) : gid
nodes_length = {}  # (fromnode, tonode) : length
for row in results:
    if (row[1], row[2]) not in nodes_gid:
        nodes_gid[(row[1], row[2])] = row[0]
        nodes_length[(row[1], row[2])] = row[3]
    else:
        duplicate = nodes_gid[(row[1], row[2])]
        print "ERROR: {} HAS DUPLICATE NODES with {}".format(row[0], duplicate)



