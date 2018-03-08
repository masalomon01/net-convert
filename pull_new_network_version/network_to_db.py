import psycopg2
from datetime import datetime
import sys
import os
import csv
import heroku3
import config


def read_sys_args(args):
	try:
		city = args[1]  # elpaso, tucson, austin
		f = args[2]  # filepath to files
		sys = args[3]  # sandbox, dev, pd
		version = args[4]
		description = args[5]  # some description of what's in the deployment updates


	except IndexError:
		raise IndexError('Incorrect inputs.  Arg1 should be city name and Arg2 should be input wkt')
	if sys == "developer":
		schema_name = 'developer'
		conn = psycopg2.connect(user=config.NETWORKSERVICE_DEV_USER,
		                        password=config.NETWORKSERVICE_DEV_PASSWORD,
		                        host=config.NETWORKSERVICE_DEV_URL,
		                        database=config.NETWORKSERVICE_DEV_DB)  # port default 5432
	elif sys == 'sandbox':
		schema_name = 'sandbox'
		conn = psycopg2.connect(user=config.NETWORKSERVICE_SB_USER,
		                        password=config.NETWORKSERVICE_SB_PASSWORD,
		                        host=config.NETWORKSERVICE_SB_URL,
		                        database=config.NETWORKSERVICE_SB_DB)  # port default 5432
	elif sys == 'production':
		schema_name = 'production'
		conn = psycopg2.connect(user=config.NETWORKSERVICE_PD_USER,
		                        password=config.NETWORKSERVICE_PD_PASSWORD,
		                        host=config.NETWORKSERVICE_PD_URL,
		                        database=config.NETWORKSERVICE_PD_DB)  # port default 5432
	else:
		print("error inorrect system", sys)
		schema_name = None

	return city, f, schema_name, version, description, conn


def retire_existing_table(cur, schema, table_name, conn):
	query = """SELECT table_name 
				FROM information_schema.tables 
				WHERE table_schema = '{}' and table_name = '{}'""".format(schema, table_name)
	cur.execute(query)
	tables = cur.fetchall()
	if len(tables) > 0:
		today = str(datetime.now().date()).replace('-', '')
		new_name = "{}_{}".format(table_name, today)
		rename = """CREATE TABLE {}.{} AS TABLE {}.{};""".format(schema, new_name, schema, table_name)
		cur.execute(rename)
		# since we copied an old table to a new name we delete the table with existing name
		# p.s. I tried simply renaming the table before but the run time took forever
		drop = """DROP TABLE {}.{};""".format(schema, table_name)
		cur.execute(drop)
		print('retired table ', table_name, 'to ', new_name)
		conn.commit()
	else:
		print('no tables to retire')


def drop_oldest_table(cur, schema, table_name, conn):
	query = """SELECT table_name 
			FROM information_schema.tables 
			WHERE table_schema = '{}' and table_name like '%{}%'""".format(schema, table_name)
	cur.execute(query)
	tables = cur.fetchall()
	dates = []
	if schema == 'developer':
		network_copies = 2
	elif schema == 'sandbox':
		network_copies = 1
	elif schema == 'production':
		network_copies = 3
	if len(tables) == network_copies:
		for i in tables:
			date = filter(str.isdigit, i[0])
			if date:
				date = int(date)
			dates.append(date)
		oldest = str(min(dates))
		if network_copies == 1:    # this condition is to drop the correct table if it's the only table
			drop_table = drop_table = schema + '.' + table_name
			drop = """DROP TABLE {}.{};""".format(schema, table_name)
		else:
			drop_table = schema + '.' + table_name + '_' + oldest
			drop = """DROP TABLE {}.{}_{};""".format(schema, table_name, oldest)
		cur.execute(drop)
		print('drop table', drop_table)
		conn.commit()
	else:
		print('no tables to drop')


def write_csv(lol, name, fieldnames):
	path = 'output/' + name
	with open(path, 'wb') as csv_file:
		writer = csv.writer(csv_file)
		writer.writerow(fieldnames)
		for row in lol:
			writer.writerow(row)


