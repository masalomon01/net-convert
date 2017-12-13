'''
Created on Oct 2, 2015

@author: asifrehan
'''
import os
from shortlink_identification import findThruSiblingOrSpouse,majorLinkChecker
from math import sin, radians

def rightTurnBayEndCond(linkID, links_df):
    try:
        offspsrings = links_df.at[linkID, 'successors'].split()
        #should hv one offsp
    except (ValueError, AttributeError):
        offsp = None
        endNodeOK = False
        endNodeLtypeChk = False
        return offsp, endNodeOK, endNodeLtypeChk
    if len(offspsrings)==1:
        offsp = int(offspsrings[0])
        thruSpouse = findThruSiblingOrSpouse(linkID, links_df, offsp, 
                                             siblingOrSpouse='spouse')
    else:
        offsp = None
        endNodeOK = False
        endNodeLtypeChk = False
        return offsp, endNodeOK, endNodeLtypeChk
    if thruSpouse != None: #thru from parent
        thruSpouseChck = True
        lastSpOrien = links_df.at[linkID, 'lastOrientation(deg)']
        offspOrien = links_df.at[offsp, 'firstOrientation(deg)']
        if 0 < sin(radians(offspOrien - lastSpOrien)) < sin(radians(90)):
            rightMergeEnd = True
        else:
            rightMergeEnd = False
        endNodeLtypeChk = majorLinkChecker(offsp, links_df) and  \
                                    majorLinkChecker(thruSpouse, links_df)
    else:
        return offsp, False, False
    try:
        endNodeOK = rightMergeEnd and thruSpouseChck
    except UnboundLocalError:
        endNodeOK = False
    return offsp, endNodeOK, endNodeLtypeChk

def rightTurnBayStartCond(linkID, links_df):
    try:
        parents = links_df.at[linkID, 'predecessors'].split() 
        #shd hv one parent
    except (ValueError, AttributeError):
        parent = None
        startNodeOK = False
        startNodeLtypeChck = False
        return  parent, startNodeOK, startNodeLtypeChck
    if len(parents)==1:
        parent = int(parents[0])
        thruSibl = findThruSiblingOrSpouse(linkID, links_df, parent)
    else:
        parent = None
        startNodeOK = False
        startNodeLtypeChck = False
        return parent, startNodeOK, startNodeLtypeChck
    if thruSibl != None: #thru from parent
        thruSiblingChck = True
        parOrien = links_df.at[parent, 'lastOrientation(deg)']
        firsOrien = links_df.at[linkID, 'firstOrientation(deg)']
        if 0 < sin(radians(firsOrien - parOrien)) < sin(radians(90)):
            rightDepartureStrt = True
        else:
            rightDepartureStrt = False
        startNodeLtypeChck = majorLinkChecker(parent, links_df) and   \
                                        majorLinkChecker(thruSibl, links_df)
    else:
        return parent, False, False
    try:
        startNodeOK = rightDepartureStrt and thruSiblingChck
                                                        
    except UnboundLocalError:
        startNodeOK = False
    return parent, startNodeOK, startNodeLtypeChck

def chkRightTurnBayFwd(linkID, links_df, nodes_df):    
    ltypeChk = links_df.at[linkID, 'ltype'] != 3 #to exclude ramps
    startNodeOK, startNodeLtypeChck =  \
                        rightTurnBayStartCond(linkID, links_df)[1:3]
    if startNodeOK ==True:
        offsp,endNodeOK,endNodeLtypeChk = rightTurnBayEndCond(linkID, links_df)
        if offsp!=None or not(endNodeOK==endNodeLtypeChk==False): 
            if endNodeOK == True:
                return startNodeOK and endNodeOK and ltypeChk and  \
                                    (startNodeLtypeChck or endNodeLtypeChk)
            if endNodeOK == False:
                offsp, endNodeOK,endNodeLtypeChk =  \
                                        rightTurnBayEndCond(offsp, links_df)
                try:
                    return startNodeOK and endNodeOK and ltypeChk and  \
                                    (startNodeLtypeChck or endNodeLtypeChk)
                except UnboundLocalError:
                    return False
        else:
            return False
    else:
        return False
    
def chkRightTurnBayBckwd(linkID, links_df, nodes_df):    
    ltypeChk = links_df.at[linkID, 'ltype'] != 3 #to exclude ramps
    endNodeOK,endNodeLtypeChk = rightTurnBayEndCond(linkID,links_df)[1:3]
    if endNodeOK == True:
        par, startNodeOK, startNodeLtypeChck =   \
                                rightTurnBayStartCond(linkID, links_df)
        if  par!=None or not(startNodeOK==startNodeLtypeChck==False): 
            if startNodeOK == True:
                return startNodeOK and endNodeOK and ltypeChk
            if startNodeOK == False:
                par, startNodeOK, startNodeLtypeChck =  \
                                    rightTurnBayStartCond(par, links_df)
                try:
                    return startNodeOK and endNodeOK and ltypeChk and  \
                                    (startNodeLtypeChck or endNodeLtypeChk)
                except UnboundLocalError:
                    return False
        else: 
            return False
    else:
        return False
      
def checkRightTurnBayShortlink(linkID, links_df, nodes_df):
    dec = chkRightTurnBayFwd(linkID, links_df, nodes_df) or   \
            chkRightTurnBayBckwd(linkID, links_df, nodes_df)
    return dec

if __name__ == '__main__':
    import  pandas as pd
    city = 'Austin'
    fldr = os.path.join("/media/asifrehan/shared_data_folder",
                            "Metropia_docs/{}_WKT".format(city))    
    links_df = pd.read_csv(fldr+"/links_wkt.csv")
    nodes_df = pd.read_csv(fldr+"/nodes_wkt.csv")
    #==========================================================================
    #for i in [13351, 18723,13175, 13336, 5646, 5647, 8331, 15727,10661,60597]: 
    #    #13351,5647,10661 should fail, 5646, (13175, 13336),
    #    #60597(minor-major) pass
    #    #8331 --> no parent, offspring.Shd get caught
    #    print i, ' ', checkRightTurnBayShortlink(i, links_df, nodes_df)
    # print checkRightTurnBayShortlink(15728, links_df, nodes_df)
    # print chkRightTurnBayFwd(15728, links_df, nodes_df) 
    # print chkRightTurnBayBckwd(15728, links_df, nodes_df) 
    #==========================================================================
    #print chkRightTurnBayBckwd(8331, links_df, nodes_df)
    #print chkRightTurnBayBckwd(60597, links_df, nodes_df)
    
    #Austin
    for i in [35601, 12912]:
        print i, checkRightTurnBayShortlink(i, links_df, nodes_df)