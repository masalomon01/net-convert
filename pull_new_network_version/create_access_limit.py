import pg8000 as pg
import csv, sys, os, json

def read_sys_args(args):
    try:
        #folder_path = os.getcwd()
        #city_name = 'austin'
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
        parade_id = int(row['LinkID_parade'])
        gid = int(row['LinkID_ptv'])
        gid_to_parade[gid] = parade_id


def read_access(city_name, id_mapping):
    conn = pg.connect(user='read_only',
                      password='only4metropians',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    query = "SELECT gid, access FROM {} WHERE access is not NULL and access != '' ".format(city_name)
    cursor.execute(query)
    results = cursor.fetchall()
    pov_links, sentri_links, cargo_links = set(), set(), set()
    for each in results:
        try:
            if each[1] == 'pov':
                pov_links.add(id_mapping[each[0]])
            elif each[1] == 'sentri':
              sentri_links.add(id_mapping[each[0]])
            elif each[1] == 'cargo':
              cargo_links.add(id_mapping[each[0]])
            else:
              print 'read-access has a bad entry check the following db link', each
        except KeyError:
            # occurs when link is added to network database after the creation of wkt
            pass

    return pov_links, sentri_links, cargo_links


def read_toll(city_name, id_mapping):
    conn = pg.connect(user='read_only',
                      password='only4metropians',
                      host='postgresql.crvadswmow49.us-west-2.rds.amazonaws.com',
                      database='Networkland')  # port default 5432
    cursor = conn.cursor()
    query = "SELECT gid, toll FROM {} WHERE toll is not NULL AND toll != 0".format(city_name)
    cursor.execute(query)
    results = cursor.fetchall()
    toll_links = set()
    for each in results:
        try:
            if each[1] == 1:
                toll_links.add(id_mapping[each[0]])
            else:
              print 'there is another entry here that is not NULL or 0', each
        except KeyError:
            # occurs when link is added to network database after the creation of wkt
            pass

    return toll_links


def write_json(toll, pov, sentri, cargo, folder):
  data = {}
  data['toll'] = list(toll)
  data['pov'] = list(pov)
  data['sentri'] = list(sentri)
  data['cargo'] = list(cargo)
  out_access = folder + 'access_limit.json'
  with open(out_access, 'wb') as outfile:  
    json.dump(data, outfile)
    print 'wrote file here', folder


if __name__ == '__main__':
  print 'creating access_limit'
  folder, city = read_sys_args(sys.argv)
  in_folder = folder + '{}/'.format(city)
  in_wkt = in_folder + 'links_wkt.csv'
  gid_to_parade = {}
  read_wkt(in_wkt)
  pov, sentri, cargo = read_access(city, gid_to_parade)
  toll = read_toll(city, gid_to_parade)
  write_json(toll, pov, sentri, cargo, folder)


