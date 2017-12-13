'''
Created on Oct 2, 2015

@author: asifrehan
'''
from shortlink_identification import majorLinkChecker, checkShortLink
from intersectionTurnType import intersectionTurnType
from math import sin, radians


def findMajNodeParentSiblingSpouseOffsp(linkID, links_df, nodes_df):
    '''find major spouse, parent, sibling, offspring from the end and 
    start node of the current link
    '''
    fromNode = links_df.at[linkID, 'fromNodeID_parade']
    toNode = links_df.at[linkID, 'toNodeID_parade']
    try:
        offsp = nodes_df.at[toNode, 'successorLinks'].split()
        offspMaj = [int(i) for i in offsp 
                if majorLinkChecker(int(i), links_df) == True
                    and links_df.at[int(i), 'reverseID_parade'] == -1]
    except:
        offspMaj = []
    try:
        spouseEndNodeLinksAll = nodes_df.at[toNode, 'predecessorLinks'].split()
        spouseMaj = [int(i) for i in spouseEndNodeLinksAll 
                 if majorLinkChecker(int(i), links_df) == True 
                    and int(i) != linkID 
                    and links_df.at[int(i), 'reverseID_parade'] == -1]
    except:
        spouseMaj = []
    reverseLinkID = links_df.at[int(linkID), 'reverseID_parade']
    try:
        succLinks = links_df.at[linkID, 'successors'].split()
    except:
        succLinks = []

    leftTurnTo = [int(i) for i in succLinks if int(i) not in offspMaj and
                  int(i) != reverseLinkID and 
        intersectionTurnType(
                            links_df.at[linkID, 'lastOrientation(deg)'], 
                            links_df.at[int(i), 'lastOrientation(deg)'])!=1]
    try:
        parentStrtNodeLinksAll =nodes_df.at[fromNode, 'predecessorLinks'].split()
        parentMajMin = [int(i) for i in parentStrtNodeLinksAll 
                        if links_df.at[int(i), 'reverseID_parade'] == -1]
        parentMaj = [i for i in parentMajMin 
                     if majorLinkChecker(i, links_df) == True]
    except:
        parentMajMin = []
        parentMaj = []
    try:
        siblingEndNodeLinksAll = nodes_df.at[fromNode, 'successorLinks'].split()
        siblingMaj = [int(i) for i in siblingEndNodeLinksAll 
                  if majorLinkChecker(int(i), links_df) == True 
                    and int(i) != linkID
                    and links_df.at[int(i), 'reverseID_parade'] == -1]
    except:
        siblingMaj = []
    if len(siblingMaj)==0 and len(parentMajMin)==1:
        singleParent = parentMajMin
    else:
        singleParent =[]
    return spouseMaj, parentMaj, offspMaj, siblingMaj, leftTurnTo, singleParent


def checkNodeParentSiblingThu_NodeOffspSpouseThru(linkID, spouseMaj, 
                                                   parentMaj, offspMaj, 
                                                   siblingMaj, singleParent, 
                                                   links_df):
    spouseOrien = links_df.at[spouseMaj[0], 'lastOrientation(deg)']
    offspOrien = links_df.at[offspMaj[0], 'firstOrientation(deg)']
    endNodeLinearity = intersectionTurnType(spouseOrien, offspOrien) == 4
    avgOrienEndNode = (spouseOrien + offspOrien) / 2.0
    if len(parentMaj)==1 and len(siblingMaj)==1:
        majCond =   len(offspMaj)==len(spouseMaj)==  \
                    len(parentMaj)==len(siblingMaj)==1
        parOrien = links_df.at[parentMaj[0], 'lastOrientation(deg)']
        sibOrien = links_df.at[siblingMaj[0], 'firstOrientation(deg)']
        strtNodeLinearity = intersectionTurnType(parOrien, sibOrien) == 4
        avgOrienStrtNode = (parOrien + sibOrien) / 2.0
        angleBetnDivRds = abs(avgOrienStrtNode - avgOrienEndNode)
    if len(parentMaj)==0 and len(siblingMaj)==0 and len(singleParent)==1:
        #this is the case when left turn lane consists multiple links 
        majCond = len(offspMaj)==len(spouseMaj)
        parOrien = links_df.at[singleParent[0], 'lastOrientation(deg)']
        linkOrien = links_df.at[linkID, 'lastOrientation(deg)']
        strtNodeLinearity = intersectionTurnType(parOrien, linkOrien) == 4
        avgOrienStrtNode = None
        angleBetnDivRds = None
    return angleBetnDivRds, strtNodeLinearity, endNodeLinearity,    \
        avgOrienStrtNode, majCond


