# This script will calculate the grade for every link based on the elevation of the link and its successor
# Elevation of a link = the elevation at the starting node. 
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


def get_elevation_dict(infile):
    # create a dict to reference elevation for successors later. 
    link_elevation_dict = {}
    reader = csv.DictReader(open(infile, 'rb'))
    for row in reader:
        gid = row['LinkID_ptv']
        link_elevation = int(row['Elevation'])
        link_elevation_dict[gid] = link_elevation
    return link_elevation_dict


def get_wkt(input_file):
    wkt = []
    with open(input_file, 'rb') as f:  # getting input data
        reader = csv.reader(f)
        wkt = list(reader)
    return wkt


def calculate_grade(wkt_lol, link_elevation_dict):
    headers = wkt_lol[0] + ['percent_Grade'] 
    new_wkt = [headers]
    for row in wkt_lol[1:]:
        gid, link_length, successors, cur_link_elevation = row[2], row[9], row[35], row[38]
        next_link = successors.split(' ')[0]
        # if there is no successors it means this is the last link, so there will be no grade
        if next_link == '':
            next_link = gid
        # get the elevation of the next link
        next_link_elevation = link_elevation_dict[next_link]
        # grade is calculated as percent slope =(rise/run) * 100
        link_grade = ((next_link_elevation - int(cur_link_elevation))/float(link_length)) * 100
        if abs(link_grade) >= 20:
            link_grade = 0
        new_wkt.append(row + [round(link_grade, 2)])
    return new_wkt


if __name__ == '__main__':
    print('generating grades on wkt_file')
    if len(sys.argv) < 2:                        # This is to test locally
        in_wkt = 'links_wkt.csv' 
    else:                                        # This part is for Jenkins
        folder, city = read_sys_args(sys.argv)
        in_folder = folder + '{}/'.format(city)
        in_wkt = in_folder + 'links_wkt.csv'

    link_elevation_dict = get_elevation_dict(in_wkt)
    wkt_data = get_wkt(in_wkt)
    new_wkt= calculate_grade(wkt_data, link_elevation_dict)
    # replace wkt file
    with open(in_wkt, 'wb') as f:
        writer = csv.writer(f)
        writer.writerows(new_wkt)