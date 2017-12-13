import pg8000 as pg
import os


def read_credentials():
    dir = os.path.dirname(__file__)
    credential_file = os.path.join(dir, '../credentials.txt')
    credential_reader = open(credential_file, 'rb')
    username = credential_reader.readline()
    password = credential_reader.readline()
    return username, password



city = 'elpaso_juarez'
restr_table = '{}_abbieger'.format(city)
conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
query = 'SELECT gid, ST_StartPoint(geom), ST_EndPoint(geom) FROM {0} WHERE gid IN ' \
        '(SELECT from_link FROM {1}) OR gid IN (SELECT to_link FROM {2})'.format(city,restr_table,restr_table)
cursor.execute(query)
results = cursor.fetchall()

link_first_points = {}  # gid : first point
link_end_points = {}  # gid : end point

for row in results:
    link_first_points[row[0]] = row[1]
    link_end_points[row[0]] = row[2]

query = 'SELECT from_link, to_link, note FROM {}'.format(restr_table)
cursor.execute(query)
results = cursor.fetchall()
for row in results:
    try:
        to_node = link_end_points[row[0]]
        from_node = link_first_points[row[1]]
        if to_node != from_node and row[2] != 'disconnected':
            print str(row) + ' does not have connected source/destination links'
            #print to_node, from_node
    except KeyError:
        print str(row) + ' has an id that does not exist in network'