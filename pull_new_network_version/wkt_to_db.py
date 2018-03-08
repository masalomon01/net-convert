import psycopg2
from datetime import datetime
import sys
import config


def read_sys_args(args):
    try:
        city = args[1]
        f = args[2]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be city name and Arg2 should be input wkt')
    return city, f


if __name__ == '__main__':
    if len(sys.argv) < 3:
        city = 'elpaso_juarez'
        in_file = 'D:/Will/temp/elpaso_juarez/links_wkt.csv'
    else:
        city, in_file = read_sys_args(sys.argv)

    schema_name = 'dev_wkts'
    conn = psycopg2.connect(user=config.NETWORKLAND_USER, password=config.NETWORKLAND_PASSWORD, host=config.NETWORKLAND_URL, database=config.NETWORKLAND_DB)  # port default 5432
    cur = conn.cursor()
    current_time = str(datetime.now().replace(microsecond=0)).replace(' ', '_').replace('-', '').replace(':', '')
    table_name = "{}_wkt_{}".format(city, current_time)
    # todo: it would be good to not hardcode the queries.
    query = "CREATE TABLE {}.{} (LinkID_parade text PRIMARY KEY,reverseID_parade text,LinkID_ptv text,reverseID_ptv text,WKT text,fromNodeID_parade text,toNodeID_parade text,fromNodeID_ptv text,toNodeID_ptv text,length text,speed text,ltype text,FFTT text,primaryName text,secondaryName text,TMC text,numLanes text,firstOrientation text,lastOrientation text,successors text,successorAngles text,predecessors text,predecessorAngles text,restrictedSuccessors text,restrictedSuccessorAngles text,restrictedPredecessors text,restrictedPredecessorAngles text,restrictedAreaID text,direction text,category text,category_ptv text,style text,type text,new_ltype text, traffic_signal text, gidSuccessors text, gidPredecessors text, osmid text, elevation text)".format(schema_name, table_name).lower()
    print query
    cur.execute(query)
    conn.commit()
    print "table created"

    input_file = open(in_file, 'rb')
    copy_sql = """
               COPY {}.{} FROM stdin WITH CSV HEADER
               DELIMITER as ','
               """.format(schema_name, table_name)

    cur.copy_expert(sql=copy_sql, file=input_file)

    query = "SELECT AddGeometryColumn('{}', '{}', 'geom', 4269, 'LINESTRING', 2);".format(schema_name, table_name)
    cur.execute(query)
    query = "UPDATE {}.{} SET geom = ST_GeomFromText(wkt, 4269)".format(schema_name, table_name)
    cur.execute(query)

    conn.commit()

