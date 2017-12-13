__author__ = 'Ran'

import arcpy
from collections import Counter
import csv

source_ptvIDs = []
dest_ptvIDs = []
sign_ptvIDs = []

with open('D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/Signs_tucson.tsv') as infile:
    reader = csv.reader(infile, delimiter='\t')
    headers = next(reader)
    for row in reader:
        source_ptvIDs.append(int(row[0]))
        dest_ptvIDs.append(int(row[1]))
        sign_ptvIDs.append(int(row[0]))
        sign_ptvIDs.append(int(row[1]))


arcpy.env.workspace = "D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/data.gdb"
fc= "matched_raw"
linkID= "MetropiaID"
XD= "LinkID_par"
length= "Shape_Length"
ptv_id= "LinkID_ptv"
XDdict= {}
XDleng = {}
XDnotGood= {}
XDGood= {}
XDequal= {}

lengthcount = 0
notgoodcount = 0
samecount = 0


cursor= arcpy.da.SearchCursor(fc,[XD, linkID, length, ptv_id, "ltype", "ltype_1"])

parade_to_ptv = {} # parade id : ptv id
metropia_ltypes = {} # mid : ltype
parade_ltypes = {}  # parade id : ltype

for row in cursor:
   XDdict.setdefault(row[1],{}).setdefault(row[0],[]).append(row[2])
   ptv = int(row[3])
   if ptv < 0:
        ptv *= -1
   parade_to_ptv[row[0]] = ptv
   metropia_ltypes[row[1]] = row[4]
   parade_ltypes[row[0]] = row[5]

del row
del cursor

for key in XDdict:
    for key1 in XDdict[key]:
        #print str(key)+ ":"+ str(key1)+ ":" + str(sum(XDdict[key][key1]))
        XDleng.setdefault(key,{}).update({key1:sum(XDdict[key][key1])})

#print XDleng

for key in XDleng:
    
    list= sorted(XDleng[key].iteritems(),key= lambda d:d[1], reverse = True )
    if key == '205554':
        print list
    if len(list)> 1:
        sign_matches = [] # full of item[0] which is parade IDs
        for item in list:
            if metropia_ltypes[key] == '3':
                # basically saying not to add a ramp as a source link
                # this works for most cases but we wont get ramp fork signs
                # data entry for that?
                if parade_to_ptv[item[0]] in dest_ptvIDs:
                    sign_matches.append(item[0])
            elif parade_to_ptv[item[0]] in sign_ptvIDs:  
                sign_matches.append(item[0])
        #small threshhold so basically just take the link that matches along a greater length of the link
        t1= list[0][1]
        t2= list[1][1]
        if len(sign_matches) > 0:
            
            XDGood.update({key:sign_matches[0]})
        elif t1- t2 >= 1:
            XDGood.update({key:list[0][0]})
            lengthcount += 1

        elif t1- t2 == 0:
           xd1= list[0][0]
           xd2= list[1][0]
           XDequal.setdefault(key,[]).append(xd1)
           XDequal.setdefault(key,[]).append(xd2)
           samecount += 1

        else:
            xd1= list[0][0]
            xd2= list[1][0]
            notgoodcount += 1
            #xd3= list[2][0]
            XDnotGood.setdefault(key,[]).append(xd1)
            XDnotGood.setdefault(key,[]).append(xd2)
            #XDnotGood.setdefault(key,[]).append(xd3)


    else:
        XDGood.update({key:list[0][0]})
        
#print lengthcount
#print samecount
#print notgoodcount



out=open('D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/link2xd_goodones.csv','w')

out.write('MetropiaID')
out.write(',')
out.write('LinkID_par')
out.write('\n')
for key1 in XDGood:
    if(XDGood[key1] != ''):
        out.write(str(key1))
        out.write(',')
        out.write(str(XDGood[key1]))
        out.write('\n')
    


out.close()

out=open('D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/3-7-2016/link2xd_same.csv','w')

out.write('MetropiaID')
out.write(',')
out.write('LinkID_par')
out.write('\n')
for key1 in XDequal:
    out.write(str(key1))
    out.write(',')
    out.write(str(XDequal[key1]))
    out.write('\n')

out.close()

