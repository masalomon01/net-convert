import time
import arcpy

arcpy.env.workspace= "D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/data.gdb"
fc= "PTV_split_points2"
fc2= "PTV_split2"

ID= "LinkID_par"
Dist= "N_dist"
DistDict= {}

cursor= arcpy.da.SearchCursor(fc,[ID,Dist])

for row in cursor:
    key= row[0]
    dist= row[1]
    DistDict.setdefault(key,[]).append(dist)

del row
del cursor

out=open('D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/Buffdist.txt','w')

for key in DistDict:
    out.write(str(key))
    out.write('\t')
    out.write(str(DistDict[key]))
    out.write('\n')

out.close()
print "distance extraction complete!"
print time.ctime()

starttime=time.clock()



cursor= arcpy.da.UpdateCursor(fc2,[ID,Dist])

for row in cursor:
    if row[0] in DistDict:
        row[1]=max(DistDict[row[0]])
        #print "added"
        cursor.updateRow(row)

endtime= time.clock()

print time.ctime()
print "update finished in %d seconds" % (endtime-starttime)

del row
del cursor



