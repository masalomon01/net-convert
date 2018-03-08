# This program will read the PostGIS enabled network database of links
# It will output network - link, network - node, and LinkXY, Abbieger, Signs,
import pg8000 as pg
import math
import unicodecsv as csv
import operator
from dbfpy import dbf
import time
import os
import sys
import config


def read_signal_locations(city_name, cur):
    q = "SELECT gid FROM {} WHERE ST_EndPoint(geom) IN " \
            "(SELECT geom FROM {}_nodes WHERE type='traffic_signal')".format(city_name, city_name)
    cur.execute(q)
    return {r[0] for r in cursor.fetchall()}



def read_sys_args(args):
    try:
        folder_path = args[1]
        city = args[2]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be a path to folder and arg2 should be city name')
    if folder_path[-1] != '/':
        folder_path += '/'
    return folder_path, city


# returns a nested list of [[latitude1,longitude1],[latitude2,longitude2],...]
# should instead retrieve the geometry in binary and use shapely.wkb to load
def parse_linestring(wkt):
    stripped = wkt[11:-1]
    points = stripped.split(",")
    point_list = []
    for p in points:
        longlat = p.split(" ")
        lon = longlat[0]
        lat = longlat[1]
        temp = [lat, lon]
        point_list.append(temp)
    return point_list


# input is list of list of the coordinates
# outputs length of the multilinestring in feet
def calc_length(coordinates):
    leng = 0
    coord1 = coordinates[0]
    for x in coordinates[1:]:
        coord2 = x
        leng += dist_from_to(str(coord1[0]), str(coord1[1]), str(coord2[0]), str(coord2[1]))
        coord1 = coord2
    return leng


# dist_from_to will return the distance between two points in feet
def dist_from_to(lat1, lng1, lat2, lng2):
    earthradius = 3958.75
    dlat = math.radians(float(lat2)-float(lat1))
    dlng = math.radians(float(lng2)-float(lng1))
    sin_dlat = math.sin(dlat/2)
    sin_dlng = math.sin(dlng/2)
    a = math.pow(sin_dlat, 2) + math.pow(sin_dlng, 2) * math.cos(math.radians(float(lat1)))\
        * math.cos(math.radians(float(lat2)))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist = earthradius * c
    dist *= 5280
    return dist


# Returns a string of the coordinates in the format of network - link
def coords_to_string(coord_list):
    number_points = str(len(coord_list))
    f_list = [number_points]
    for point in coord_list:
        # Make sure coordinates are proper lengths b/c parade divides by a million to get decimal in correct spot
        # It is because of a bug in dynuStudio which removed decimal points from coordinates
        # Rather than fix the bug, parade decided to roll with it...
        # This lazy hack will not work with a city that is on the border of a 2 digit and 3 digit lat/lon
        if float(point[1]).is_integer():
            point[1] += '.0'
        if float(point[0]).is_integer():
            point[0] += '.0'
        while len(point[1]) < longitude_length:
            point[1] += '0'  # 0 is after the decimal so shouldnt change data
        while len(point[0]) < 9:
            point[0] += '0'
        while len(point[1]) > longitude_length:
            point[1] = point[1][:-1]  # Remove last character and keep looping
        while len(point[0]) > 9:
            point[0] = point[0][:-1]
        remove = set('.')
        point[1] = ''.join(ch for ch in point[1] if ch not in remove)  # efficiently remove . in the coord
        point[0] = ''.join(ch for ch in point[0] if ch not in remove)
        f_list.append(point[1])
        f_list.append(point[0])  # add long then lat b/c our formatting is x,y
    return f_list


