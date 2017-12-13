import arcpy
import csv
import time

"""
This program will take a match table, the OSM shapefile, PTV shapefile, and PTV signs as input
It will output an OSM shapefile with updated TMC IDs
Also output a new signs.tsv
"""
print time.ctime()
StartTime = time.clock()
arcpy.env.workspace = "D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016"
osm = 'OSM_tucson.shp'
add_tmc_field_to_OSM = True
ptv = 'PTV_tucson.shp'
signs = arcpy.env.workspace + '/Signs_tucson.tsv'
match_table = arcpy.env.workspace + '/link2xd_goodones.csv'

metropia_to_parade = {}  # int(metropiaID) : int(paradeID)
with open(match_table, 'rb') as infile:
    reader = csv.reader(infile)
    next(reader)  # we don't want to read headers
    for row in reader:
        metropia_to_parade[int(row[0])] = int(row[1])

parade_links = {}  # int(paradeID) : ['TMC','speed','lanes', 'ltype']
parade_to_ptv = {}  # int(paradeID) : int(ptvID)
cursor = arcpy.da.SearchCursor(ptv, ['LinkID_par', 'LinkID_ptv', 'TMC', 'speed(mph)', 'numLanes', 'ltype'])
for row in cursor:
    parade_links[int(row[0])] = row[2:]
    parade_to_ptv[int(row[0])] = abs(int(row[1]))

metropia_to_ptv = {}  # int(metropia ID) : int(ptv ID) use this dict to update signs
for key, value in metropia_to_parade.items():
    metropia_to_ptv[key] = parade_to_ptv[value]

if add_tmc_field_to_OSM:
    arcpy.AddField_management(osm, 'TMC', "TEXT", field_length=15)

nodes_with_successors = {}  # node in format of (lat, lon) : metropia id
nodes_with_predecessors = {}  # node in format of (lat, lon) : metropia id
metropia_from_node = {}  # metropia ID : (lat,lon)
metropia_to_node = {}  # metropia ID : (lat,lon)
osm_ltypes = {}  # metropia ID : ltype
cursor = arcpy.da.UpdateCursor(osm, ['MetropiaID', 'speed', 'lane', 'TMC', 'SHAPE@', 'ltype'])
for row in cursor:
    osm_ltypes[int(row[0])] = row[5]
    # Get the corresponding parade link
    if int(row[0]) in metropia_to_parade:
        paradeID = metropia_to_parade[int(row[0])]
        parade_link = parade_links[paradeID]
        parade_ltype = parade_link[3]
        parade_lanes = parade_link[2]
        parade_speed = parade_link[1]
        parade_tmc = parade_link[0]
        if parade_tmc != ' ' and (row[5] == '1' or row[5] == '3' or row[5] == '5' or row[5] == '7'):
            row[3] = parade_tmc

        # now we need to update the nodes dictionary, for later use when comparing source, destination links in signs
        lat = float(row[4].firstPoint.Y)
        lon = float(row[4].firstPoint.X)
        # if this node is already in the nodes dictionary, add current link as a successor
        if (lat, lon) in nodes_with_successors:
            nodes_with_successors[(lat, lon)].append(int(row[0]))
            metropia_from_node[int(row[0])] = (lat, lon)
        # else we need to initialize it in the dict
        # note that this successor dictionary does not take into account turn restrictions
        else:
            nodes_with_successors[(lat, lon)] = [int(row[0])]
            metropia_from_node[int(row[0])] = (lat, lon)
        lat = float(row[4].lastPoint.Y)
        lon = float(row[4].lastPoint.X)
        if (lat, lon) in nodes_with_predecessors:
            nodes_with_predecessors[(lat, lon)].append(int(row[0]))
            metropia_to_node[int(row[0])] = (lat, lon)
        else:
            nodes_with_predecessors[(lat, lon)] = [int(row[0])]
            metropia_to_node[int(row[0])] = (lat, lon)
        cursor.updateRow(row)
del cursor
# challenge with signs is that we are given a mapping table of metropia ID : ptv ID and a signs table using ptv ids
# but there might be multiple metropia links assigned to one ptv ID, and that ID might have a sign
# how can we know which metropia ID to assign it to?
# Solution: Need to run through every metropia link that has a ptv ID with a sign
# Then check to see if any of that links successors = the destination link
# if so, this is where the sign should be placed
# otherwise

sign_data = {}  # (int(source link), int(destination link)) : [[sign data including source link],[sign2]
with open(signs, 'rb') as infile:
    reader = csv.reader(infile, delimiter='\t')
    sign_headers = next(reader)
    for row in reader:
        if (int(row[0]), int(row[1])) in sign_data:
            sign_data[int(row[0]), int(row[1])].append(row)
        else:
            sign_data[int(row[0]), int(row[1])] = [row]

new_sign_data = {}  # (source ID, destination ID) : [[sign data including source link, but using metropia IDs],[sign2]]
for key, value in metropia_to_ptv.items():
    to_node = metropia_to_node[key]
    if to_node in nodes_with_successors:
        successors = nodes_with_successors[to_node]
        for each in successors:
            if (value, metropia_to_ptv[each]) in sign_data:
                if osm_ltypes[each] == '3':
                    temp_signs = sign_data[(value, metropia_to_ptv[each])]
                    for s in temp_signs:
                        if (key, each) in new_sign_data:
                            new_sign_data[(key, each)].append([key, each] + s[2:])
                        else:
                            new_sign_data[(key, each)] = [[key, each] + s[2:]]


out_signs = signs[:-4] + '_updated.tsv'  # [:-4] removes the .tsv
writer = csv.writer(open(out_signs, 'wb'), delimiter='\t')
writer.writerow(sign_headers)
for key, value in new_sign_data.items():
    for each in value:
        writer.writerow(each)

print time.ctime()
EndTime = time.clock()
print "Updating finished in %s seconds" % (EndTime - StartTime)

'''
TODO: take highway tag into account when matching signs
source link shouldnt be ltype 3
shouldnt have a source link and destination link that are both ltype 1
'''