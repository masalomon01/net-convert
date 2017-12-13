import time
import arcpy
from fuzzywuzzy import fuzz

print time.ctime()

StartTime= time.clock()

arcpy.env.workspace = "D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/data.gdb"

fc= "Identity"

arcpy.AddField_management(fc, "M_score", "SHORT")
arcpy.AddField_management(fc, "M_flag", "SHORT")

linkID= "MetropiaID"
XD= "LinkID_par"
RnameHD= "street_nam"
RnameLD= "primaryNam"
RnameListLD= "secondaryN"
score= "M_score"
flag= "M_flag"


cursor= arcpy.da.UpdateCursor(fc,[XD, linkID, RnameHD, RnameLD, score, flag, RnameListLD])

for row in cursor:

 #if row[1]== 1015:
        #print row[2]
        #print row[3]
        #print row[6]

        # compare HD name with LD name
        s1=fuzz.partial_ratio(row[2],row[3])
        s2=fuzz.ratio(row[2],row[3])
        s3=fuzz.token_sort_ratio(row[2],row[3])
        s4=fuzz.token_set_ratio(row[2],row[3])
        #print " HD name with LD name: %d %d %d %d" % (s1,s2,s3,s4)


        # compare HD name with LD namelist
        s5=fuzz.partial_ratio(row[2],row[6])
        s6=fuzz.ratio(row[2],row[6])
        s7=fuzz.token_sort_ratio(row[2],row[6])
        s8=fuzz.token_set_ratio(row[2],row[6])
        #print "HD name with LD namelist: %d %d %d %d" % (s5,s6,s7,s8)


        # if there is an empty HD roadname or LD roadname:
        if s1==0 or s2==0 or s3==0 or s4==0:
            s = 0
        else:
            s =  max(s1,s2,s3,s4,s5,s6,s7,s8)

        row[4]=s

        if s==100:
            row[5]=1
        elif s>= 46 and s < 100:
            row[5]=2
        elif s>= 20 and s < 46:
            row[5]=3
        elif s>=1 and s< 20:
            row[5]=4
        else:
            row[5]=0

        cursor.updateRow(row)

        #if row[5]== 1 or row[5]==2:
        #    XDID= row[0]
         #   LinID= row[1]
          #  XDdict.setdefault(LinID,[]).append(XDID)

        #print s
        #print "------"


 #else:
    #pass

del row
del cursor

print time.ctime()
EndTime= time.clock()
print "Updating finished in %s seconds" % (EndTime - StartTime)


