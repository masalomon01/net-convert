import pg8000 as pg
import csv
import time
import sys
import os
import config


def read_sys_args(args):
    try:
        folder_path = args[1]
        city = args[2]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be a path to folder and arg2 should be city name')
    if folder_path[-1] != '/':
        folder_path += '/'
    return folder_path, city


def elpaso_poe_table(folder, cur, mapping_table):
    out = csv.writer(open(folder+'poe_segment_table.csv', 'wb'))
    out.writerow(['gid', 'parade_id', 'segment_id', 'name', 'port_of_entry', 'direction', 'wt_entity_id', 'wt_seg_id'])
    query = "SELECT l.segment_id, l.gid, m.name, m.port_of_entry, m.direction, m.wt_entity_id, m.wt_seg_id " \
            "FROM public.elpaso_juarez_poe_link2segment l inner join public.elpaso_juarez_poe_segments_mapping m " \
            "on l.segment_id = m.segment_id"
    cur.execute(query)
    results = cur.fetchall()
    for row in results:
        gid = str(row[1])  # convert to string bc it is previously read as a string from wkt
        seg_id = row[0]
        if gid in mapping_table:
            parade_id = mapping_table[gid]
            out.writerow([gid, parade_id, seg_id, row[2], row[3], row[4], row[5], row[6]])


if __name__ == '__main__':

    print '...'
    start_time = time.time()

    # To RUN please enter city
    if len(sys.argv) < 3:  # for testing locally
        city = sys.argv[1]  # elpaso, tucson, austin
        folder = os.getcwd() + '/'
    else:
        folder, city = read_sys_args(sys.argv)  # this line is to incorporate jenkins

    in_wkt = open(folder + city + '/links_wkt.csv', 'rb')
    out_file = open(folder + 'parade gid zone.csv', 'wb')
    conn = pg.connect(user=config.NETWORKLAND_USER, password=config.NETWORKLAND_PASSWORD, host=config.NETWORKLAND_URL, database=config.NETWORKLAND_DB)  # port default 5432
    cursor = conn.cursor()

    query = "SELECT {}.gid, {}_zones.zone " \
            "FROM {}, {}_zones " \
            "WHERE ST_INTERSECTS({}.geom,{}_zones.geom)".format(city, city, city, city, city, city)
    cursor.execute(query)
    print 'query executed'
    results = cursor.fetchall()
    print 'results fetched'

    gid_zone = {}  # gid : zone
    gid_parade = {}
    for row in results:
        gid_zone[str(row[0])] = row[1]
    print 'gid to zone table built'

    reader = csv.DictReader(in_wkt)
    writer = csv.writer(out_file)
    writer.writerow(['LinkID_parade', 'gid', 'zone'])
    for row in reader:
        parade = row['LinkID_parade']
        gid = row['LinkID_ptv']
        gid_parade[gid] = parade
        try:
            zone = gid_zone[gid]
        except KeyError:
            zone = '40'
        new_row = [parade, gid, zone]
        writer.writerow(new_row)

    if city == 'elpaso_juarez':
        print 'building elpaso_poe_segment table'
        elpaso_poe_table(folder, cursor, gid_parade)

    print("Elapsed time... %s seconds" % (time.time() - start_time))
