import networkx as nx
import csv
import pg8000 as pg

# get the network
city = 'newyork'
conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
query = "SELECT gid, ST_AsText(ST_StartPoint(geom)), ST_AsText(ST_EndPoint(geom)) FROM {}".format(city)
cursor.execute(query)
results = cursor.fetchall()
print 'data fetched'
G = nx.Graph()

# construct undirected graph
for row in results:
    gid = row[0]
    start_point = row[1]
    end_point = row[2]
    G.add_edges_from([(start_point, end_point, {'gid': gid})])

print 'graph constructed'

# evaluate on connected components
connected_components = list(nx.connected_component_subgraphs(G))
# gather edges and components to which they belong
fid_comp = {}
for i, graph in enumerate(connected_components):
   for edge in graph.edges_iter(data=True):
       fid_comp[edge[2].get('gid', None)] = i

print 'components analyzed...printing results'

# write output to csv file
with open('D:/Will/temp/disconnected_islands.csv', 'wb') as f:
    w = csv.DictWriter(f, fieldnames=['gid', 'comp_id'])
    w.writeheader()
    for row in fid_comp.items():
        if row[1] != 0:  # only want a list of the disconnected ones right now
            w.writerow({'gid': row[0], 'comp_id': row[1]})