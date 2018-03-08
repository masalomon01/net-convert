import pg8000 as pg
import csv
import sys
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


def parse_restriction(restriction):
    r = []
    days = ''
    for item in restriction:
        if item == True:
            days+= '1'
        elif item == False:
            days+= '0'
    r+= [days]
    for item in restriction[7:]:
        if item:
            r += [item]
    return r


if __name__ == '__main__':
    folder, city = read_sys_args(sys.argv)
    conn = pg.connect(user=config.NETWORKLAND_USER, password=config.NETWORKLAND_PASSWORD, host=config.NETWORKLAND_URL, database=config.NETWORKLAND_DB)  # port default 5432cursor = conn.cursor()
    cursor = conn.cursor()
    outfile = open(folder+'gid_tdtr.csv', 'wb')
    query = 'SELECT from_link, to_link, monday, tuesday, wednesday, thursday, friday, saturday, sunday, from_time1, to_time1, from_time2, to_time2 FROM {}_tdtr'.format(city)
    cursor.execute(query)
    results = cursor.fetchall()

    restrictions = {}  # (from_link, to_link) : [monday, tuesday, wednesday, thursday, friday, saturday, sunday, from_time1, to_time1, from_time2, to_time2]
    for row in results:  # this loop is just a little QAQC to check connectivity
        restrictions[(row[0],row[1])] = row[2:]
        query = "SELECT ST_AsText(ST_EndPoint(geom)) FROM {0} WHERE gid={1}".format(city,str(row[0]))
        cursor.execute(query)
        end_point = cursor.fetchone()
        query = "SELECT ST_AsText(ST_StartPoint(geom)) FROM {0} WHERE gid={1}".format(city,str(row[1]))
        cursor.execute(query)
        start_point = cursor.fetchone()
        if end_point != start_point:
            print 'ERROR: ' + str(row[0]) + ' and ' + str(row[1]) + ' are not connected!'

    writer = csv.writer(outfile)
    writer.writerow(['from_link', 'to_link', 'days', 'time_start', 'time_end', 'time_start2', 'time_end2'])
    for sequence, values in restrictions.items():
        formatted_data = [sequence[0], sequence[1]] + parse_restriction(values)
        while len(formatted_data) < 7:
            formatted_data += ['']
        writer.writerow(formatted_data)

    query = "SELECT from_link, to_link FROM {}_abbieger".format(city)
    cursor.execute(query)
    results = cursor.fetchall()
    for row in results:
        formatted_data = row + ['', '', '', '', '']
        writer.writerow(formatted_data)
