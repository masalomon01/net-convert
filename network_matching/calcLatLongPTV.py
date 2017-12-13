import arcpy
import math

def Bearing(slat,slong,elat,elong):
	startLat = math.radians(slat)
	startLong = math.radians(slong)
	endLat = math.radians(elat)
	endLong = math.radians(elong)

	dLong = endLong - startLong

	temp = math.tan(endLat/2.0+math.pi/4.0)/math.tan(startLat/2.0+math.pi/4.0)
	dPhi = math.log(temp)
	if abs(dLong) > math.pi:
		 if dLong > 0.0:
			 dLong = -(2.0 * math.pi - dLong)
		 else:
			 dLong = (2.0 * math.pi + dLong)

	bearing = (math.degrees(math.atan2(dLong, dPhi)) + 360.0) % 360.0

	return bearing

def CalDirect(bearing):
    if (bearing >= 0 and bearing <= 22.5)or(bearing > 337.5 and bearing <= 360):
        return "N"
    elif bearing > 22.5 and bearing <= 67.5:
        return "NE"
    elif bearing > 67.5 and bearing <= 112.5:
        return "E"
    elif bearing > 112.5 and bearing <= 157.5:
        return "SE"
    elif bearing > 157.5 and bearing <=202.5:
        return "S"
    elif bearing > 202.5 and bearing <=247.5:
        return "SW"
    elif bearing > 247.5 and bearing <=302.5:
        return "W"
    elif bearing > 302.5 and bearing <=337.5:
        return "NW"


arcpy.env.workspace = "D:/Will/GIS Data/network_matching/OSM and PTV/El Paso/11-14-2015/data.gdb"

#feature class must use decimal degrees as unit of measurement
fc = "PTV_split"

arcpy.AddField_management(fc,"PTV_bear", "SHORT")
arcpy.AddField_management(fc,"PTV_direct", "TEXT")

cursor = arcpy.da.UpdateCursor(fc,['SHAPE@','PTV_bear','PTV_direct'])

for row in cursor:
	#x is long
	#y is lat
	startx = row[0].firstPoint.X
	starty = row[0].firstPoint.Y

	endx = row[0].lastPoint.X
	endy = row[0].lastPoint.Y

	comma = ","

	bear = Bearing(starty,startx,endy,endx)
	row[1] = bear
	row[2] = CalDirect(bear)
	cursor.updateRow(row)