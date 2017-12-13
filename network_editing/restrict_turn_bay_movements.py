import pg8000 as pg
from shapely import wkb
import math


def bearing(slat, slong, elat, elong):
    start_lat = math.radians(slat)
    start_lon = math.radians(slong)
    end_lat = math.radians(elat)
    end_lon = math.radians(elong)
    d_lon = end_lon - start_lon
    temp = math.tan(end_lat/2.0+math.pi/4.0)/math.tan(start_lat/2.0+math.pi/4.0)
    d_phi = math.log(temp)
    if abs(d_lon) > math.pi:
        if d_lon > 0.0:
            d_lon = -(2.0 * math.pi - d_lon)
        else:
            d_lon = (2.0 * math.pi + d_lon)

    b = (math.degrees(math.atan2(d_lon, d_phi)) + 360.0) % 360.0
    return b


def calc_angle(bearing1, bearing2):
    return ((((bearing1 - bearing2) % 360) + 540) % 360) - 180


def get_link_geom(city):
    query = "SELECT gid, geom FROM {} WHERE (highway = 'primary_link' OR highway = 'secondary_link' OR highway = 'tertiary_link') OR ST_StartPoint(geom) IN (SELECT ST_EndPoint(geom) FROM tucson WHERE (highway = 'primary_link' OR highway = 'secondary_link' OR highway = 'tertiary_link'))".format(city)

    cursor.execute(query)
    results = cursor.fetchall()
    start = {}
    end = {}
    link_geom = {}
    for row in results:
        geometry = wkb.loads(row[1], hex=True).coords[:]
        start_point = geometry[0]
        end_point = geometry[1]
        start[row[0]] = start_point
        end[row[0]] = end_point
        link_geom[row[0]] = geometry

    return link_geom, start, end


def get_link_types(city):
    query = "SELECT gid FROM {} WHERE highway (highway = 'primary_link' OR highway = 'secondary_link' OR highway = 'tertiary_link')".format(city)
    cursor.execute(query)
    results = cursor.fetchall()
    gids = [row[0] for row in results]



if __name__ == '__main__':
    conn = pg.connect(user='read_only', password='only4metropians',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    link_geometry, link_start, link_end = get_link_geom('tucson')
