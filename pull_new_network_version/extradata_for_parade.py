import csv
import os
import sys


def read_sys_args(args):
    try:
        # folder_path = os.getcwd()
        # city_name = 'austin'
        folder_path = args[1]
        city_name = args[2]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be a path to folder and arg2 should be city name')
    if folder_path[-1] != '/':
        folder_path += '/'
    return folder_path, city_name


def read_wkt(infile):
    reader = csv.DictReader(open(infile, 'rb'))
    for row in reader:
        parade_id = int(row['LinkID_parade']) + 1
        # gid = int(row['LinkID_ptv'])
        first_o = float(row['firstOrientation(deg)'])
        last_o = float(row['lastOrientation(deg)'])
        parade_id_orientations[parade_id] = [first_o, last_o]


def add_orientation_to_link_files(folder):
    file1, file2 = folder + 'output_Link1.csv', folder + 'output_Link2.csv'
    files, temp_files = [file1, file2], [folder + 'output_Link1_temp.csv', folder + 'output_Link2_temp.csv']
    fieldnames = ['Link_ID', 'A_NODE', 'B_NODE', '#LENGTH', '#SPEED', '#LTYPE', '#STREET', 'Sec_Name', 'VON', 'NACH',
                  'TMC', 'original_Anode', 'original_Bnode', 'lane', 'category', 'style', 'trace_linkid', 'trace_Anode',
                  'trace_Bnode', 'new_ltype', 'firstOrientation(deg)', 'lastOrientation(deg)']
    for one, temp in zip(files, temp_files):
        # reader = csv.DictReader(open(one, 'rb')
        # writer = csv.DictWriter(open(temp, 'wb'), fieldnames=fieldnames)
        with open(one, 'rb') as r:
            reader = csv.DictReader(r)
            with open(temp, 'wb') as w:
                writer = csv.DictWriter(w, fieldnames=fieldnames)
                writer.writeheader()
                # print 'writing file', temp
                for row in reader:
                    link_id = int(row['Link_ID'])
                    if link_id in parade_id_orientations:
                        row['firstOrientation(deg)'] = parade_id_orientations[link_id][0]
                        row['lastOrientation(deg)'] = parade_id_orientations[link_id][1]
                        writer.writerow(row)
            w.close()
        r.close()
        os.remove(one)
        os.rename(temp, one)


if __name__ == '__main__':
    print 'adding data to links for parade'
    folder, city = read_sys_args(sys.argv)
    in_folder = folder + '{}/'.format(city)
    # city = 'elpaso'
    # folder = os.getcwd()
    # in_folder = folder + '\\' + city + '\\'
    in_wkt = in_folder + 'links_wkt.csv'
    parade_id_orientations = {}
    read_wkt(in_wkt)
    add_orientation_to_link_files(folder)
