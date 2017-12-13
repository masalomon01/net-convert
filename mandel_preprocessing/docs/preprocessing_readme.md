## How to Run Mandel Preprocessing

1.  Ensure that preprocessing.py, mutual_turns.py, read_data.py, and geometry_calculations.py are stored in the same folder
2.  Execute main function of preprocessing.py with two arguments - path to folder, and city name
3.  The folder path should contain other a subfolder with the same name as the city, which should in turn contain the links_wkt.csv file
4.  City name must be exactly as it is named in network database    

######Valid Options:
* austin
* tucson
* elpaso_juarez
* newyork
* houston
* arizona    
    
######Example execution on Windows:
1. cd to folder where code is stored
2. python preprocessing.py D:/Will/Metropia/Network Updates/Austin/Update 12-19-2016/ austin