def leftTurnMajLink(leftTurnTo, links_df):
    leftTurnLn = False
    if len(leftTurnTo) >= 1:
        for leftTurnLink in leftTurnTo:
            if majorLinkChecker(leftTurnLink, links_df) == True:
                leftTurnLn = True
                break
    return leftTurnLn

def checkUTurnBayLeftTurnLane(linkID, links_df, nodes_df):
    '''
    detects if U-turn bay (shortlink) or left turn lane (not shortlink)
    '''
    #assume one major incoming, one outgoing at both start and end node
    #if issues occur, then would modify this assumption as needed
    try:
        MajNodeInOutLinks = findMajNodeParentSiblingSpouseOffsp(linkID, 
                                        links_df, nodes_df)
        spouseMaj,parentMaj,offspMaj,siblingMaj = MajNodeInOutLinks[0:4]
        leftTurnTo, singleParent = MajNodeInOutLinks[4:6]
    except AttributeError:
        return False, False
    
    if len(spouseMaj)!=1 or len(offspMaj)!=1 :
        return False, False
    try: 
        condLinearEndsChecker = checkNodeParentSiblingThu_NodeOffspSpouseThru(
                                linkID, spouseMaj, parentMaj, offspMaj,
                                siblingMaj, singleParent,links_df)
    except:
        return False, False
    angleBetnDivRds, strtNodeThru = condLinearEndsChecker[0:2]
    endNodeThru, avgOrienStrtNode, majCond = condLinearEndsChecker[2:5]
    
    if angleBetnDivRds is not None:
        divParallCnd = abs(angleBetnDivRds -180) < 20
        betnDividedMajorRds = strtNodeThru and endNodeThru and divParallCnd
    linkOrienStrt = links_df.at[linkID, 'firstOrientation(deg)']
    if avgOrienStrtNode is not None:    
        if sin(radians(0.1)) < sin(radians(avgOrienStrtNode-linkOrienStrt))  \
                        < sin(radians(50)):
            angularJunc = True
        else:
            angularJunc = False
    else:
        angularJunc = None
    #if major to major then this is a left turn lane, so do NOT identify as
    #intersection
    leftTurnToMajor = leftTurnMajLink(leftTurnTo, links_df)
    
    #lastly if there is a simple intersection shortlink outgoing/incoming on 
    #the right at the endNode, this is a left turn lane, not a u-turn bay only
    toNode = links_df.at[linkID, 'toNodeID_parade']
    try:
        outLinks = [int(i) for i in 
                 nodes_df.at[toNode, 'successorLinks'].split()]
    except:
        outLinks = []
    try:
        inLinks = [int(i) 
                  for i in nodes_df.at[toNode, 'predecessorLinks'].split()
                  if int(i) != linkID]
    except:
        inLinks = []
    hasIntShortlink = False
    for i in [inLinks, outLinks]:
        for j in i:
            if checkShortLink(j, links_df, nodes_df):
                hasIntShortlink = True
                break
    
    if len(parentMaj)==1 and len(siblingMaj)==1:
        uTurnDetected = (majCond and betnDividedMajorRds and angularJunc and 
                        (not leftTurnToMajor) and (not hasIntShortlink))
        leftTurnLaneDetected = (majCond and betnDividedMajorRds and angularJunc 
                                and (leftTurnToMajor or hasIntShortlink))
    #left tun lanes like link 25724
    else:
        uTurnDetected = False
        leftTurnLaneDetected = (majCond and endNodeThru and 
                                  (leftTurnToMajor or hasIntShortlink)) 
    return (uTurnDetected, leftTurnLaneDetected) 