def load_featurePoints_table(cur, schema, city, current, conn):
	print('start LINKXY2 or featurepoints')
	table_name = "featurepoints_{}".format(city)
	# drop oldest table
	drop_oldest_table(cur, schema, table_name, conn)
	# retire existing table
	retire_existing_table(cur, schema, table_name, conn)
	#read and edit csv file
	fp_lol = []
	fieldnames = ['from_node_parade', 'to_node_parade', 'num_featurePoints', 'featurePoints']
	in_file = current + '/output_LINKXY2.csv'
	with open(in_file, 'r') as f:
		reader = csv.reader(f)
		for row in reader:
			if row[0].isdigit(): # linkxy is a weird file so I want to skip the top 2 rows because they are not necessary
				anode, bnode, num, latlons = row[0], row[1], row[2], row[3:]
				features = [anode, bnode, num, str(latlons)]
				fp_lol.append(features)
	# write new csv file
	csv_name = table_name + '.csv'
	write_csv(fp_lol, csv_name, fieldnames)
	# read new csv file
	in_file = current + '/' + csv_name
	input_file = open(in_file, 'r')
	# create table
	query = """CREATE TABLE {}.{} (from_node_parade integer NOT NULL, to_node_parade integer, num_featurePoints integer, 
						featurePoints text)""".format(schema, table_name).lower()
	cur.execute(query)
	# make query
	copy_sql = """
					   COPY {}.{} FROM stdin WITH CSV HEADER
					   DELIMITER as ','
					   """.format(schema, table_name)
	# load table
	cur.copy_expert(sql=copy_sql, file=input_file)
	conn.commit()
	print('featurePoints or LINKXY2 loaded and committed', table_name)


def load_angles_table(cur, schema, city, current, conn):
	print('start output_angle_2')
	table_name = "angles_{}".format(city)
	# drop oldest table
	drop_oldest_table(cur, schema, table_name, conn)
	# retire existing table
	retire_existing_table(cur, schema, table_name, conn)
	#read csv file
	in_file = current + '/output_angle2.csv'
	input_file = open(in_file, 'r')
	#create table
	query = """CREATE TABLE {}.{} (from_link_parade integer NOT NULL, to_link_parade integer, restrict integer, 
				angle real)""".format(schema, table_name).lower()
	cur.execute(query)
	#make query
	copy_sql = """
				   COPY {}.{} FROM stdin WITH CSV HEADER
				   DELIMITER as ','
				   """.format(schema, table_name)
	#load table
	cur.copy_expert(sql=copy_sql, file=input_file)
	conn.commit()
	print('output_Angle_2 loaded and committed', table_name)


def load_nodes_table(cur, schema, city, current, conn):
	print('start nodes_2')
	table_name = "nodes_{}".format(city)
	# drop oldest table
	drop_oldest_table(cur, schema, table_name, conn)
	# retire existing table
	retire_existing_table(cur, schema, table_name, conn)
	#read csv file
	in_file = current + '/output_Node2.csv'
	input_file = open(in_file, 'r')
	#create table
	query = """CREATE TABLE {}.{} (nodeID_parade integer NOT NULL PRIMARY KEY, YCOORD real, XCOORD real, 
				nodeID_gid integer, nodeID_trace integer)""".format(schema, table_name).lower()
	cur.execute(query)
	#make query
	copy_sql = """
				   COPY {}.{} FROM stdin WITH CSV HEADER
				   DELIMITER as ','
				   """.format(schema, table_name)
	#load table
	cur.copy_expert(sql=copy_sql, file=input_file)
	conn.commit()
	print('Nodes_2 loaded and committed', table_name)


def load_zones_table(cur, schema, city, current, conn):
	print('start zones')
	table_name = "zones_{}".format(city)
	# drop oldest table
	drop_oldest_table(cur, schema, table_name, conn)
	# retire existing table
	retire_existing_table(cur, schema, table_name, conn)
	#read csv file
	in_file = current + '/parade gid zone.csv'
	input_file = open(in_file, 'r')
	#create table
	query = "CREATE TABLE {}.{} (LinkID_parade integer NOT NULL PRIMARY KEY, gid integer, zone integer)".format(schema, table_name).lower()
	cur.execute(query)
	#make query
	copy_sql = """
				   COPY {}.{} FROM stdin WITH CSV HEADER
				   DELIMITER as ','
				   """.format(schema, table_name)
	#load table
	cur.copy_expert(sql=copy_sql, file=input_file)
	conn.commit()
	print('Zones loaded and committed', table_name)


