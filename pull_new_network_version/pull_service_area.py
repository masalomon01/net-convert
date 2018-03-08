import pg8000 as pg
import time
import config

# This file is exported from
print '...'
start_time = time.time()

folder = 'D:/Will/Metropia/Network Updates/New York/Update 6-28-2016/'
city = "osm_newyork"
out_boundary = open(folder + city + '_polygon.json', 'wb')

conn = pg.connect(user=config.NETWORKLAND_USER, password=config.NETWORKLAND_PASSWORD, host=config.NETWORKLAND_URL, database=config.NETWORKLAND_DB)  # port default 5432
cursor = conn.cursor()

query = "SELECT ST_AsGeoJSON(geom) FROM {}_polygons WHERE type='boundary'".format('newyork')
cursor.execute(query)
results = cursor.fetchall()
for row in results:
    out_boundary.write(row[0])

print("Elapsed time... %s seconds" % (time.time() - start_time))