def checkComplexIntrsectionShrtlnk(linkID, links_df, nodes_df):
    reverseID = int(links_df.at[linkID, 'reverseID_parade'])
    try:
        restrSucc=[int(i) for i in 
                   links_df.at[linkID, 'restrictedSuccessors'].split()]
    except AttributeError:
        try:
            restrSucc=[int(links_df.at[linkID, 'restrictedSuccessors'])]
        except ValueError:
            restrSucc = []

    try:
        restrPred=[int(i) for i in 
                   links_df.at[linkID, 'restrictedPredecessors'].split()]
    except AttributeError:
        try:
            restrPred = [int(links_df.at[linkID, 'restrictedPredecessors'])]
        except ValueError:
            restrPred = []
    try:
        offspAll = links_df.at[linkID, 'successors'].split()
        offsp = [int(i) for i in offspAll if int(i) not in restrSucc and 
                                            int(i) != reverseID]
    except AttributeError:
        offsp = []
    try:
        parentAll = links_df.at[linkID, 'predecessors'].split()
        parent = [int(i) for i in parentAll if int(i) not in restrPred and 
                                            int(i) != reverseID]
    except:
        parent = []
    lengthCond = links_df.at[linkID, "length(feet)"] <= 100
    majLinkCond = True
    if len(offsp)>=0 and len(parent)!=0:
        for x in [offsp, parent, [linkID]]:
            for link in x:
                majLinkCond = majLinkCond and majorLinkChecker(
                                                            int(link),links_df)
    else:
        majLinkCond = False
    shortlink = False
    typeC = len(restrPred) >= 1 and len(parent) == 1 and len(offsp) == 2
    typeB = len(restrSucc) >= 1 and len(offsp) == 1 and len(parent) == 2
    typeA = (len(restrPred) == len(restrSucc) == 1) and (len(offsp) == 
                                                         len(parent) == 1)
    if typeA or typeB or typeC:  
        shortlink = majLinkCond and lengthCond
    return  shortlink
            
    
if __name__ == '__main__':
    import pandas as pd
    import platform, os
    city = "Tucson"
    this_os = platform.system()
    if this_os == "Linux":
        fldr = "/media/asifrehan/shared_data_folder/"
    elif this_os == "Windows":
        fldr = r"D:\\"
    fldr=os.path.join(fldr, r"Metropia_docs/P1/{}_WKT".format(city))
    #fldr = "/media/asifrehan/shared_data_folder/Metropia_docs/NYNJ_WKT"
    links_df = pd.read_csv(os.path.join(fldr,"links_wkt.csv"))
    nodes_df = pd.read_csv(os.path.join(fldr,"nodes_wkt.csv"))
    
    #==========================================================================
    #print "u-turn"
    #==========================================================================
    #for i in [140, 13352, 19544, 25249, 9298, 4436,26925, 8566,2017, 19600, 17502, 
    #          25724, 7511, 8337,8331]: 
    #==========================================================================
    #     #7511 should not pass OK
    #    #13352, 8566, 19544 --> left turn lane,so should be false  
    #    print i, ' ', checkUTurnBayLeftTurnLane( i, links_df, nodes_df)
    # print "complex intersection"
    #==========================================================================
    for i in [5472
               #20401, 19555, 27629, 13138, 10953, 17518, 17266, 1883, 24455, 
                #14523, 3940, 23928, 8331
                ]: #8331 
    #        --> no parent, offspring. Shd get caught
        print i, ' ', checkComplexIntrsectionShrtlnk(i, links_df, nodes_df)
    #==========================================================================
    # print checkUTurnBayLeftTurnLane(9624, links_df, nodes_df)
    # print checkUTurnBayLeftTurnLane(15822, links_df, nodes_df)
    #==========================================================================
    #==========================================================================
    # for i in range(len(links_df)):
    #     if checkUTurnBayLeftTurnLane(i, links_df, nodes_df):
    #         print i, " = ", links_df.at[i, 'length(feet)']
    #==========================================================================
    