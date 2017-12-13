import psycopg2 as pg
import sys
from shapely import wkb
import requests


def read_sys_args(args):
    try:
        city = args[1]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be city name')
    return city


if __name__ == '__main__':
    if len(sys.argv) < 2:
        city = 'elpaso_juarez'
    else:
        city = read_sys_args(sys.argv)
    conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
    cursor = conn.cursor()
    while True:
        gids = []
        # todo: dont hardcode the key
        url = 'https://maps.googleapis.com/maps/api/elevation/json?key=AIzaSyCsgqzVsSW-ivbSC0bdu51y7SpnbIFgY1A&locations='
        # google api has a limit on url length so stick to 100 links at a time
        query = "SELECT gid, ST_StartPoint(geom) FROM {} WHERE elevation IS NULL LIMIT 100".format(city)
        cursor.execute(query)
        results = cursor.fetchall()
        if len(results) == 0:
            print 'All links have an elevation'
            break
        for row in results:
            gids.append(row[0])
            geom = wkb.loads(row[1], hex=True).coords[:]
            latitude = geom[0][1]
            longitude = geom[0][0]
            url += '{}, {}|'.format(latitude, longitude)

        url = url[:-1]  # trim the last |
        r = requests.get(url).json()
        if r['status'] == 'INVALID_REQUEST':
            print r['error_message']

        data = r['results']
        if len(data) != len(gids):
            print 'ERROR: Google returned {} elevations when queried for {} links'.format(len(data), len(gids))
            print 'Problem URL:'
            print url
            break

        # really feels like there should be a library to optimize sending large numbers of queries
        # but no db library I could find has a better alternative than building a big string containing many updates
        update_query = ""
        for i, gid in enumerate(gids):
            elevation = int(data[i]['elevation']) * 3.2808399  # convert to feet
            update_query += "UPDATE {} SET elevation = {} WHERE gid = {};".format(city, elevation, gid)

        cursor.execute(update_query)
        conn.commit()


