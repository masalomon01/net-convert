'''
Created on Nov 11, 2015

@author: asifrehan
'''
import os
import pandas as pd
from shortlink_identification import parentOffspringTurnBin, majorLinkChecker,\
    findSiblingOrSpouseLinks, findRightSpouseOrSibling
from intersectionTurnType import intersectionTurnType

def bidirecVsDividedMajLeftTurnTypeX(linkID, links_df, nodes_df):
    '''
    Typical example: linkID_parade 6046 and 24204
    One major road is represented by overlapping lines and the other major 
    road is represented by separate non-overlapping lines and has left turn
    lanes on opposite directions.     
    '''
    length = links_df.at[linkID, 'length(feet)'] <= 60
    ltype = links_df.at[linkID, 'ltype']
    major = majorLinkChecker(linkID, links_df)

    parentOrien = parentOffspringTurnBin(linkID, "predecessor", links_df)
    
    #check major thru parent with same ltype as current link
    if len(parentOrien[1])==1: thruPar = int(parentOrien[1][0]) 
    thruMajPar = links_df.at[thruPar, 'ltype']==ltype

    #check major left parent and get ltype for comparing with right sibling    
    if len(parentOrien[2])==1: leftPar = int(parentOrien[2][0])
    leftMajPar = majorLinkChecker(leftPar, links_df)
    if leftMajPar:
        leftParLtype = links_df.at[leftPar, 'ltype']
         
    #check if one right sibling exists and the ltype of sibling matches with
    #left parent's to check major right sibling. Right sibling is also almost 
    #on the same direction of the left parent
    sib = findSiblingOrSpouseLinks(linkID, links_df, nodes_df, 'sibling')
    rightSibling = findRightSpouseOrSibling(links_df, parentOrien, 
                                sib, SiblingOrSpouse='sibling')
    rightMajSib = links_df.at[rightSibling, 'ltype'].values[0]==leftParLtype
    
    #Check if major through offspring exists
    offsp = parentOffspringTurnBin(linkID, "successor", links_df)    
    if len(offsp[1])==1: thruOffsp = int(offsp[1][0])
    thruMajOffsp = links_df.at[thruOffsp, 'ltype']==ltype
    
    #check opposite links meeting up from left and right at the end node
    spouse = findSiblingOrSpouseLinks(linkID, links_df, nodes_df, 'spouse')
    if len(spouse)>=3:
        angleOrien = links_df.at[linkID, 'lastOrientation(deg)']
        turns = [[], [], [], []]
        for sp in spouse:
            spAngleOrien = links_df.at[sp, 'firstOrientation(deg)']
            turn = intersectionTurnType(angleOrien, (spAngleOrien+180)%360)
            turns[turn-1].append(sp)
        leftTurnBaysMeet = len(turns[0])==1 and len(turns[1])==1 
        rightSpLtype = links_df.at[turns[0], 'ltype'].values[0]
        leftSpLtype = links_df.at[turns[1], 'ltype'].values[0]
        leftTurnBaysLtype = rightSpLtype==leftSpLtype==leftParLtype
        leftTurnBays = leftTurnBaysLtype and leftTurnBaysMeet
    
    return (length and major and thruMajPar and rightMajSib and thruMajOffsp 
            and leftTurnBays)

def bidirecVsDividedMajLeftTurn(linkID, links_df, nodes_df):
    '''
    Finds if the link is "TypeX" if not checks if its reverse link is.
    e.g. TypeX = 6046 and its TypeY= 16291
    TypeX and TypeY names are used just to differentiate
    '''
    try:
        return bidirecVsDividedMajLeftTurnTypeX(linkID, links_df, nodes_df)
    except:
        try:
            revID = links_df.at[linkID, 'reverseID_parade']
            return bidirecVsDividedMajLeftTurnTypeX(revID, links_df, nodes_df)
        except:
            return False
    
if __name__ == '__main__':
    city = 'Austin'
    fldr = os.path.join("/media/asifrehan/shared_data_folder",
                            "Metropia_docs/{}_WKT".format(city))
    links_df = pd.read_csv(fldr+"/links_wkt.csv")
    nodes_df = pd.read_csv(fldr+"/nodes_wkt.csv")
    print bidirecVsDividedMajLeftTurn(6046, links_df, nodes_df)
    print bidirecVsDividedMajLeftTurn(24204, links_df, nodes_df)
    print bidirecVsDividedMajLeftTurn(16291, links_df, nodes_df)
    for i in range(len(links_df)):
        if bidirecVsDividedMajLeftTurn(i, links_df, nodes_df):
            print i