def load_wkt_table(cur, schema, city, current, conn):
	print('start wkt')
	current_time = str(datetime.now().replace(microsecond=0)).replace(' ', '_').replace('-', '').replace(':', '')
	table_name = "wkt_{}".format(city)
	# drop oldest table
	drop_oldest_table(cur, schema, table_name, conn)
	# retire existing table
	retire_existing_table(cur, schema, table_name, conn)
	#create table
	# Todo: it would be good to not hardcode the queries.
	query = """CREATE TABLE {}.{} (LinkID_parade bigint NOT NULL PRIMARY KEY, reverseID_parade bigint,LinkID_ptv bigint,reverseID_ptv bigint,
					WKT text,fromNodeID_parade bigint,toNodeID_parade bigint,fromNodeID_ptv bigint,toNodeID_ptv bigint,length real,speed int,ltype int,
					FFTT real,primaryName text,secondaryName text,TMC text,numLanes int,firstOrientation real,lastOrientation real,successors text,
					successorAngles text,predecessors text,predecessorAngles text,restrictedSuccessors text,restrictedSuccessorAngles text,
					restrictedPredecessors text,restrictedPredecessorAngles text,restrictedAreaID int,direction int,category int,category_ptv int,
					style int,type int,new_ltype int,signal_type text,gidSuccessors text,gidPredecessors text,osmid bigint,
					elevation int, access text)""".format(schema, table_name).lower()
	cur.execute(query)
	#load data into table
	in_file = current + '/' + city + '/links_wkt.csv'
	input_file = open(in_file, 'r')
	copy_sql = """
				   COPY {}.{} FROM stdin WITH CSV HEADER
				   DELIMITER as ','
				   """.format(schema, table_name)

	cur.copy_expert(sql=copy_sql, file=input_file)
	#add geom to table
	query = "SELECT AddGeometryColumn ('{}', '{}', 'geom', 4269, 'LINESTRING', 2);".format(schema, table_name)
	cur.execute(query)
	query = "UPDATE {}.{} SET geom = ST_GeomFromText(wkt, 4269)".format(schema, table_name)
	cur.execute(query)
	conn.commit()
	print('WKT loaded and committed', table_name)


def load_quadTree_table(cur, schema, city, current, conn):
	print('start quadTree')
	table_name = "quadtree_{}".format(city)
	# drop oldest table
	drop_oldest_table(cur, schema, table_name, conn)
	# retire existing table
	retire_existing_table(cur, schema, table_name, conn)
	#read csv file
	in_file = current + '/mapping.csv'
	input_file = open(in_file, 'r')
	#create table
	query = "CREATE TABLE {}.{} (gid integer NOT NULL PRIMARY KEY, cell_id integer, ltype integer)".format(schema, table_name).lower()
	cur.execute(query)
	#make query
	copy_sql = """
				   COPY {}.{} FROM stdin WITH CSV HEADER
				   DELIMITER as ','
				   """.format(schema, table_name)
	#load table
	cur.copy_expert(sql=copy_sql, file=input_file)
	conn.commit()
	print('quadTree loaded and committed', table_name)


def load_POE_segments(cur, schema, city, current, conn):
	print('start POE segments')
	table_name = "poesegments_{}".format(city)
	drop_oldest_table(cur, schema, table_name, conn)  # drop oldest table
	retire_existing_table(cur, schema, table_name, conn)  # retire existing table
	in_file = current + '/poe_segment_table.csv'   #read csv file
	input_file = open(in_file, 'r')
	#create table
	query = "CREATE TABLE {}.{} (gid integer NOT NULL, traceid integer, segment_id integer, name text, " \
	        "port_of_entry text, direction text, wt_entity_id integer, wt_seg_id integer)".format(schema, table_name).lower()
	cur.execute(query)
	#make query
	copy_sql = """COPY {}.{} FROM stdin WITH CSV HEADER DELIMITER as ',' """.format(schema, table_name)
	cur.copy_expert(sql=copy_sql, file=input_file)  #load table
	conn.commit()
	print('POE segments loaded and committed', table_name)


def load_ports_links(cur, schema, city, current, conn):
	print('start ports links')
	table_name = "portslinks_{}".format(city)
	drop_oldest_table(cur, schema, table_name, conn)  # drop oldest table
	retire_existing_table(cur, schema, table_name, conn)  # retire existing table
	in_file = current + '/ports_links.csv'   #read csv file
	input_file = open(in_file, 'r')
	#create table
	query = "CREATE TABLE {}.{} (port_id integer NOT NULL, port_info text ARRAY, port_length text ARRAY, " \
	        "port_links text ARRAY, port_mode text)".format(schema, table_name).lower()
	cur.execute(query)
	#make query
	copy_sql = """COPY {}.{} FROM stdin WITH CSV DELIMITER as ',' """.format(schema, table_name)
	cur.copy_expert(sql=copy_sql, file=input_file)  #load table
	conn.commit()
	print('port links loaded and committed', table_name)


