__author__ = 'RanLi'

import arcpy

arcpy.env.workspace = "D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/data.gdb"

fc= "Identity"

arcpy.AddField_management(fc,"O_flag","SHORT")

linkID= "MetropiaID"
PTV= "LinkID_par"
score= "M_score"
flag= "M_flag"
one= "O_flag"
dict= {}

cursor= arcpy.da.SearchCursor(fc,[PTV, linkID])

for row in cursor:
    dict.setdefault(row[1],[]).append(row[0])

del row
del cursor

#print dict

cursor= arcpy.da.UpdateCursor(fc,[PTV, linkID, one])

for row in cursor:
    if len(set(dict[row[1]]))== 1:

        row[2]= 1
        #print "one to one found"

    else:

        row[2]= 0
        #print "one to one not found"

    cursor.updateRow(row)


 #print "updatefinsihed"



del row
del cursor
