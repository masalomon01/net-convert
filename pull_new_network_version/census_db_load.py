import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import sys
import cStringIO
import config


con1 = psycopg2.connect(database=config.NETWORKLAND_DB, user=config.NETWORKLAND_USER, password=config.NETWORKLAND_PASSWORD, host=config.NETWORKLAND_URL)
cur1 = con1.cursor()

# sandbox and dev connections
con2 = psycopg2.connect(database=config.NETWORKSERVICE_SB_DB, user=config.NETWORKSERVICE_SB_USER, password=config.NETWORKSERVICE_SB_PASSWORD, host=config.NETWORKSERVICE_SB_URL)
cur2 = con2.cursor()

# production connection
#con2 = psycopg2.connect(database="d7a1ehnrppums", user="u4vuqnmf29u9ls", password="pb637b42549b9d70e12fe3e6c8e092973abfa0afccf0b5c5691b4e9a5a72a8ab8", host="ec2-34-233-65-7.compute-1.amazonaws.com")
#cur2 = con2.cursor()

# first create the table on the DB
'''
FOR EL PASO AND JUAREZ ONLY
CREATE TABLE sandbox.elpaso_censustracts
(
  id bigint NOT NULL PRIMARY KEY,
  geom geometry(MultiPolygon,4269),
  cve_ent bigint,
  cve_mun bigint,
  cve_loc bigint,
  cve_ageb character varying(254),
  city character varying(254),
  statefp bigint,
  countyfp bigint,
  tractce bigint,
  geoid numeric,
  name numeric,
  namelsad character varying(254),
  mtfcc character varying(254),
  funcstat character varying(254),
  aland numeric,
  awater bigint,
  intptlat numeric,
  intptlon numeric,
  census_id character varying(254)
)
'''

'''
FOR ALL CITIES
CREATE TABLE developer.austin_censustracts
(
  id bigint NOT NULL,
  geom geometry(MultiPolygon,4269),
  statefp character varying(254),
  countyfp character varying(254),
  tractce character varying(254),
  affgeoid character varying(254),
  geoid character varying(254),
  name character varying(254),
  lsad character varying(254),
  aland character varying(254),
  awater character varying(254),
  city character varying(10),
  census_id character varying(10)
)

CREATE INDEX sidx_austin_censustracts_geom
  ON developer.austin_censustracts
  USING gist
  (geom);
'''

input = cStringIO.StringIO()
cur1.copy_expert('COPY (select * from public.austin_censustracts) TO STDOUT', input)
input.seek(0)
cur2.copy_expert('COPY production.austin_censustracts FROM STDOUT', input)
con2.commit()
