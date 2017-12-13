import pg8000 as pg
import csv
import sys


def read_sys_args(args):
    try:
        folder_path = args[1]
        city_name = args[2]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be a path to folder and arg2 should be city name')
    if folder_path[-1] != '/':
        folder_path += '/'
    return folder_path, city_name


def parse_days(restr):
    days = restr[2:9]
    day_string = str([1 if x else 0 for x in days])
    return day_string

conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432
cursor = conn.cursor()
folder, city = read_sys_args(sys.argv)
infile = open(folder + 'parade gid zone.csv', 'rb')
outfile = open(folder + 'new_restrictions.csv', 'wb')

gid_parade = {}
reader = csv.reader(infile)
headers = next(reader)
for row in reader:
    gid_parade[int(row[1])] = int(row[0])

query = "SELECT * FROM {}_abbieger".format(city)
cursor.execute(query)
results = cursor.fetchall()
writer = csv.writer(outfile)
writer.writerow(['from_link', 'to_link', 'days', 'time_start', 'time_end', 'time_start2', 'time_end2'])
for row in results:
    try:
        from_parade = gid_parade[row[0]]
        to_parade = gid_parade[row[1]]
        writer.writerow([from_parade, to_parade])
    except KeyError:
        print str(row) + ' has a link that doesnt exist in network!!'

query = "SELECT from_link, to_link, monday, tuesday, wednesday, thursday, friday, saturday, sunday, from_time1, to_time1, from_time2, to_time2 FROM {}_tdtr".format(city)
cursor.execute(query)
results = cursor.fetchall()
for row in results:
    from_parade = gid_parade[row[0]]
    to_parade = gid_parade[row[1]]
    days = parse_days(row)
    times = row[9:]
    writer.writerow([from_parade, to_parade, days] + times)