if __name__ == '__main__':
    print '...'
    start_time = time.time()
    conn = pg.connect(user=config.NETWORKLAND_USER, password=config.NETWORKLAND_PASSWORD, host=config.NETWORKLAND_URL, database=config.NETWORKLAND_DB)  # port default 5432
    cursor = conn.cursor()
    folder, city = read_sys_args(sys.argv)
    # folder, city = os.path.dirname(__file__), 'elpaso_juarez'  #for testing
    signalized_links = read_signal_locations(city, cursor)

    if city == "elpaso":
        query = "SELECT gid,ST_AsText(geom),speed,lane,ltype,street_name,tmc,category,toll,special_type FROM " + city
    else:
        query = "SELECT gid,ST_AsText(geom),speed,lane,street_name,tmc,toll,highway,special_type, time_depen, osmid, elevation, access FROM {} WHERE ST_Intersects(geom,(SELECT geom FROM {}_polygons WHERE name='service area'))".format(city, city)

    if city in ['austin', 'newyork', 'houston']:
        longitude_length = 10
    elif city in ['elpaso', 'arizona', 'tucson', 'la', 'elpaso_juarez', 'taiwan']:
        longitude_length = 11

    cursor.execute(query)
    print 'data selected'
    results = cursor.fetchall()
    print 'data fetched'
    nodes = {}  # "coordinates" : node ID
    old_nodes = {}  # "coordinate" : node ID
    links = {}
    xy = {}  # "fromNode-toNode" : "coordinates" in string
    toll_roads = {}  # gid : [von,nach,roadname,type]
    texas_uturn_links = {}  # gid : True
    intersection_links = {}  # gid : True
    roundabout_links = {}  # gid : True
    #here we add roundabout links
    # Loop through all links
    # Generate node dict
    current_node_id = 1
    for row in results:
        # TODO: temp patch
        if city == 'houston' and row[7] is None:
            row[7] = 'residential'
        # GET GEOMETRY OF POINT HERE
        geom = parse_linestring(row[1])
        # Check if first/last node are already in nodes
        # If they are, retrieve the node ID's
        # If not, add them to nodes and save the ID's
        first_point = geom[0]  # this is from node
        last_point = geom[-1]  # this is to node
        lat_lng1 = first_point[0] + '&' + first_point[1]
        from_node = 0

        if lat_lng1 in nodes:
            from_node = nodes[lat_lng1]
        else:
            nodes[lat_lng1] = current_node_id
            from_node = current_node_id
            current_node_id += 1
        lat_lng2 = last_point[0] + '&' + last_point[1]
        to_node = 0
        if lat_lng2 in nodes:
            to_node = nodes[lat_lng2]
        else:
            nodes[lat_lng2] = current_node_id
            to_node = current_node_id
            current_node_id += 1
        # At this point we have from/to nodes and a nodes dictionary built
        # Now we need to build the links dictionary
        length = calc_length(geom)
        if length == 0:
            print str(row[0]) + ' has a length of 0'
        # Now fill in default values for roads with no speed limits
        speed_default = {'motorway': 65, 'motorway_link': 45, 'trunk': 55, 'trunk_link': 35, 'primary': 45, 'secondary': 35,
                         'tertiary': 30, 'primary_link': 25, 'secondary_link': 25, 'tertiary_link': 25, 'residential': 15,
                         'living_street': 15, 'service': 5, 'track': 15, 'road': 20, 'unclassified': 18, 'parking': 5,
                         'alley': 4}

        lane_default = {'motorway': 3, 'motorway_link': 1, 'trunk': 2, 'trunk_link': 1, 'primary': 2, 'secondary': 2,
                         'tertiary': 1, 'primary_link': 1, 'secondary_link': 1, 'tertiary_link': 1, 'residential': 1,
                         'living_street': 1, 'service': 1, 'track': 1, 'road': 1, 'unclassified': 1, 'parking': 1,
                        'alley': 1}

        new_ltype = {'motorway': 1, 'motorway_link': 3, 'trunk': 2, 'trunk_link': 3, 'primary': 4, 'secondary': 5,
                     'tertiary': 6, 'primary_link': 4, 'secondary_link': 5, 'tertiary_link': 6, 'residential': 8,
                     'living_street': 8, 'service': 10, 'track': 10, 'road': 8, 'unclassified': 10, 'parking': 11,
                     'alley': 10}

        old_ltype = {'motorway': 1, 'motorway_link': 3, 'trunk': 7, 'trunk_link': 3, 'primary': 5, 'secondary': 5,
                     'tertiary': 5, 'primary_link': 5, 'secondary_link': 5, 'tertiary_link': 5, 'residential': 11,
                     'living_street': 11, 'service': 11, 'track': 11, 'road': 11, 'unclassified': 11, 'parking': 11,
                     'alley': 11}

        category = {'motorway': 1, 'motorway_link': 3, 'trunk': 4, 'trunk_link': 3, 'primary': 5, 'secondary': 5,
                     'tertiary': 5, 'primary_link': 5, 'secondary_link': 5, 'tertiary_link': 5, 'residential': 6,
                     'living_street': 7, 'service': 8, 'track': 7, 'road': 7, 'unclassified': 8, 'parking': 8,
                    'alley': 8}
        if city != 'elpaso':
            if row[2] == '' or row[2] is None:  # if no speed value use the highway tag for a default
                row[2] = speed_default[row[7]]
            if row[3] == '' or row[3] is None:
                row[3] = lane_default[row[7]]

        # need to not have , in the road name
        try:
            name = row[4].replace(',', '').replace('\n', ' ').strip()

        except AttributeError:
            name = None
        if city == 'elpaso':
            links[str(row[0])] = [from_node, to_node, row[5], length, row[4], row[3], row[2], '', row[6], row[7],
                              '6', from_node, to_node, row[4]]
        else:
            links[str(row[0])] = [from_node, to_node, name, length, str(old_ltype[row[7].lower()]), row[3], row[2], '', row[5], str(category[row[7]]),
                              '6', from_node, to_node, str(new_ltype[row[7]]), row[10], row[11], row[12]]  # insert 6 for all styles, it doesnt really matter

            # lazy way to allow us to manually set some residential roads as time dependent (useful in manhattan)
            if row[9] == True and row[6] == 'residential':
                links[str(row[0])][9] = 5
        if city != 'elpaso':
            if row[8] == 'texas_uturn':
                texas_uturn_links[str(row[0])] = True
            elif row[8] == 'intersection':
                intersection_links[str(row[0])] = True
            elif row[8] == 'roundabout': #logic to find roundabout links IS_ROUNDABOUT
                roundabout_links[str(row[0])] = True
        else:
            if row[9] == 'texas_uturn':
                texas_uturn_links[str(row[0])] = True
            elif row[9] == 'intersection':
                intersection_links[str(row[0])] = True
            elif row[8] == 'roundabout': #logic to find roundabout links IS_ROUNDABOUT
                roundabout_links[str(row[0])] = True
        # Now need to generate an xy dictionary to contain number of points
        # Also create a dict that contains all the coordinates

        if len(geom) > 2:
            # create string of from/to node sequence

            node_seq = str(from_node) + '^' + str(to_node)
            # slice list of coordinates to remove from/to node
            coords = geom[1:-1]
            xy[node_seq] = coords_to_string(coords)
        # At this point nodes, links, xy should contain all data needed for network - link network - node and LinkXY
        # Now generate toll roads
        if row[6] in [1, 2, 3]:
            try:
                toll_roads[row[0]] = [str(from_node), str(to_node), name, str(row[6])]
            except UnicodeEncodeError:
                print 'Unicode error on the following gid', row[0]

    out_nodes = open(folder + 'network - node.csv', 'wb')
    out_links = open(folder + 'network - link.csv', 'wb')
    out_XY = open(folder + 'LinkXY.csv', 'wb')
    out_restrictions = open(folder + 'Abbieger.csv', 'wb')
    out_signs = open(folder + 'Signs.tsv', 'wb')
    out_toll = open(folder + 'toll_hov_hot.csv', 'wb')
    out_boundary = open(folder + city + '_polygon.json', 'wb')
    out_tdtr = open(folder + 'network - TDTR.csv','wb')
    out_strassen = open(folder + 'Strassen.csv','wb')
    out_penalties = open(folder + 'Link_Penalties.csv','wb')
    node_writer = csv.writer(out_nodes)
    node_writer.writerow(['NODE_ID(f0)', 'X_COORD(f0)', 'Y_COORD(f0)', '#NEW_ID(f0)'])
    link_writer = csv.writer(out_links)
    link_writer.writerow(['A_NODE(f0)', 'B_NODE(f0)', '#STREET(c20)', '#LENGTH(f0)', '#LTYPE(f0)', '#LANES(f0)',
                          '#SPEED(f0)', 'Sec_Name(c16)', 'TMC(c16)', 'Category(f0)', 'Style(f0)', 'VON(f0)', 'NACH(f0)',
                          'new_ltype', 'OSMID', 'Elevation', 'Access', 'IS_INTERSECTION', 'IS_TEXAS_U_TURN', 'IS_ROUNDABOUT',
                          'SIGNAL_TYPE'])

    xy_writer = csv.writer(out_XY)
    xy_writer.writerow(['#LINKXY, 21987, 145, 0, MOTHR, 0.000000, 8, 2,ANODE,BNODE,POINTS,X1,Y1,X2,Y2,X3,Y3,X4,Y4,'
                        'X5,Y5,X6,Y6,X7,Y7,X8,Y8,X9,Y9,X10,Y10,X11,Y11,X12,Y12,X13,Y13,X14,Y14,X15,Y15,X16,Y16,X17,'
                        'Y17,X18,Y18,X19,Y19,X20,Y20,X21,Y21,X22,Y22,X23,Y23,X24,Y24,X25,Y25,X26,Y26,X27,Y27,X28,'
                        'Y28,X29,Y29,X30,Y30,X31,Y31,X32,Y32,X33,Y33,X34,Y34,X35,Y35,X36,Y36,X37,Y37,X38,Y38,X39,'
                        'Y39,X40,Y40,X41,Y41,X42,Y42,X43,Y43,X44,Y44,X45,Y45,X46,Y46,X47,Y47,X48,Y48,X49,Y49,X50,'
                        'Y50,X51,Y51,X52,Y52,X53,Y53,X54,Y54,X55,Y55,X56,Y56,X57,Y57,X58,Y58,X59,Y59,X60,Y60,X61,'
                        'Y61,X62,Y62,X63,Y63,X64,Y64,X65,Y65,X66,Y66,X67,Y67,X68,Y68,X69,Y69,X70,Y70,X71,Y71'])
    xy_writer.writerow(['Link shape points'])
    restriction_writer = csv.writer(out_restrictions)
    sign_writer = csv.writer(out_signs, delimiter='\t')
    sign_writer.writerow(['Source_LinkID', 'Destination_LinkID', 'Sign_ID', 'Seq_Number', 'Exit_Number', 'Exit_LangCd',
                          'ExitNum_Tr', 'Alt_Ex_Num', 'Branch_RouteID', 'BrRte_Tr', 'Branch_RouteDir',
                          'Sign_TextType', 'Sign_Text', 'Lang_Code', 'SignTxt_Tr', 'Trans_Type', 'Toward_RouteID',
                          'TowRte_Tr', 'Straight_On'])
    toll_writer = csv.writer(out_toll)
    toll_writer.writerow(['VON', 'NACH', 'Roadname', 'Type'])
    tdtr_writer = csv.writer(out_tdtr)
    tdtr_writer.writerow(['node1', 'node2', 'node3', 'restriction'])
    strassen_writer = csv.writer(out_strassen)
    strassen_writer.writerow(['PRIM_NAME', 'SEK_NAME', 'KAT', 'VON', 'NACH', 'LAENGE', 'RICHTUNG', 'RESTRIKTIO', 'FROMLEFT', 'TOLEFT',
                              'FROMRIGHT', 'TORIGHT', 'ID', 'STIL', 'FUSSWEG', 'FUSS_ZONE', 'HN_INFO', 'SPURHIN', 'SPURRUECK',
                              'TYPHIN', 'TYPRUECK', 'KM_HHIN', 'KM_HRUECK', 'LEVEL', 'KAT_PRE', 'TMC_POS_TM', 'TMC_NEG_TM'])
    penalties_writer = csv.writer(out_penalties)
    penalties_writer.writerow(['Von', 'Nach', 'Penalty', 'Note'])
    # Loop through in order of the values so that the node IDs start at 1 in the output file
    for key, value in sorted(nodes.items(), key=operator.itemgetter(1)):
        formatted_list = [value]
        lat_lng = key.split('&')
        # Again format lengths...
        if float(lat_lng[0]) % 1 == 0:  # handles an edge case where the lat or long doesnt have a decimal and is exactly 32
            lat_lng[0] += '.0'
        if float(lat_lng[1]) % 1 == 0:
            lat_lng[1] += '.0'
        while len(lat_lng[1]) < longitude_length:
            lat_lng[1] += '0'  # 0 is after the decimal so shouldnt change data
        while len(lat_lng[0]) < 9:
            lat_lng[0] += '0'
        while len(lat_lng[1]) > longitude_length:
            lat_lng[1] = lat_lng[1][:-1]  # Remove last character and keep looping
        while len(lat_lng[0]) > 9:
            lat_lng[0] = lat_lng[0][:-1]
        exclude = set('.')
        lon = ''.join(ch for ch in lat_lng[1] if ch not in exclude)  # remove . in the coord
        exclude = set('.')
        lat = ''.join(ch for ch in lat_lng[0] if ch not in exclude)  # remove . in the coord
        node_writer.writerow([value, lon, lat, value])

    # Loop through links and write data to network - link.csv
    # Also need to create dbf which is just used as a lookup table of id, von, nach
    # Also create linkFromNode and linkToNode for later use
    link_from_node = {}
    link_to_node = {}
    db = dbf.Dbf(folder + 'Strassen.dbf', new=True)
    f1 = ('Prim_Name', "C", 13)
    f2 = ('Sek_Name', "C", 13)
    f3 = ('Kat', "C", 13)
    f4 = ('Von', "C", 13)
    f5 = ('Nach', "C", 13)
    f6 = ('Laenge', "C", 13)
    f7 = ('Richtung', "C", 13)
    f8 = ('Restriktio', "C", 13)
    f9 = ('FromLeft', "C", 13)
    f10 = ('ToLeft', "C", 13)
    f11 = ('FromRight', "C", 13)
    f12 = ('ToRight', "C", 13)
    f13 = ('ID', "C", 13)
    f14 = ('Stil', "C", 13)
    f15 = ('Fussweg', "C", 13)
    f16 = ('Fuss_zone', "C", 13)
    f17 = ('HN_Info', "C", 13)
    f18 = ('SpurHin', "C", 13)
    f19 = ('SpurRueck', "C", 13)
    f20 = ('TypHin', "C", 13)
    f21 = ('TypRueck', "C", 13)
    f22 = ('km_hHin', "C", 13)
    f23 = ('km_hRueck', "C", 13)
    f24 = ('Level', "C", 13)
    f25 = ('Kat_pre', "C", 13)
    f26 = ('TMC_POS_TM', "C", 13)
    f27 = ('TMC_NEG_TM', "C", 13)
    db.addField(f1)
    db.addField(f2)
    db.addField(f3)
    db.addField(f4)
    db.addField(f5)
    db.addField(f6)
    db.addField(f7)
    db.addField(f8)
    db.addField(f9)
    db.addField(f10)
    db.addField(f11)
    db.addField(f12)
    db.addField(f13)
    db.addField(f14)
    db.addField(f15)
    db.addField(f16)
    db.addField(f17)
    db.addField(f18)
    db.addField(f19)
    db.addField(f20)
    db.addField(f21)
    db.addField(f22)
    db.addField(f23)
    db.addField(f24)
    db.addField(f25)
    db.addField(f26)
    db.addField(f27)

    for key, value in links.iteritems():
        rec = db.newRecord()
        rec['ID'] = key
        rec['Von'] = value[0]
        rec['Nach'] = value[1]
        rec['Kat'] = value[9]
        rec['Stil'] = value[10]
        rec['Richtung'] = '1'
        rec['TypHin'] = value[5]
        rec['TypRueck'] = value[5]
        rec.store()
        link_from_node[key] = value[0]
        link_to_node[key] = value[1]
        row_to_write = value
        # texas uturn, intersection and roundabout should be mutually exclusive, maybe in future combine into single column
        if key in texas_uturn_links:  # this is where we add 1 for IS_ROUNDABOUT
            row_to_write += ['0', '1', '0']
        elif key in intersection_links:
            row_to_write += ['1', '0', '0']
        elif key in roundabout_links:
            row_to_write += ['0', '0', '1']
        else:
            row_to_write += ['0', '0', '0']

        if int(key) in signalized_links:
            row_to_write += ['traffic_light']
        else:
            row_to_write += ['0']
        link_writer.writerow(row_to_write)
        strassen_writer.writerow(['', '', value[9], value[0], value[1], '', '1', '', '', '', '', '', key, '6', '', '',
                                  '', '', '', '1', '1', '', '', '', '', '', ''])
    db.close()
    # Loop through XY and write data to LinkXY.csv
    for key, value in xy.iteritems():
        from_to_nodes = key.split('^')
        xy_writer.writerow(from_to_nodes + value)

    # Now need to generate Abbieger.csv
    # There should be a table containing necessary data

    query = "SELECT from_link,to_link FROM " + city + "_abbieger"
    cursor.execute(query)
    results = cursor.fetchall()
    for restriction in results:
        from_link = str(restriction[0])
        to_link = str(restriction[1])
        if from_link in link_from_node and to_link in link_from_node:
            through_node = link_from_node[to_link]
            if link_from_node[to_link] != link_to_node[from_link]:
                print str(restriction) + " from and to nodes do not match"
            else:
                restriction_writer.writerow([from_link, str(through_node), to_link, '1'])

    query = 'SELECT "source_link","destination_link","exit_number","Branch_RouteID","Branch_RouteDir","Sign_TextType","Sign_Text","Toward_RouteID","Straight_On" FROM ' + city + "_signs"
    cursor.execute(query)
    results = cursor.fetchall()
    for row in results:
        from_link = str(row[0])
        to_link = str(row[1])
        try:
            if link_from_node[to_link] != link_to_node[from_link]:
                print str(row) + ' from and to nodes do not match!'
            else:
                new = [str(row[0]), str(row[1]), '', '', row[2], '', '', '', row[3], '', row[4], row[5], row[6], '', '', '',
                           row[7], '', row[8]]  # sign table that is read by topology needs a bunch of blank fields for some reason
                sign_writer.writerow(new)
        except KeyError:
            print str(row) + ' has a link ID that does not exist in network'


    for key, value in toll_roads.iteritems():
        toll_writer.writerow(value)


    query = "SELECT ST_AsGeoJSON(geom) FROM {}_polygons WHERE type='boundary'".format(city)
    cursor.execute(query)
    results = cursor.fetchall()
    for row in results:
        out_boundary.write(row[0])

    query =  "SELECT from_link, to_link, monday, tuesday, wednesday, thursday, friday, saturday, sunday, from_time1, to_time1, from_time2, to_time2 FROM {}_tdtr".format(city)
    cursor.execute(query)
    results = cursor.fetchall()
    for row in results:
        try:
            node1 = str(link_from_node[str(row[0])])  # for some reason I stored all the keys as strings previously
            node2 = str(link_to_node[str(row[0])])
            node3 = str(link_to_node[str(row[1])])

            if str(link_from_node[str(row[1])]) != node2:  # checking for connectivity issue on this restriction
                print 'Connectivity issue on TDTR from link {} to link {}'.format(row[0],row[1])
                continue

            restr_str = ''
            for item in row[2:9]:
                if item == True:
                    restr_str += '1'
                else:
                    restr_str += '0'
            for item in row[9:13]:
                if item:
                    restr_str += ','
                    restr_str += str(item)
            tdtr_writer.writerow([node1, node2, node3, restr_str])
        except KeyError:
            print 'Bad ID in TDTR: ' + str(row)

    os.mkdir(folder+city)

    print("Elapsed time... %s seconds" % (time.time() - start_time))
