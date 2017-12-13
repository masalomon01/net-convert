__author__ = 'Ran'

import arcpy
arcpy.env.workspace= "D:\Will\Google Drive\Metropia\Map matching\OSM and PTV\Tucson1\Tucson1.gdb"
fc= "matched_raw6"
linkID= "MetropiaID"
XD= "LinkID_par"
RnameHD= "primaryNam"
RnameHD2nd="secondaryN"
RnameLD= "RoadName"
RnameListLD= "RoadList"
score= "M_Score"
m_flag= "M_flag"
b_flag= "B_flag"
e_flag= "E_flag"
matched= "matched"
XDdict= {}


cursor= arcpy.da.SearchCursor(fc,[XD, linkID,])

for row in cursor:
            LinID= row[1]
            XDID= row[0]
            XDdict.setdefault(LinID,[]).append(XDID)

del row
del cursor


out=open('D:\Will\Google Drive\Metropia\Map matching\OSM and PTV\Tucson1\link2xd_raw.csv','w')


for key in XDdict:
    XDdict[key]=list(set(XDdict[key]))

out.write('MetropiaID')
out.write(',')
out.write('LinkID_par')
out.write('\n')
for key in XDdict:
    out.write(str(key))
    out.write(',')
    out.write(str(XDdict[key]))
    out.write('\n')

out.close()