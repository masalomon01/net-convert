import csv
import pg8000 as pg
import operator
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


def parse_restriction(restriction, number_successors, index_of_restriction):
    r = '['
    for item in restriction:
        if item == True:
            r+= '1'
        elif item == False:
            r+= '0'
    for item in restriction[7:]:
        if item:
            r += ',' + str(item)
    r += ']'
    return r


conn = pg.connect(user='networkland', password='M+gis>ptv', host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com', database='Networkland')  # port default 5432cursor = conn.cursor()
cursor = conn.cursor()
folder, city = read_sys_args(sys.argv)
in_wkt = open(folder+'{}/links_wkt.csv'.format(city), 'rb')
out_tdtr = folder + 'output_TDTR_2.csv'
query = 'SELECT from_link, to_link, monday, tuesday, wednesday, thursday, friday, saturday, sunday, from_time1, to_time1, from_time2, to_time2 FROM ' + city + '_tdtr'
cursor.execute(query)
results = cursor.fetchall()

restrictions = {}  # (from_link, to_link) : [monday, tuesday, wednesday, thursday, friday, saturday, sunday, from_time1, to_time1, from_time2, to_time2]
for row in results:
    restrictions[(row[0],row[1])] = row[2:]
    query = "SELECT ST_AsText(ST_EndPoint(geom)) FROM {0} WHERE gid={1}".format(city,str(row[0]))
    cursor.execute(query)
    end_point = cursor.fetchone()
    query = "SELECT ST_AsText(ST_StartPoint(geom)) FROM {0} WHERE gid={1}".format(city,str(row[1]))
    cursor.execute(query)
    start_point = cursor.fetchone()
    if end_point != start_point:
        print 'ERROR: ' + str(row[0]) + ' and ' + str(row[1]) + ' are not connected!'


reader = csv.DictReader(in_wkt)
f_names = ['LinkID_par', 'reverseID_', 'LinkID_ptv', 'reverseI_1', 'WKT', 'fromNodeID','toNodeID_p','fromNode_1','toNodeID_1','length(fee','speed(mph)','ltype', 'FFTT(sec)', 'primaryNam', 'secondaryN', 'TMC', 'numLanes','firstOrien','lastOrient','successors','successorA','predecesso','predeces_1','restricted','restrict_1','restrict_2','restrict_3','restrict_4','direction','category','category_p','style', 'type', 'time_depen']
f_names2 = reader.fieldnames + ['time_depen']
out = open(out_tdtr,'wb')
writer = csv.DictWriter(out,fieldnames=f_names)
writer.writeheader()
writer.fieldnames = f_names2
links = {}  # gid : csv reader row
parade_to_gid = {}
new_restrictions = {}  # gid : (index, restriction)
for row in reader:
    row['time_depen'] = ''
    links[int(row['LinkID_ptv'])] = row
    parade_to_gid[row['LinkID_parade']] = int(row['LinkID_ptv'])

for location, restr in restrictions.items():
    from_link = location[0]
    to_link = location[1]

    try:
        successors = links[from_link]['successors'].split(" ")[:-1]
    except KeyError:
        print 'ERROR: {} not a valid ID'
        continue
    successor_paradeID = None
    for each in successors:
        if parade_to_gid[each] == to_link:
            successor_paradeID = each
    if successor_paradeID is None:
        print 'ERROR: Cannot find successor for link {}'.format(from_link)
        continue
    idx_of_succ = successors.index(successor_paradeID)
    parsed_restriction = parse_restriction(restr,len(successors),idx_of_succ)
    if from_link in new_restrictions:
        new_restrictions[from_link].append((idx_of_succ,parsed_restriction))
    else:
        new_restrictions[from_link] = [(idx_of_succ,parsed_restriction)]

for gid, restriction in new_restrictions.items():
    number_successors = links[gid]['successors'].split(" ")[:-1]
    r = ['[]' for x in number_successors]
    for each in restriction:
        r[each[0]] = each[1]

    r_expanded = '['
    for each in r:
        r_expanded += each + ','

    r_expanded = r_expanded[:-1] + ']'
    links[gid]['time_depen'] = r_expanded

for gid, row in links.items():
    writer.writerow(row)
out.close()
with open(out_tdtr, 'rb') as infile:
    sort_reader = csv.reader(infile)
    headers = next(sort_reader)
    links_to_sort = []
    for x in sort_reader:
        x[0] = int(x[0])
        links_to_sort.append(x)

links_to_sort.sort(key=operator.itemgetter(0))

with open(out_tdtr, 'wb') as outfile:
    writer = csv.writer(outfile)
    writer.writerow(headers)
    for x in links_to_sort:
        # Disabling this print statement to be more Jenkins friendly
        # print x
        writer.writerow(x)
