from pandas import read_csv
import json, os, time, datetime, pytz, math, csv, sys
import pg8000 as pg
import pandas as pd
import config


def read_sys_args(args):
	try:
		folder_path = args[1]
		city = args[2]
	except IndexError:
		raise IndexError('Incorrect inputs.  Arg1 should be a path to folder and arg2 should be city name')
	if folder_path[-1] != '/':
		folder_path += '/'
	return folder_path, city


def write_to_file(out_dict, filepath):
	#parent_dir = os.path.dirname(filepath)

	#if not os.path.exists(parent_dir):
	#    os.makedirs(parent_dir)
	json.dump(out_dict, open(filepath, 'wb'))


def write_to_csv(out_lol):
	with open("ports_links.csv", "wb") as f:
		writer = csv.writer(f)
		writer.writerows(out_lol)


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


def get_sequence(l, ls):
	seq, count = 1, 0
	while len(ls)+1 > len(l):
		last_node = l[-1][2]
		fl_node = l[-1][3]
		#print len(l), len(ls)
		for i in ls:
			#print last_node, i[3]
			if last_node == i[3] and fl_node != i[2]: #second part of logic is to avoid reverse links
				n = [i[0], i[1], i[2], i[3], seq, i[4]]
				l.append(n)
				seq = seq + 1
				last_node = i[2]
			else:
				continue
		count = count + 1
		if count > 20:
			break
	l = [(i[0], round(i[5], 3), i[2]) for i in l]
	check = []
	for e in l:
		if e not in check:
			check.append(e)
	return check


def get_gids(table):
	conn = pg.connect(user=config.NETWORKLAND_USER, password=config.NETWORKLAND_PASSWORD, host=config.NETWORKLAND_URL, database=config.NETWORKLAND_DB)  # port default 5432
	cursor = conn.cursor()
	city = 'elpaso_juarez'
	links_dict = {}
	for_db = []
	for index, row in ref_table.iterrows():
		query = "SELECT {}.gid,  {}.special_type, ST_AsText({}.geom), {}.access " \
			"FROM {}, {}_poe_segments " \
			"WHERE ST_INTERSECTS({}.geom, {}_poe_segments.geom) and {}_poe_segments.id in {} and {}.access in {} ".format(city, city, city, city, city, city, city, city, city, row['segment_id'], city, row['access'])
		cursor.execute(query)
		results = cursor.fetchall()
		links = []
		gids = []
		for i in results:
			geom = parse_linestring(i[2])
			length = calc_length(geom)
				# Get first/last nodes
			first_point = geom[0]  # this is from node
			last_point = geom[-1]  # this is to node
			new = [i[0], i[1], first_point, last_point, length]
			links.append(new)
			access = i[3]
			gids.append(i[0])
		#print row['id'], row['segment_id'], links
		l1, l2, ls, count, len_s = [], [], [], 0, 0
		for e in links:
			if e[1] == 'end_bridge' and count == 0:
				n = [e[0], e[1], e[2], e[3], 0, e[4]]
				l1.append(n)
				count = count + 1
			elif e[1] == 'end_bridge' and count == 1:
				n = [e[0], e[1], e[2], e[3], 0, e[4]]
				l2.append(n)
				count = count + 1
			else:
				ls.append(e)
				len_s += e[4]

		total_l1, total_l2 = [], []
		if len(l1) > 0:
			l1 = get_sequence(l1, ls)
			for s in l1:
				total_l1.append(s[1])
			total_l1 = sum(total_l1)
		if len(l2) > 0:
			l2 = get_sequence(l2, ls)
			for t in l2:
				total_l2.append(t[1])
			total_l2 = sum(total_l2)
			lol = [l1, l2]
			total_length = [total_l1, total_l2]
		else:
			lol = [l1]
			total_length = [total_l1]

		if access not in ('pov', 'cargo', 'sentri'):
			access = 'pov'
		else:
			pass

		#print row['id'], row['segment_id'], l1, l2
		links_dict[row['id']] = lol, total_length
		lol, total_length, gids = str(map(str, lol)), str(map(str, total_length)), str(map(str, gids))
		lol = lol.replace('[', '{').replace(']', '}')
		total_length = total_length.replace('[', '{').replace(']', '}')
		gids = gids.replace('[', '{').replace(']', '}')
		list_db = [row['id'], lol, total_length, gids, access]
		for_db.append(list_db)


	#print links_dict
	write_to_file(links_dict, filepath=PORT_LINKS_FILENAME)
	write_to_csv(for_db)



