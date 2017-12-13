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


def dist_from_to(lat1, lng1, lat2, lng2):
    # returns distance in feet
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


#  +150   ^   -150
#     \   |   /
#      \  |  /
#       \ | /
#        \|/
# +90 ----|---- -90
#        /|\
#       / | \
#      /  |  \
#     /   |   \
#   +30   0   -30
def calc_angle(link1, link2, link_geom):
    '''
    see http://stackoverflow.com/questions/16180595/find-the-angle-between-two-bearings for math details
    Some links have sharp angle at very end of link that incorrectly throws off angle calculations
    We want to identify and ignore feature points that do this
    We will ignore the last feature point if the following conditions are met
    1.  Number of feature points > 2 (including from/to nodes as a feature point)
    2.  Distance between second to last feature point and last is less than 60 feet (exact number subject to change)

    '''
    from_geom = link_geom[link1]
    to_geom = link_geom[link2]
    ignore = True

    number_fp = len(from_geom)
    if number_fp <= 2:  # not enough feature points so use standard angle calculation
        ignore = False

    # we will run into exceptions in next logic if there are only 2 feature points so do a quick check
    # need end bearing elsewhere so calculate it outside the block
    end_bearing = bearing(from_geom[-2][0], from_geom[-2][1], from_geom[-1][0], from_geom[-1][1])
    if ignore:
        # calculate distance between 2nd to last feature point and last feature point
        last_fp_lat = from_geom[-1][0]
        last_fp_lon = from_geom[-1][1]
        second_last_fp_lat = from_geom[-2][0]
        second_last_fp_lon = from_geom[-2][1]
        last_fp_distance = dist_from_to(last_fp_lat, last_fp_lon, second_last_fp_lat, second_last_fp_lon)
        if last_fp_distance > 60:  # feature points too far apart so use standard angle calc
            ignore = False

        # next compare how the bearing is affected by last feature point
        # feature points to ignore cause about 35 degree angle to the left
        end_bearing = bearing(second_last_fp_lat, second_last_fp_lon, last_fp_lat, last_fp_lon)
        prev_lat = from_geom[-3][0]
        prev_lon = from_geom[-3][1]
        prev_bearing = bearing(prev_lat, prev_lon, second_last_fp_lat, second_last_fp_lon)
        angle = ((((prev_bearing - end_bearing) % 360) + 540) % 360) - 180
        if not (angle > 15 and angle <= 50):
            ignore = False

        # next thing to check is the prev bearing should be about the same as the bearing in second link
        first_lat = to_geom[0][0]
        first_lon = to_geom[0][1]
        second_lat = to_geom[1][0]
        second_lon = to_geom[1][1]
        to_bearing = bearing(first_lat, first_lon, second_lat, second_lon)
        angle = ((((prev_bearing - to_bearing) % 360) + 540) % 360) - 180
        if abs(angle) > 20:
            ignore = False

        # from link bearing variable is the official bearing to use in angle calculation
        if ignore:
            from_link_bearing = prev_bearing
        else:
            from_link_bearing = end_bearing
    else:
        from_link_bearing = end_bearing

    # now we have to do all the same stuff but for the beginning of the to_link *sadface*
    ignore = True
    number_fp = len(to_geom)
    if number_fp <= 2:
        ignore = False

    first_bearing = bearing(to_geom[0][0], to_geom[0][1], to_geom[1][0], to_geom[1][1])
    if ignore:
        # distance between first/second feature pt
        first_lat = to_geom[0][0]
        first_lon = to_geom[0][1]
        second_lat = to_geom[1][0]
        second_lon = to_geom[1][1]
        distance = dist_from_to(first_lat, first_lon, second_lat, second_lon)
        if distance > 60:
            ignore = False

        first_bearing = bearing(first_lat, first_lon, second_lat, second_lon)
        third_lat = to_geom[2][0]
        third_lon = to_geom[2][1]
        second_bearing = bearing(second_lat, second_lon, third_lat, third_lon)
        angle = ((((first_bearing - second_bearing) % 360) + 540) % 360) - 180
        if not (angle > 15 and angle <= 50):
            ignore = False
        # second bearing should be about the same as previous link's end bearing
        difference = abs(((((second_bearing - end_bearing) % 360) + 540) % 360) - 180)
        if difference > 20:
            ignore = False

        if ignore == True:
            to_link_bearing = second_bearing
        else:
            to_link_bearing = first_bearing
    else:
        to_link_bearing = first_bearing

    return ((((from_link_bearing - to_link_bearing) % 360) + 540) % 360) - 180
