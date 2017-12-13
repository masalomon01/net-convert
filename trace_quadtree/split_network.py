'''
Created on Aug 2, 2017

@author: Asif Rehan

NOTE: The Quadtree iterator functionality is availble for Pyqtree version >= 0.25.0
So current PIP installation provides v 0.24.0 which will not work. Update manually on Python's site-package.
'''
import os
import sys
import pandas
from pyqtree import Index
import s2sphere
import datetime
import time
import requests
from scipy.spatial import kdtree


PCT_LINKS_IN_CELL=0.05
MAX_CROWD = 5000
MAX_DEPTH= 5
DATA_AVAILABILITY_PERIOD = 7    #days
TRAFFIC_DB_URL = 'http://metropia-traffic-production.herokuapp.com/api/v2.0/'
SELECT_DATA = {'inrix': 1, 'ltta': 1}   #select only the ones with X days' data out of 7 days
# not sure if should select data based on data for all timeslots


def read_sys_args(args):
	try:
		f = args[1]  # filepath to files
		city = args[2]  # elpaso, tucson, austin
	except IndexError:
		raise IndexError('Incorrect inputs.  Arg1 should be a path to folder and arg2 should be city name')

	in_file = f + '/' + city + '/links_wkt.csv'
	out_file = f + '/mapping.csv'
	if city == 'elpaso_juarez':
		city = 'elpaso'
	else:
		pass

	return city, in_file, out_file



