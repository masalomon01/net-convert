import csv
import math


def angle_between_rad(from_bearing, to_bearing):
    out = math.radians(to_bearing) - math.radians(from_bearing)
    while out < -math.pi:
        out += (2 * math.pi)
    while out > math.pi:
        out -= (2 * math.pi)
    return out


def number_successors(successors):
    return len(successors.split(" ")[:-1])


def number_predecessors(predecessors):
    return len(predecessors.split(" ")[:-1])


def parse_linestring(wkt):
    stripped = wkt[12:-1]
    points = stripped.split(",")
    point_list = []
    for p in points:
        longlat = p.split(" ")
        if longlat[0] == '':
            longlat = longlat[1:]
        lon = float(longlat[0])
        lat = float(longlat[1])
        temp = [lat, lon]
        point_list.append(temp)
    return point_list


def bearing(slat, slong, elat, elong):
    startLat = math.radians(slat)
    startLong = math.radians(slong)
    endLat = math.radians(elat)
    endLong = math.radians(elong)
    dLong = endLong - startLong
    temp = math.tan(endLat/2.0+math.pi/4.0)/math.tan(startLat/2.0+math.pi/4.0)
    dPhi = math.log(temp)
    if abs(dLong) > math.pi:
        if dLong > 0.0:
            dLong = -(2.0 * math.pi - dLong)
        else:
            dLong = (2.0 * math.pi + dLong)

    b = (math.degrees(math.atan2(dLong, dPhi)) + 360.0) % 360.0
    return b


def isOneWay(link_id):
    if all_links[link_id]['reverseID_parade'] == '-1':
        return True
    else:
        return False


if __name__ == '__main__':
    folder = 'D:/Will/Metropia/Network Updates/Austin/Update 11-21-2016/austin/'
    in_wkt = folder + 'links_wkt.csv'
    out_file = folder + 'texas_uturn_links.csv'
    out_file2 = folder + 'texas_uturn_links_gid.csv'
    reader = csv.DictReader(open(in_wkt, 'rb'))
    writer = csv.writer(open(out_file, 'wb'))
    writer.writerow(['linkID', 'is_texas_uturn'])
    writer2 = csv.writer(open(out_file2, 'wb'))
    writer2.writerow(['gid', 'is_texas_uturn'])

    all_links = {}  # linkID_parade : {link_attribute_dict}
    uturn_links = []  # will hold link IDs of texas u turn links
    for row in reader:
        all_links[row['LinkID_parade']] = row

    for parade_id, row in all_links.iteritems():
        if number_predecessors(row['predecessors']) == 1 and number_successors(row['successors']) == 1:
            predecessor = row['predecessors'][:-1]  # fsr the wkt adds a space at the end of predecessors and successors
            successor = row['successors'][:-1]
            if isOneWay(predecessor) and isOneWay(successor):
                pred_points = parse_linestring(all_links[predecessor]['WKT'])
                succ_points = parse_linestring(all_links[successor]['WKT'])
                lat1 = succ_points[0][0]
                lon1 = succ_points[0][1]
                lat2 = succ_points[1][0]
                lon2 = succ_points[1][1]
                succ_bearing = bearing(lat1, lon1, lat2, lon2)

                lat1 = pred_points[-2][0]
                lon1 = pred_points[-2][1]
                lat2 = pred_points[-1][0]
                lon2 = pred_points[-1][1]
                pred_bearing = bearing(lat1, lon1, lat2, lon2)

                angle = abs(math.degrees(angle_between_rad(pred_bearing, succ_bearing)))
                acceptable_ltypes = {'5', '7'}
                # if the link basically takes the user on a u turn
                if abs(angle-180) < 15:
                    if len(parse_linestring(row['WKT'])) > 2 and all_links[successor]['ltype'] in acceptable_ltypes and all_links[predecessor]['ltype'] in acceptable_ltypes:  # texas u turns should always have feature points
                        writer.writerow([parade_id, '1'])
                        writer2.writerow([all_links[parade_id]['LinkID_ptv'], '1'])

"""
TODO:
Add parameter that the turn should be going left

"""