import arcpy

arcpy.env.workspace= "D:\Will\Google Drive\Metropia\Map matching\OSM and PTV\Tucson1"

osm = "OSM_tucson.shp"
ptv = "PTV_tucson.shp"

osmLength = "length"
ptvLength = "length(fee"

cursor = arcpy.da.SearchCursor(osm,[osmLength])

osmTotalLength = 0

for row in cursor:
	lengthInt = float(row[0])
	osmTotalLength += lengthInt

print osmTotalLength

cursor = arcpy.da.SearchCursor(ptv,[ptvLength])

ptvTotalLength = 0
for row in cursor:
	lengthInt = float(row[0])
	ptvTotalLength += lengthInt

print ptvTotalLength

print (osmTotalLength - ptvTotalLength)