class SplitNetwork:

	def __init__(self,
				in_filepath,
				city='tucson'):
		'''
		steps
		====
		1. read network data
		2. for each ltype:for each link in network, grab a week's data
		2.1    select the links in the network
		2.2    if data exists: add it for quadtree
		2.3
		'''
		self.city = city
		self._in_filepath = in_filepath
		self.__GLOBAL_CELL_ID = 0
		self._full_ntwk = self.extract_ntwk_data()
		self._bbox = self.__get_network_bounding_box() #[lat_min, lat_max, lon_min, lon_max]
		self._links_with_data = self.get_gids_with_data(self.city)
		self.link_cellid_map = self.__cell_id_map()

	def extract_ntwk_data(self):
		full_ntwk = pandas.read_csv(self._in_filepath)
		full_ntwk['centroid'] = full_ntwk.apply(lambda x: self.__get_link_centroid(x), axis=1)
		full_ntwk = full_ntwk[['centroid', 'ltype', 'LinkID_ptv']] #select columns
		return full_ntwk


	def get_gids_with_data(self, city):
		'''
		check the ltta and inrix data and of a link has more than a fixed number of days' LTTA or INRIX data
		add it to a list.

		return
		------
		a list of integers: the list provides GID's
		'''
		now = datetime.datetime.utcnow()

		gids_w_data= {}
		sources = ['inrix', 'ltta']
		#INRIX and LTTA data check
		for source in sources:
			for i in range(DATA_AVAILABILITY_PERIOD):
				datestamp = (now - datetime.timedelta(days=i)).strftime('%Y%m%d')
				r = requests.get(TRAFFIC_DB_URL + source+'/' + datestamp + '?city=' + self.city)
				for i in r.json().keys():
					gid = gids_w_data.setdefault(int(i), {})
					gid.setdefault(source, 0)
					gid[source] += 1

		#select gid's which have data in more days than the threshold set up earlier
		list_gid_w_data = []
		for gid in gids_w_data:
			for i in source:
				gid_data = gids_w_data.get(gid)
				if gid_data.get(source) is not None:
					if gid_data[source] >= SELECT_DATA[source]:
						if gid not in list_gid_w_data:
							list_gid_w_data.append(gid)


		return list_gid_w_data

	def __get_link_centroid(self, row):
		wkt = row['WKT']
		points = wkt[wkt.find('(')+1 : -1].split(',')
		points = [point.strip().split(' ') for point in points]
		point_lon_lat = [[float(i[0]), float(i[1])] for i in points]
		avg_lon = sum([i[0] for i in point_lon_lat]) / len(point_lon_lat)
		avg_lat = sum([i[1] for i in point_lon_lat]) / len(point_lon_lat)
		return avg_lon, avg_lat

	def __get_network_bounding_box(self):
		# xmin, ymin, xmax, ymax
		lons = [i[0] for i in self._full_ntwk['centroid']]
		lats = [i[1] for i in self._full_ntwk['centroid']]
		return (min(lons), min(lats), max(lons), max(lats))

	def __quick_search_kdtree(self, ntwk):
		lons = [i[0] for i in ntwk['centroid']]
		lats = [i[1] for i in ntwk['centroid']]
		search_kdtree = kdtree.KDTree(zip(lons, lats))

		return search_kdtree

	def __cell_id_map(self):
		'''
		build quatree map bases on the links with data
		'''
		link_cellid_map = [] #only for the links with data
		for ltype in self._full_ntwk['ltype'].unique():
			print '\n=========\nltype' + str(ltype) + '\n========='
			ntwk = self._full_ntwk[(self._full_ntwk['ltype'] == ltype)]
			print 'ltype', ltype, '# of links w/ ltype ', ltype, '=', ntwk.shape[0]
			link_cellid_map += self.__apply_quadtree_pyqtree(ntwk, ltype)

		return link_cellid_map

	def __apply_quadtree_pyqtree(self, ntwk, ltype):
		ntwk_w_data_ltype = ntwk[ntwk['LinkID_ptv'].isin(self._links_with_data)]
		print 'ltype', ltype, '# of links w/ data =', ntwk_w_data_ltype.shape[0]
		spindex = Index(bbox=self._bbox, max_items=int(min(ntwk_w_data_ltype.shape[0]*PCT_LINKS_IN_CELL, MAX_CROWD)),
						max_depth=MAX_DEPTH)
		for i in xrange(ntwk_w_data_ltype.shape[0]):
			#print ltype, i, '/ ', ntwk_w_data_ltype.shape[0], '(', float(i)/ntwk_w_data_ltype.shape[0]*100, '%)'
			link = ntwk_w_data_ltype.iloc[i]
			spindex.insert(link['LinkID_ptv'], bbox=(link['centroid'] * 2))

		link_cellid_map = self.__get_link_cube_tuple(spindex, ltype)
		assert len(link_cellid_map) == ntwk_w_data_ltype.shape[0]
		#now assign cell id;s to the links without data by looking at their nearest neighboring link's cell_id
		link_cellid_map = self.__find_cellid_neighbors(spindex, ntwk, link_cellid_map, ltype)
		return link_cellid_map

	def __find_cellid_neighbors(self, spindex, ntwk, link_cellid_map, ltype):
		'''
		1. get a set of links w/ data
		2. get the remaining set of links w/o data
		3. build a kd tree for the set of links w/ data
		4. for each link in w/o data
		4.1     get the centroid
		4.2     find nearest neighbor's centroid from kd tree
		4.3     find the gid of the nearest neighbor's centroid in the set of links w/ data
		4.4     find the cell id for the nearest neighbor's gid
		4.5     assign the same cell id
		'''
		#get neighbor_links that do not have data
		ntwk_without_data_ltype = ntwk[ ~ntwk['LinkID_ptv'].isin(self._links_with_data)]
		ntwk_w_data_ltype = ntwk[ntwk['LinkID_ptv'].isin(self._links_with_data)]

		print 'ltype',  ltype, '# of neighbor_links w/o data', ntwk_without_data_ltype.shape[0]

		#count_links_wo_neighbors = 0
		gids_cellid_map = [i[0] for i in link_cellid_map]
		ltype_kdtree = self.__quick_search_kdtree(ntwk_w_data_ltype)

		for i in xrange(ntwk_without_data_ltype.shape[0]):
			link = ntwk_without_data_ltype.iloc[i]
			nearest_link_index = ltype_kdtree.query(list(link['centroid']), k=1)[1]
			nearest_link_centroid = ltype_kdtree.data[nearest_link_index]
			nearest_gid = ntwk_w_data_ltype[ntwk_w_data_ltype['centroid'] == tuple(nearest_link_centroid)]['LinkID_ptv'].values[0]
			index_pick_link = gids_cellid_map.index(nearest_gid)
			neighbor_cellid = link_cellid_map[index_pick_link][1]
			link_cellid_map.append([link['LinkID_ptv'], neighbor_cellid, ltype])
		#print 'ltype',  ltype, '# of neighbor_links w/o data and no neighbor', count_links_wo_neighbors
		return link_cellid_map

	def __get_link_cube_tuple(self, spindex, ltype):

		mapping = []

		#collect nodes if tree root has any
		if len(spindex.nodes) > 0 :
			for node in spindex.nodes:
				mapping.append([node.item, self.__GLOBAL_CELL_ID, ltype])
			self.__GLOBAL_CELL_ID +=  1

		#now loop through all children and if it has nodes, collect them too!
		for child in spindex:
			if len(child.nodes) >= 0:
				for node in child.nodes:
					mapping.append([node.item, self.__GLOBAL_CELL_ID, ltype])
				self.__GLOBAL_CELL_ID +=  1
		return mapping

	def __apply_quadtree_s2(self):
		'''
		unused, implemented
		'''

		cell_ids = []
		for i in xrange(self._links_with_data.shape[0]):
			lon, lat = self._links_with_data.iloc[i]['centroid']
			latlng = s2sphere.LatLng.from_degrees(lat, lon)
			cell = s2sphere.CellId.from_lat_lng(latlng)
			cell_id = cell.id()
			cell_ids.append(cell_id)
		#assert _links_with_data.shape[0] == len(set(cell_ids))
		return cell_ids

	def write_mapping(self, out_filepath='./mapping.csv'):
		pandas.DataFrame(self.link_cellid_map, columns=['gid', 'cell_id', 'ltype']).to_csv(
																						out_filepath, index=False)

if __name__ == '__main__':
	start_time = datetime.datetime.now()
	# To RUN please enter city
	if len(sys.argv) < 3:  # for testing locally
		city = sys.argv[1]  # elpaso, tucson, austin
		in_file = os.getcwd()
		in_file = in_file + '/links_wkt.csv'
		out_file = './mapping.csv'
	else:
		city, in_file, out_file = read_sys_args(sys.argv)  # this line is to incorporate jenkins

	if city == 'taiwan':
		print 'we are skipping taiwan for now because there is no trace data'
	else:
		splitted = SplitNetwork(city=city, in_filepath=in_file)
		splitted.write_mapping(out_filepath=out_file)
	print 'total script time took', datetime.datetime.now() - start_time
