import pg8000 as pg


def read_signal_locations(city_name, id_mapping):
    conn = pg.connect(user='read_only',
                      password='only4metropians',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    query = "SELECT gid FROM {} WHERE ST_EndPoint(geom) IN " \
            "(SELECT geom FROM {}_nodes)".format(city_name, city_name)
    cursor.execute(query)
    results = cursor.fetchall()
    signalized_links = {id_mapping[row[0]]: 'traffic_signal' for row in results if row[0] in id_mapping}
    return signalized_links


def read_intersection_links(city_name, id_mapping):
    conn = pg.connect(user='read_only',
                      password='only4metropians',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    query = "SELECT gid, special_type FROM {} WHERE special_type = 'intersection' OR special_type = 'texas_uturn' OR special_type = 'roundabout'".format(city_name)
    cursor.execute(query)
    results = cursor.fetchall()
    inter_links = set()
    round_links = set()
    texas_u_links = set()
    for each in results:
        try:
            if each[1] == 'roundabout':
                round_links.add(id_mapping[each[0]])
            if each[1] == 'texas_uturn':
                texas_u_links.add(id_mapping[each[0]])
            inter_links.add(id_mapping[each[0]])
        except KeyError:
            # occurs when link is added to network database after the creation of wkt
            pass

    return inter_links, round_links, texas_u_links


def read_restrictions(city_name, id_mapping):
    conn = pg.connect(user='read_only',
                      password='only4metropians',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    query = "SELECT from_link, to_link FROM {}_abbieger".format(city_name)
    cursor.execute(query)
    results = cursor.fetchall()
    restrictions = set()
    for row in results:
        try:
            item0 = id_mapping[row[0]]  # change the gid to parade id
            item1 = id_mapping[row[1]]
        except KeyError:
            # this occurs when the restriction table references a link that doesnt exist in the wkt
            continue
        restrictions.add((item0, item1))
    return restrictions


if __name__ == '__main__':
    # Only used for testing
    read_signal_locations('austin')