def write_deployment_info(cur, schema, city, version, description, conn):
	# first check if the table exists if it does not create the table
	table_name = "deployment_info"
	query = """SELECT table_name 
				FROM information_schema.tables 
				WHERE table_schema = '{}' and table_name like '%{}%'""".format(schema, table_name)
	cur.execute(query)
	tables = cur.fetchall()
	if len(tables) == 0:
		query = """CREATE TABLE {}.{} (id SERIAL PRIMARY KEY, environment text, city text, network_version text,
				deployment_date timestamp, description text)""".format(schema, table_name).lower()
		cur.execute(query)
	else:
		pass
	date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	# query = """INSERT INTO {}.{} (deployment_date) VALUES ({})""".format(schema, table_name, date)
	query = """INSERT INTO {}.{} (environment, city, network_version, deployment_date,  description)
			VALUES ('{}', '{}', '{}', '{}', '{}')""".format(schema, table_name, schema, city, version, date, description)
	cur.execute(query)
	conn.commit()
	print('deployment_info loaded')


if __name__ == '__main__':
	start_time = datetime.now()
	# To RUN please enter city system and description
	if len(sys.argv) < 5: # for testing locally
		description = sys.argv[3]  # elpaso_juarez, tucson, austin
		city = sys.argv[1]  # elpaso, tucson, austin
		sys = sys.argv[2]  # sandbox, developer, pd
		in_file = os.getcwd()
		schema_name = sys  # you might het an error if the schema does not exist on the db
		if sys == "developer":
			schema_name = 'developer'
			conn = psycopg2.connect(user=config.NETWORKSERVICE_DEV_USER,
									password=config.NETWORKSERVICE_DEV_PASSWORD,
									host=config.NETWORKSERVICE_DEV_URL,
									database=config.NETWORKSERVICE_DEV_DB)  # port default 5432
		elif sys == 'sandbox':
			schema_name = 'sandbox'
			conn = psycopg2.connect(user=config.NETWORKSERVICE_SB_USER,
									password=config.NETWORKSERVICE_SB_PASSWORD,
									host=config.NETWORKSERVICE_SB_URL,
									database=config.NETWORKSERVICE_SB_DB)  # port default 5432
		elif sys == 'production':
			schema_name = 'production'
			conn = psycopg2.connect(user=config.NETWORKSERVICE_PD_USER,
									password=config.NETWORKSERVICE_PD_PASSWORD,
									host=config.NETWORKSERVICE_PD_URL,
									database=config.NETWORKSERVICE_PD_DB)  # port default 5432
		else:
			print('please enter the correct second argument for production, developer or sandbox')
	else:
		city, in_file, schema_name, version, description, conn = read_sys_args(sys.argv)

	cur = conn.cursor()

	heroku_conn = heroku3.from_key('4e0df56f-251c-4752-8777-a4ef1e315f01')
	heroku_name = 'network-' + schema_name
	print heroku_name
	heroku_app = heroku_conn.apps()[heroku_name]
	heroku_app.restart()

	load_wkt_table(cur, schema_name, city, in_file, conn)
	load_zones_table(cur, schema_name, city, in_file, conn)
	load_nodes_table(cur, schema_name, city, in_file, conn)
	load_angles_table(cur, schema_name, city, in_file, conn)
	load_featurePoints_table(cur, schema_name, city, in_file, conn)
	load_quadTree_table(cur, schema_name, city, in_file, conn)
	if city == 'elpaso_juarez' or city == 'elpaso':
		load_POE_segments(cur, schema_name, city, in_file, conn)
		load_ports_links(cur, schema_name, city, in_file, conn)
	else:
		print('no poe segments for city: ', city)
		pass
	write_deployment_info(cur, schema_name, city, version, description, conn)
	cur.close()
	conn.close()

	print 'total script time took', datetime.now() - start_time

# things used to time script
'''
	start_time = datetime.now()
	print 'starting script', start_time
	print 'create table took', datetime.now() - start_time
	ctable_time = datetime.now()

	print 'loading table took', datetime.now() - ctable_time
	ltable_time = datetime.now()
	print 'adding geom to table took', datetime.now() - ltable_time
	print 'total script time took', datetime.now() - start_time
'''