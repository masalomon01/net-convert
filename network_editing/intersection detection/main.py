'''
Created on Sep 24, 2015

@author: asifrehan
'''
#!/usr/bin/python
import pandas as pd
import numpy as np
import os
import getopt
import json
import sys

from detect.conflicting_links import findConflictingLinks
from detect.shortlink_identification import checkShortLink
from detect.complex_intersection_uTurn_bay import checkUTurnBayLeftTurnLane,\
    checkComplexIntrsectionShrtlnk
from detect.right_turn_bay import checkRightTurnBayShortlink
from detect.bidirecVsDividedMajLeftTurn import bidirecVsDividedMajLeftTurn


CURRENT_DIR = os.path.dirname(__file__)

def main_intersection_shortlink_filter(newLinkWktFile, columnName, appendToFile,
         links_df, nodes_df, begin_link=0, end_link=None):
    '''
    This function goes through each of the links in the network and checks 5 filters to detect if the link is in
    an intersection or is on a maneuver.

    checks these 5 filters:

        1.   detects link inside a major-major intersection using checkShortLink()
        2.1. detects U-turn bays using checkUTurnBayLeftTurnLane()
        2.2. detects left turn lanes using checkUTurnBayLeftTurnLane()
        3.   detects right turn bays using checkRightTurnBayShortlink()
        4.   detects left turn lanes on divided major road meeting a road which has overlapping links in each direction
             using bidirecVsDividedMajLeftTurn()
        5.   detects intersection links in a major-major complex intersections using checkComplexIntrsectionShrtlnk()

    It appends 5 indicator columns for these cases to the links_wkt file and writes the file. Additionally, it also adds
    another column which is a boolean if nay of those 5 filters can capture the link.

    **inputs:**
    newWriteToFile: *str*
        filepath of the new appended wkt file
    columnName: *str*
        name of the column which will check if any filter flagged the link
    appendToFile: *str*
        filepath of the original link_wkt file
    links_df: *pandas.DataFrame*
        Original link_wkt file converted to an DataFrame
    nodes_df: *pandas.DataFrame*
        Original node_wkt file converted to an DataFrame
    begin_link: *int*, default: 0
        switch to set which link to start from. Use it for debugging only. By default starts from row 0 to end of file

    ** returns**
    None

    ** outputs **
    a new link wkt file appended with new columns

    '''
    
    max_linkID = links_df.LinkID_parade.tail(1).values[0]
    
    if end_link is not None:
        end_link = min(end_link, max_linkID)
    elif end_link is None:
        end_link = max_linkID
    
    
        
        
    results = np.zeros((max_linkID+1, 7))
    for linkID in xrange(begin_link, end_link+1):
        uturnBayOrLeft = checkUTurnBayLeftTurnLane(linkID, links_df,
                                                        nodes_df)
        type1 = checkShortLink(linkID, links_df, nodes_df)
        type2 = uturnBayOrLeft[0]
        type3 = checkRightTurnBayShortlink(linkID, links_df, nodes_df)
        type4 = bidirecVsDividedMajLeftTurn(linkID, links_df, nodes_df)
        type5= checkComplexIntrsectionShrtlnk(linkID,links_df,nodes_df)
        leftTurnOnly = uturnBayOrLeft[1]

        shtlnkCk = type1 or type2 or type3 or type4 or type5
        
        results[linkID,:] = [shtlnkCk, type1, type2, type3, type4, type5, leftTurnOnly]
        pct_done = float(linkID - begin_link + 1)/(end_link - begin_link + 1)*100
        print "step#2"+ "\tbegin:" + str(begin_link) + "\tFinished:"+ str(linkID) + "\tend:" +  \
                        str(end_link) + "\tTotal Links:" + str(max_linkID+1) + "\t{}% done".format(pct_done)
    
    header =    columnName          +   ',' +  \
                'intersectionType1' +   ',' +  \
                'intersectionType2' +   ',' +  \
                'intersectionType3' +   ',' +  \
                'intersectionType4' +   ',' +  \
                'intersectionType5' +   ',' +  \
                'leftTurnOnlyLane'
    np.savetxt(newLinkWktFile, results, fmt='%i', delimiter=',', header=header, comments='') 
    
                


