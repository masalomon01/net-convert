import xml.etree.cElementTree as cElementTree
import pg8000 as pg
import csv


def get_osmid_in_network(city):
    conn = pg.connect(user='will',
                      password='will1234',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    query = "SELECT osmid FROM {} WHERE osmid IS NOT NULL".format(city)
    cursor.execute(query)
    results = cursor.fetchall()
    return {row[0] for row in results}


def read_osm_data(filepath, links_in_network):
    context = cElementTree.iterparse(filepath, events=("start", "end"))
    context = iter(context)
    event, root = next(context)
    osm_lanes = {}  # osmid : lane
    osm_speeds = {}  # osmid : speed

    for event, elem in context:
        if event == 'end' and elem.tag == 'way':
            osmid = int(elem.get('id'))
            if osmid not in links_in_network:
                continue
            iterator = iter(elem)
            speed = None
            lane = None
            lane_forward = None
            lane_backward = None  # osm puts lanes in 3 diff attributes
            is_oneway = False

            for child in iterator:
                if child.get('k') == 'maxspeed':
                    try:
                        speed = int(child.get('v')[:2])  # shouldnt have triple digit speeds and this cuts off the mph at end
                    except ValueError:
                        pass  # occurs when there is an unusual character in the speed field
                elif child.get('k') == 'lanes':
                    try:
                        lane = int(child.get('v'))
                    except ValueError:
                        pass
                elif child.get('k') == 'lanes:forward':
                    try:
                        lane_forward = int(child.get('v'))
                    except ValueError:
                        pass
                elif child.get('k') == 'lanes:backward':
                    try:
                        lane_backward = int(child.get('v'))
                    except ValueError:
                        pass

                if child.get('k') == 'oneway' and child.get('v') == 'yes':
                    is_oneway = True

            if speed is not None:
                osm_speeds[osmid] = speed
            if lane is not None and is_oneway:  # the lane attribute typically captures both directions so only use if oneway road
                osm_lanes[osmid] = lane
            elif lane_forward is not None and lane_forward == lane_backward:  # use this attribute for 2 way streets
                osm_lanes[osmid] = lane


        root.clear()
    return osm_lanes, osm_speeds


def compare_database_to_osm(city, osm_lanes, osm_speeds, speed_diff_writer):
    conn = pg.connect(user='will',
                      password='will1234',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    query = "SELECT osmid, lane, speed FROM {} WHERE osmid IS NOT NULL AND (lane is not null or speed is not null)".format(city)
    cursor.execute(query)
    results = cursor.fetchall()
    old_lane = {}
    old_speed = {}

    lane_updates = {}
    speed_updates = {}
    for row in results:
        if row[1] != None:
            old_lane[row[0]] = row[1]
        if row[2] != None:
            old_speed[row[0]] = row[2]

    for osmid, lane in osm_lanes.items():
        try:
            old_data = old_lane[osmid]
            if old_data != lane:
                print 'osmid {} has {} lane in database and {} in latest osm map'.format(osmid, old_data, lane)
        except KeyError:
            # occurs when database doesnt have this info
            lane_updates[osmid] = lane

    for osmid, speed in osm_speeds.items():
        try:
            old_data = old_speed[osmid]
            if old_data != speed:
                speed_diff_writer.writerow([osmid, old_data, speed])
        except KeyError:
            # occurs when database doesnt have this info
            speed_updates[osmid] = speed

    return lane_updates, speed_updates


def update_database(city, lane_updates, speed_updates):
    conn = pg.connect(user='will',
                      password='will1234',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()

    for osmid, new_lane in lane_updates.items():
        query = "UPDATE {} SET lane = {} WHERE osmid = {}".format(city, new_lane, osmid)
        print(query)



def main():
    city_name = 'austin'
    folder = 'D:/Will/GIS Data/Raw OSM Data/Austin/2017/'
    in_file = folder + 'austin_1-4-2017.osm'
    difference_file = folder + 'speed_differences.csv'
    writer1 = csv.writer(open(difference_file, 'wb'))
    writer1.writerow(['osmid', 'database_speed', 'latest_osm_speed'])

    links = get_osmid_in_network(city_name)
    lane_data, speed_data = read_osm_data(in_file, links)

    lanes_to_change, speed_to_change = compare_database_to_osm(city_name, lane_data, speed_data, writer1)
    update_database(city_name, lanes_to_change, speed_to_change)


if __name__ == '__main__':
    main()


