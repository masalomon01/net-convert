import pg8000 as pg
import math

# UPDATE: There is no longer a reason to run this from python script

print('Running Calculate Bearing...')
city = 'austin'
conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
query = "UPDATE {} SET bearing = (ST_Azimuth(ST_StartPoint(geom), ST_EndPoint(geom))/(2*pi())*360)".format(city)
cursor.execute(query)
conn.commit()
