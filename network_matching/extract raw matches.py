import arcpy

arcpy.env.workspace = "D:/Will/GIS Data/Network Matching/OSM and PTV/Tucson/test_minimumBuffer2/data.gdb"

fc = "Identity"
fc2 = "matched_raw2"

where = '(M_flag =4 AND O_flag= 0) OR (B_flag = 1 AND O_flag= 0) OR intersect=1 OR uncovered=1'

arcpy.Select_analysis(fc,fc2,where)