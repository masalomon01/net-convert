import arcpy

#return true if the two bearings are quite different
#could eventually skip the step of converting bearing (degrees) to its letter representation
#could then directly calculate the degree difference in bearings
#then determine threshhold for what is acceptable (i.e. bearing difference must be less than 90 or something)
#this would be more accurate

def isFlag(dir1,dir2):
	if ((dir1 == 'N') and (dir2 == 'S' or dir2 == 'SE' or dir2 == 'SW')):
		return True
	elif ((dir1 == 'NW') and (dir2 == 'S' or dir2 == 'SE' or dir2 == 'E')):
		return True
	elif ((dir1 == 'NE') and (dir2 == 'S' or dir2 == 'SW' or dir2 == 'W')):
		return True
	elif ((dir1 == 'W') and (dir2 == 'NE' or dir2 == 'SE' or dir2 == 'E')):
		return True
	elif ((dir1 == 'SW') and (dir2 == 'N' or dir2 == 'NE' or dir2 == 'E')):
		return True
	elif ((dir1 == 'S') and (dir2 == 'N' or dir2 == 'NE' or dir2 == 'NW')):
		return True
	elif ((dir1 == 'SE') and (dir2 == 'NW' or dir2 == 'N' or dir2 == 'W')):
		return True
	elif ((dir1 == 'E') and (dir2 == 'W' or dir2 == 'SW' or dir2 == 'NW')):
		return True
	else:
		return False



arcpy.env.workspace = "D:/Will/GIS Data/network_matching/OSM and PTV/Tucson/3-7-2016/data.gdb"
fc = "Identity"

arcpy.AddField_management(fc,"B_flag","SHORT")
cursor = arcpy.da.UpdateCursor(fc, ['OSM_direct','PTV_direct','B_flag'])

for row in cursor:

	if isFlag(row[0],row[1]):
		row[2] = 1
	else:
		row[2] = 0
	cursor.updateRow(row)

