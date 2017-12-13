import csv


def read_parade(file_path):
    link_attributes = {}  # linkID : [speed, ltype, street]
    with open(file_path, 'rb') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            link_id = int(row['Link_ID']) - 1 # subtract 1 to match the ID number in the other two files
            speed = row['#SPEED']
            ltype = row['#LTYPE']
            street = row['#STREET']
            link_attributes[link_id] = [speed, ltype, street]
    return link_attributes

def read_zones(file_path):
    link_zones = {}  # linkID : zone
    with open(file_path, 'rb') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            link_id = int(row['LinkID_parade'])
            zone = row['zone']
            link_zones[link_id] = zone
    return link_zones


if __name__ == '__main__':
    folder = 'D:/Will/Metropia/Network Updates/New York/Update 6-28-2016/'
    in_table = folder + 'NY mapping table.csv'
    in_links = folder + 'output_Link1.csv'
    in_zone_table = folder + 'parade gid zone.csv'
    out_table = folder + 'extra_TD_links.csv'

    link_attributes = read_parade(in_links)
    link_zones = read_zones(in_zone_table)

    with open(in_table, 'rb') as infile, open(out_table,'wb') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.writer(outfile)
        writer.writerow(['LinkID_parade', 'speed(mph)', 'ltype', 'primaryName', 'areaID'])
        exclude = ['0', '1', '2', '3', '4', '5']  # we don't want to include links with these sources
        for row in reader:
            if row['source'] not in exclude:
                link_id = int(row['link id'])
                attributes = link_attributes[link_id]
                zone = link_zones[link_id]
                writer.writerow([link_id]+attributes+[zone])