def main(begin_link=0, end_link=None):
    '''
    **inputs***
    city: *str*
        name of the city in lower case
    task: *str*
        name of the task the script should perform. Recommended value: 'complete'. Task can be either of
        'intersection': detects intersection links only and outputs a new wkt file by appending
    begin_link: *int*, optional, default: 0
        switch to set which link to start from. Use it for debugging only. By default starts from row 0 up to end
    '''
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ht:c:v:d:o:b:e:", ["help", "task=", "city=", "version=", "data-folder=",
                                                               "output-folder=", "begin=", "end="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    city = None
    task = 'complete'
    data_location = None
    out_location = None
    version=""
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt in ('--city', '-c'):
            city = str(arg)
        elif opt in ("--version", '-v'):
            version = arg
        elif opt in ('--task', '-t'):
            task = str(arg)
        elif opt in ('--data-folder', '-d'):
            data_location = arg
        elif opt in ('--output-folder', '-o'):
            out_location = arg
        elif opt in ("--begin", '-b'):
            begin_link = int(arg)
        elif opt in ("--end", '-e'):
            end_link = int(arg)
            if not begin_link < end_link:
                raise Exception("end_link should be greater than begin_link")
        else:
            usage()
    

    DATA_FOLDER = os.path.join(CURRENT_DIR, 'data', city, version)

    OUTPUT_FOLDER = os.path.join(DATA_FOLDER, 'mandel_prep_output')


    if data_location is not None:
        DATA_FOLDER = data_location

    if out_location is not None:
        OUTPUT_FOLDER = os.path.join(out_location, 'mandel_prep_output')

    OUTPUT_FOLDER_MANDEL = os.path.join(OUTPUT_FOLDER, 'mandel')
    OUTPUT_FOLDER_PARADE = os.path.join(OUTPUT_FOLDER, 'parade')

    if not os.path.isdir(OUTPUT_FOLDER_MANDEL):
        os.makedirs(OUTPUT_FOLDER_MANDEL)
    if not os.path.isdir(OUTPUT_FOLDER_PARADE):
        os.makedirs(OUTPUT_FOLDER_PARADE)

    global columnName

    columnName = "intersectionShortlinkCheck"

    appendToFile = os.path.join(DATA_FOLDER, "links_wkt.csv")
    links_df = pd.read_csv(os.path.join(DATA_FOLDER, "links_wkt.csv"))
    nodes_df = pd.read_csv(os.path.join(DATA_FOLDER, "nodes_wkt.csv"))

    newLinkWktFile = os.path.join(  OUTPUT_FOLDER, "check_intersection_link.txt")


    main_intersection_shortlink_filter(newLinkWktFile, columnName,
                        appendToFile, links_df, nodes_df, begin_link=begin_link, end_link=end_link)


def usage():
    print('usage: python main.py [--city <CITY_NAME> | -c <CITY_NAME>] \n'
          '                      [--version <NETWORK VERSION> | -V <NETWORK VERSION>] \n  '
          'optional: \n'
          '                      [--data-folder <DIRECTORY OF INPUT FILES> | [-d <DIRECTORY OF INPUT FILES>]  \n'
          '                      [--output-folder <OUTPUT DIRECTORY> | -d <OUTPUT DIRECTORY>]  \n'
          '                      [--begin <LINK ID TO START FROM> | -b <LINK ID TO START FROM>]  \n'
          '                      [--end <LINK ID TO STOP AT> | -e <LINK ID TO STOP AT>]  \n'
          '                      [--help | -h ] \n'
          'description: \n'
          ' --city <CITY_NAME> | -c <CITY_NAME>                                 : specifies city name \n'
          ' --version <NETWORK VERSION> | -V <NETWORK VERSION>                  : as in YYYYMMDD, e.g. 20161018 \n'
          ' --data-folder <DIRECTORY OF INPUT FILES> | -d <DIRECTORY OF INPUT FILES>\n'
          "                                                                     : folder with link & node wkt  \n"         
          "                                                                       e.g. '/main/.../foldername' \n"
          ' --output-folder <OUTPUT DIRECTORY> | -d <OUTPUT DIRECTORY>          : output folder \n'
          '                                                                       default: --data-folders \n'
          ' --begin <LINK ID TO START FROM> | -b <LINK ID TO START FROM>        : link ID from 0-N \n'
          ' --end <LINK ID TO STOP AT> | -e <LINK ID TO STOP AT>                : link ID from 0-N \n'
          ' --help | -h                                                         : print this help message and exit. \n'
          'details on options: \n'
          '    --city | -c    : city name in lower case'
          '    --task | -t    : task name can be any one of these \n'
          "                       'intersection', 'linkpair', 'fstar' for each step  \n"
          "                       'intersection+linkpair': for first two tasks together  \n"
          "                       'linkpair+fstar': for last two tasks together  \n"
          "                       'intersection+linkpair+fstar' or 'complete': for all three tasks in one shot  \n"
          "   --begin | -b    : should be less than [--end | -e ]  \n"
          "   --end   | -e    : should be greater than [--begin | -b ]\n")


if __name__ == '__main__':
    main()



    #==========================================================================
    # print findTargetLinkPairs(10038, links_df, shortlink_df)
    # print findTargetLinkPairs(128840, links_df, shortlink_df)
    # print findTargetLinkPairs(2764, links_df, shortlink_df)
    # print findTargetLinkPairs(23795, links_df, shortlink_df)
    # print intersectionTurnType(links_df.at[22827, 'lastOrientation(deg)'],
    #                      links_df.at[13173, 'firstOrientation(deg)'])
    # print intersectionTurnType(links_df.at[22827, 'lastOrientation(deg)'],
    #                      links_df.at[14411, 'firstOrientation(deg)'])
    # print intersectionTurnType(links_df.at[22827, 'lastOrientation(deg)'],
    #                      links_df.at[9796, 'firstOrientation(deg)'])
    # print intersectionTurnType(links_df.at[22827, 'lastOrientation(deg)'],
    #                      links_df.at[5939, 'firstOrientation(deg)'])
    #==========================================================================
    #==========================================================================
    # ##check for upstreamlinkID
    # print upstreamLink(14411, 5, links_df)
    # print upstreamLink(9796, 5, links_df)
    # print upstreamLink(19016, 5, links_df)
    #
    # print upstreamLink(13813, 5, links_df)
    # print upstreamLink(19016, 5, links_df)
    #
    # print upstreamLink(4337, 5, links_df)
    # print upstreamLink(20116, 5, links_df)
    # print upstreamLink(3521, 5, links_df)
    # print upstreamLink(5453, 5, links_df)
    #==========================================================================