if __name__ == '__main__':
	# CURRENT_DIR = os.path.dirname(__file__)
	# RESOURCES_DIR = os.path.abspath(__file__ + "/../../resources")
	# PORT_LINKS_FILENAME = os.path.join(RESOURCES_DIR, 'ports_links.json')
	# PORT_LINKS_CSV = os.path.join(RESOURCES_DIR, 'ports_links.csv')
	# To RUN please enter city
	if len(sys.argv) < 3:  # for testing locally
		city = sys.argv[1]  # elpaso, tucson, austin
		folder = os.getcwd() + '/'
	else:
		folder, city = read_sys_args(sys.argv)  # this line is to incorporate jenkins
	#CURRENT_DIR = os.path.dirname(__file__)

	if city == 'elpaso_juarez' or city == 'elpaso':
		PORT_LINKS_CSV = open(folder + 'ports_links.csv', 'wb')
		PORT_LINKS_FILENAME = os.path.join(folder, 'ports_links.json')
		# the following dict matches the ref bridge ids with the corresponding segment ids. This is important to get the correct links fir each bridge
		# {bridge_id : [segment_id, direction of end bridge}  ST_ymin = SOUTH, ST_ymax = NORTH, ST_xmin = WEST , ST_xmax = EAST
		ref_segment_dict = {32:["(610, 613, 614)", "('pov', 'sb_bota_1')"], 1:['(594)', "('pov')"], 7:["(622)", "('pov')"], 42:["(645)","('pov')"], 22:["(665)", "('pov')"], 53:["(673)", "('pov')"], 46:["(764)", "('pov')"], 15:["(737)", "('pov')"], 58:["(712)", "('pov')"], 27:["(690)", "('pov')"], 12:["(633)", "('sentri')"], 17:["(744)", "('sentri')"], 3:["(583)", "('cargo')"], 34:["(600)", "('cargo', 'sb_bota_2')"], 55:["(669)", "('cargo')"], 24:["(656)", "('cargo')"], 49:["(752)", "('cargo')"], 18:["(724)", "('cargo')"]}
		#ref_segment_dict = {1:[594, 'pov']}#, 1:[594, 'pov'], 7:[622, 'pov'], 42:[645,'pov'], 22:[665, 'pov'], 53:[673, 'pov'], 46:[764, 'pov'], 15:[737, 'pov'], 58:[712, 'pov'], 27:[690, 'pov'], 12:[633, 'sentri'], 17:[744, 'sentri'], 3:[583, 'cargo'], 34:[600, 'cargo'], 55:[669, 'cargo'], 24:[656, 'cargo'], 49:[752, 'cargo'], 18:[724, 'cargo']}
		ref_table = read_csv(os.path.join(folder, 'ref_table.csv'))
		ref_table = ref_table[ref_table['id'].isin(ref_segment_dict.keys())].reset_index()
		ref_table = ref_table.filter(['id', 'poe_name', 'direction', 'mode', 'svc_type'])
		ref_table['l_seg_dict'] = ref_table['id'].map(ref_segment_dict)
		ref_table[['segment_id','access']] = pd.DataFrame([x for x in ref_table.l_seg_dict])
		ref_table = ref_table.drop('l_seg_dict', axis=1)

		get_gids(ref_table)
	else:
		print "city ", city, 'is not elpaso and juarez so this file is not needed'

	#print ref_table.loc[ref_table['id'] == 1]
