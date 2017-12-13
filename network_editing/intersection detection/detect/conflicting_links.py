'''
Created on Sep 24, 2015

@author: asifrehan
'''
import os
import numpy as np
from turning_link_pairs import linkPairBWithTurnTypeNodeLinkSeq, fromNodeLatLon, \
            toNodeLatLon, magneticBearingFromNodeToNodeStraightLine
from shortlink_identification import parentOffspringTurnBin, majorLinkChecker,\
    sameDirectionChecker
from intersectionTurnType import intersectionTurnType


def upstreamLink(linkID, linkID_LType, links_df, shortlink_df):
    thruParents = parentOffspringTurnBin(int(linkID),'predecessor',links_df)[1]  
    if len(thruParents)==0:
        return None #no-upstream example: link 6758 in Tucson
    deviation_from_target_link = []
    for thruParent in thruParents:
        deviation =sameDirectionChecker(links_df.at[linkID, 'firstOrientation(deg)'], 
                         links_df.at[thruParent, 'lastOrientation(deg)'])
        deviation_from_target_link.append((thruParent,abs(deviation)))
    a = np.array(deviation_from_target_link)
    sorted_on_deviation = a[a[:,1].argsort()]
    thruParents = sorted_on_deviation[:,0] 
    # ^ ranks the thruParents on how closely they align with target linkID 
    for thruParent in thruParents:
        thruParentLType = links_df.at[int(thruParent), 'ltype']
        thruParShtLnkChk = shortlink_df.iloc[int(thruParent)].values[0]        
        if thruParShtLnkChk != True:
            if len(thruParents) > 1:
                if thruParentLType == linkID_LType:
                    return thruParent
            if len(thruParents) == 1:
                return int(thruParent)
        else:
            return upstreamLink(int(thruParent),
                                linkID_LType, links_df, shortlink_df)
                        
def oppositeLink(findLinkFromTurn, links_df, shortlink_df):
    for link in findLinkFromTurn[2]: #u-turn link from linkA
        majorlinkChk = majorLinkChecker(int(link), links_df)
        if majorlinkChk:
            linkID_LType = links_df.at[int(link), 'ltype']
            return upstreamLink(link, linkID_LType, links_df, shortlink_df)

def findDividedOrUndevidedMajNodeSpouseOffsp(linkID, links_df, 
                                                          nodes_df):
    '''find major divided or undivided spouse, 
    offspring from the end node of 
    the current link
    '''
    toNode = links_df.at[linkID, 'toNodeID_parade']
    offsp = nodes_df.at[toNode, 'successorLinks'].split()
    offspMaj = [int(i) for i in offsp 
                if majorLinkChecker(int(i), links_df) == True]
    spouseEndNodeLinksAll = nodes_df.at[toNode, 'predecessorLinks'].split()
    spouseMaj = [int(i) for i in spouseEndNodeLinksAll 
                 if majorLinkChecker(int(i), links_df) == True 
                    and int(i) != linkID]
    return spouseMaj, offspMaj

def checkMinorToMinorAcrossMajor(linkA_Ltype,linkB_Ltype,
                                linkA,linkB, links_df, nodes_df):
    '''
    Typical case: when crossing major road
                 
                 /\
                 / minor link B
                /
         =====>+=====> major road 
              /\  
              /  minor link A
             /
         
    Special case: left turn lane meeting major road
        
         <======+<========+<======= Major road X   
                 |        /
                 |/-----/  Minor left turn lane A 
                 |
                 V
         =======>+=========> Major road Y
                 |
                 | Minor road B
                 V   
    '''
    TurnBetnMinorsNotAcrossMajor = (linkA_Ltype == linkB_Ltype == 11)
    if TurnBetnMinorsNotAcrossMajor == True:    
        temp = findDividedOrUndevidedMajNodeSpouseOffsp(linkA, links_df, 
                                                   nodes_df)
        spouseMaj, offspMaj = temp[0], temp[1]
        spMajLen = len(spouseMaj)
        offspMajLen = len(offspMaj)
        if spMajLen==0 or offspMajLen==0:
            return TurnBetnMinorsNotAcrossMajor
            
        if spMajLen>0 or offspMajLen>0:
            #finds the major links on a straight line: leftSpouse, rttOffspring
            diff = 666
            lftSps = None
            rtOffsp = None
            for i in spouseMaj:
                spOrien = links_df.at[i, 'lastOrientation(deg)']
                for j in offspMaj:
                    offspOrien = links_df.at[j, 'lastOrientation(deg)']
                    delta = abs(spOrien - offspOrien)
                    if delta <= diff:
                        diff = delta
                        lftSps = i
                        rtOffsp = j
            
        #Now check the end nodes of linkA and linkB using this 
        #http://math.stackexchange.com/a/274728/172410
        #construct vector using fromNode of spouseMajor and toNode of offspMaj 
        
        x1, y1 = fromNodeLatLon(lftSps, links_df, nodes_df)
        x2, y2 = toNodeLatLon(rtOffsp, links_df, nodes_df) 
        
        #check which side (+/-) is the fromNode of linkA
        x, y = fromNodeLatLon(linkA, links_df, nodes_df)
        d1 = (x-x1)*(y2-y1) - (y-y1)*(x2-x1)
        #check if side toNode of linkB falls on the other side
        x, y = toNodeLatLon(linkB, links_df, nodes_df)
        d2 = (x-x1)*(y2-y1) - (y-y1)*(x2-x1)
        #conclude if minor roads are crossing over a pair of linear major roads
        if (d1<0 and d2>0) or (d1>0 and d2<0):
            TurnBetnMinorsNotAcrossMajor = False  
    
    return TurnBetnMinorsNotAcrossMajor
        
def singlThruMaj(linkA, linkA_Ltype, linkB, linkB_Ltype, findLinkFromTurn, 
                  thru_offsp, thru_maj_offsp, 
                  links_df, nodes_df, shortlink_df):
    toNode = links_df.at[linkA, 'toNodeID_parade']
    #first check: if any successor or predecessor link is an intersection 
    #shortlink then through movement is likely signalized 
    majMajThruNoIntrsction = True
    for inOut in ['predecessor', 'successor']:
        try:
            for i in nodes_df.at[toNode, inOut + 'Links'].split():
                if (int(i) != linkA and int(i) != linkB and 
                    int(i) not in thru_offsp):
                    #among the links incoming and outgoing at to-node
                    if shortlink_df.iloc[int(i)].values[0] == True:
                        #if any one of them is shortlink
                        majMajThruNoIntrsction = False
                        break
        except:
            pass
    

    
    #second check: if left and right successors are bidirectional and each of
    #them are major links and through link is also a major link
    if majorLinkChecker(linkA, links_df)==majorLinkChecker(linkB, links_df)  \
                    and links_df.at[linkA, 'reverseID_parade']!=-1   \
                    and links_df.at[linkA, 'reverseID_parade']!=-1:
        for links in findLinkFromTurn[0:2]:
            for link in links:
                if majorLinkChecker(link, links_df) and    \
                    links_df.at[link, 'reverseID_parade']!=-1:
                        majMajThruNoIntrsction = False
                        break
    single_thru_major = int(linkB) in findLinkFromTurn[3] and   \
                        int(linkB) in thru_maj_offsp and   \
                        linkA_Ltype == linkB_Ltype and majMajThruNoIntrsction
                            
    return single_thru_major

def findConflictingLinks(linkA,links_df, nodes_df, shortlink_df):
    """
    determines
     
        1.1 the maneuver link pairs
        1.2 turn type
        1.3 conflicting links
        1.4 ltype of the conflicting links
        1.5 constant delays, if that applies for that maneuver
        2.  node subpath of the maneuver
        3.  link subpath of the maneuver
        
    Excludes these from being identified as valid maneuvers because these do not have any maneuver delay: 
        
        1. maneuver from one ramp link to the next ramp link
        2. movement along curvy freeways links 
        3. single_thru_major
        4. special case: major link to a left turn lane (detected as left turn link in previous step) 
     
    Assumes, linkA to be a non-intersection-shortlink.
    So check for this condition before calling this function
    
    **args**
    --------
        linkA: *int*
            linkID
        links_df: *pandas.DataFrame*
            Original link_wkt file converted to an DataFrame
        nodes_df: *pandas.DataFrame*
            Original node_wkt file converted to an DataFrame 
        shortlink_df*pandas.DataFrame*
            Dataframe of the appended WKT file from step#1, using main_intersection_shortlink_filter()
        
    **returns**
        turn_pairs:*list of list*
            in each list element it holds the information about the maneuvers, 1.1~1.5
            format:
                [[fromLink,toLink, turnType, fromLinkLtype,toLinkLtype, conflicting link1,conflicting link2, constant],
                ..., [..]]
        link_subpath_dict:*dict*
            sequence of nodes in the subpaths
            format:
                {fistNode_of_fromLink: {toLink1: [fistNode_of_fromLink, nodeP, nodeQ, ..., toNode_of_toLink1], 
                                        toLink2: [fistNode_of_fromLink, nodeM, nodeN, ..., toNode_of_toLink2],
                                        ...}}
        node_subpath_dict:*dict*
            sequence of nodes in the subpaths
            format:        
                {fromLink: {toLink1: [fromLink, linkP, linkQ,...,toLink], 
                            toLink2: [fromLink, linkM, linkN,...,toLink2],
                            ...}}
    """
    returned_tuple = linkPairBWithTurnTypeNodeLinkSeq(linkA, 
                                                        links_df,nodes_df, shortlink_df)
    pairB, findLinkFromTurn, findTurnForLink = returned_tuple[:3] 
    node_subpath_dict, link_subpath_dict = returned_tuple[4:6]
    linkA_Ltype = links_df.at[int(linkA), 'ltype']
    offsp = parentOffspringTurnBin(linkA, 'successor', links_df)
    thru_offsp = offsp[1]
    thru_maj_offsp = [i for i in thru_offsp if 
                      majorLinkChecker(linkA, links_df) == True]
    turn_pairs = []
    for linkB in pairB:
        linkB_Ltype = links_df.at[int(linkB), 'ltype']
        TurnBetnMinorsNotAcrossMajor = checkMinorToMinorAcrossMajor(
                                            linkA_Ltype, linkB_Ltype, 
                                            linkA,linkB, 
                                            links_df, nodes_df)                
        turnBetnRamps = (linkA_Ltype == linkB_Ltype == 3)
        moveBetnFreeways =  (linkA_Ltype == linkB_Ltype == 1)
        single_thru_major = singlThruMaj(linkA, linkA_Ltype, 
                                          linkB, linkB_Ltype, findLinkFromTurn,
                                        thru_offsp, thru_maj_offsp, 
                                        links_df, nodes_df, shortlink_df)
        if not (turnBetnRamps or moveBetnFreeways or single_thru_major): 
            confLinkX, confLinkY, const = confLinkPair(linkA, linkA_Ltype, 
                                    int(linkB), linkB_Ltype, findLinkFromTurn,
                                    findTurnForLink, TurnBetnMinorsNotAcrossMajor, links_df,shortlink_df)
            turn_pairs.append([int(linkA), int(linkB), findTurnForLink[int(linkB)],  \
                            linkA_Ltype, linkB_Ltype,  \
                            confLinkX, confLinkY, const])
        else:
            del node_subpath_dict[node_subpath_dict.keys()[0]][linkB]
            del link_subpath_dict[link_subpath_dict.keys()[0]][linkB]
    
    return (turn_pairs, node_subpath_dict, link_subpath_dict)
        
def confLinkPair(linkA, linkA_LType, linkB, linkB_LType, 
                 findLinkFromTurn, findTurnForLink, TurnBetnMinorsNotAcrossMajor,
                 links_df, shortlink_df):
    '''
    this conflicting links finding funtion needs to be cleaned up and 
    streamlined. So many arbitrary conditions make it clouded.
    To avoid falling in undefined traps, assign default values first and
    update for individual maneuver cases.
    '''
    #==========================================================================
    # default values here
    #==========================================================================
    confLinkX = linkA
    confLinkY = None
    const = None
    #==========================================================================
    # for individual conditions
    #==========================================================================
    turnType = findTurnForLink[int(linkB)]
    if (linkA_LType == 5 or linkA_LType==7) and  \
       (linkB_LType == 5 or linkB_LType==7 or linkB_LType==3):
        #main to main intersection
        if turnType == 1: #right turn
            
            confLinkY = upstreamLink(linkB, linkB_LType, links_df,shortlink_df)

        if turnType == 2 or turnType == 3: #left turn or u-turn
            
            if shortlink_df.at[linkA, 'leftTurnOnlyLane']:    
                if findLinkFromTurn[2] != []:
                    confLinkY = upstreamLink(findLinkFromTurn[2][0], 
                                        linkA_LType, links_df, shortlink_df)
                else:
                    spMaj = findDividedOrUndevidedMajNodeSpouseOffsp(linkA, 
                                                        links_df, nodes_df)[0]
                    orien = magneticBearingFromNodeToNodeStraightLine(linkA, 
                                                            links_df, nodes_df)
                    for x in spMaj:
                        orienOpposite= links_df.at[x, 'lastOrientation(deg)']
                        if intersectionTurnType(orien, orienOpposite)==3:
                            confLinkY = x
            else:
                confLinkY = oppositeLink(findLinkFromTurn, links_df, 
                                             shortlink_df)
                if confLinkY is None:
                    confLinkY = upstreamLink(linkB, linkB_LType, 
                                         links_df,shortlink_df)

        if turnType == 4: # thru
            pass    #gets default values
            
        
    if (linkA_LType == 5 or linkA_LType==7  or linkB_LType==3) and   \
                            linkB_LType == 11:
        if turnType == 1: #right turn
            confLinkX = None    # voids default, special case 
            const = 3
        if turnType == 2: 
            #left turn from major to minor typically happens at u-turn bays
            confLinkX = oppositeLink(findLinkFromTurn, links_df, shortlink_df)
        if turnType == 3: #u-turn to major to minor is a rare case
            confLinkX = oppositeLink(findLinkFromTurn,links_df,shortlink_df)
        if turnType == 4: 
            #e.g. 21440-->19544, major to left turn lane (minor)
            confLinkX = None    # voids default, special case
            const = 3

    if linkA_LType == 11 and   \
                (linkB_LType == 5 or linkB_LType==7 or linkB_LType==3):
        if turnType == 1: #right or thru from merging minor
            confLinkX = upstreamLink(linkB, linkB_LType, links_df,shortlink_df)

        if turnType==2 or turnType==3:
            if turnType == 2:                
                if shortlink_df.at[linkA, 'leftTurnOnlyLane']:
                    try:
                        confLinkX = upstreamLink(findLinkFromTurn[2][0], 
                                        linkB_LType, links_df, shortlink_df)
                    except:
                        confLinkX = linkB
                    confLinkY = linkA
                else:
                    try:
                        confLinkX = upstreamLink(linkB, linkB_LType, 
                                                 links_df,shortlink_df)
                    except:
                        confLinkX = None    #changes default
                    try:
                        confLinkY = upstreamLink(findLinkFromTurn[0][0],
                                            linkB_LType,links_df, shortlink_df)
                    except:
                        pass #default confLinkY = None    
                
                #for minor left turn lanes: conflicting links are different
        
            if turnType == 3:
                #minor LinkA can be a left turn lane, so should be treated as a 
                #major to major turn actually
                try:
                    confLinkX=upstreamLink(linkB, linkB_LType, links_df, 
                                           shortlink_df)
                except:
                    try:
                        linkU = [int(i) for i in findLinkFromTurn[2] if 
                                 int(links_df.at[int(i), 'reverseID_parade']!=int(i))]
                        confLinkX=upstreamLink(linkU[0], 
                                        linkB_LType, links_df, shortlink_df)
                    except:
                        confLinkX = linkB
                #if linkA is a U-turn lane or left turn lane (undetected), 
                #it is a conflicting link
                
                if shortlink_df.at[linkA, 'leftTurnOnlyLane']:
                    confLinkY = linkA
                else:
                    try:
                        confLinkY = upstreamLink(findLinkFromTurn[0][0], 
                                        linkB_LType, links_df, shortlink_df)
                    except:
                        try:
                            confLinkY = upstreamLink(findLinkFromTurn[3][0], 
                                    linkB_LType, links_df, shortlink_df)
                        except:
                            pass #default confLinkY = None            

                
        if turnType == 4:
            try:
                confLinkX = upstreamLink(linkB, linkB_LType, 
                                         links_df,shortlink_df)
            except:
                try:
                    confLinkX = upstreamLink(findLinkFromTurn[0][0],
                                            linkB_LType, links_df,shortlink_df)
                except:
                    confLinkX = linkB
            
    if linkA_LType==linkB_LType==11:
        if TurnBetnMinorsNotAcrossMajor==True:
            confLinkX = None
            if turnType==1:
                const = 4
            if turnType==2:
                const = 4
            if turnType==3:
                const = 10
            if turnType==4:
                const = 2
                
        if TurnBetnMinorsNotAcrossMajor==False:
            if shortlink_df.at[linkA, 'leftTurnOnlyLane']:
                try:
                    linkU = [int(i) for i in findLinkFromTurn[2] if 
                            int(links_df.at[int(i), 'reverseID_parade']!=int(i))]
                    confLinkY = upstreamLink(linkU[0], 
                                    linkB_LType, links_df, shortlink_df)
                except:
                    confLinkY = linkB
        
            else:
                try:
                    confLinkX = upstreamLink(findLinkFromTurn[0][0],
                                         5,links_df, shortlink_df)  \
                            or upstreamLink(findLinkFromTurn[0][0],
                                         7,links_df, shortlink_df)
                except:
                    confLinkX = None
                try:
                    confLinkY = upstreamLink(findLinkFromTurn[1][0],
                                         5,links_df, shortlink_df)  \
                            or upstreamLink(findLinkFromTurn[1][0],
                                         7,links_df, shortlink_df)
                except:
                    pass #default confLinkY = None
            
    if (linkA_LType == 3 and linkB_LType !=3) or  \
       (linkA_LType != 3 and linkB_LType ==3):
        if turnType==1:
            
            confLinkY = upstreamLink(linkB, linkB_LType, links_df,shortlink_df)

            
        if turnType == 2 or turnType == 3: #left turn or u-turn
            
            confLinkY = oppositeLink(findLinkFromTurn, links_df, 
                                         shortlink_df)
            if confLinkY is None:
                confLinkY = upstreamLink(linkB, linkB_LType, 
                                         links_df,shortlink_df)

        if turnType==4:
            
            y = upstreamLink(linkB, linkB_LType, 
                                         links_df,shortlink_df)
            if y != linkA:
                confLinkY = y

            
    if (linkA_LType == 1 and linkB_LType !=1) or  \
       (linkA_LType != 1 and linkB_LType ==1):
        pass    #default, only fromLink impacts

    return confLinkX, confLinkY, const
    
if __name__ == "__main__":
    import pandas as pd
    city = 'Austin'
    fldr = os.path.join("D:\Metropia_docs\P1\{}_WKT".format(city))
    links_df = pd.read_csv(fldr+"/links_wkt.csv")
    nodes_df = pd.read_csv(fldr+"/nodes_wkt.csv")
    newWriteToFile = fldr+"\checkShortlink{}.txt".format(city.capitalize())
    shortlink_df = pd.read_csv(newWriteToFile,
                               usecols=["intersectionShortlinkCheck", 
                                        'leftTurnOnlyLane'])
    #==========================================================================
    # print "minor --> major (right, left)"
    # for conf in findConflictingLinks(133439, links_df, shortlink_df):
    #     print conf
    # print "major --> minor left"
    # for conf in findConflictingLinks(17122, links_df, shortlink_df):
    #     print conf
    # print "Divided Major --> Undivided Major"
    # for i in [10598, 9303, 22827, 18785]:
    #     print "linkID_parade = ", i
    #     for conf in findConflictingLinks(i, links_df, shortlink_df):
    #         print conf
    #==========================================================================
    #==========================================================================
    # if shortlink_df.iloc[int(8331)].any() == 0:
    #     for conf in findConflictingLinks(8331, links_df, shortlink_df):
    #         print conf
    #==========================================================================
    #==========================================================================
    # for test in [13352, 28161, 135982, 104, 1252, 9756, 22205, 180, 102548, 
    #    148232, 264, 23790,  18913, 16871, 2400, 8474, 14051, 11023, 13476, 
    #    14628, 20600, 20629, 19387, 1780, 10663, 6491]:
    #     # 102548, 148232 --> minors to minor across major --> should yield
    #     print test
    #     for i in findConflictingLinks(test, links_df, nodes_df,shortlink_df):
    #         print i 
    
    #5625 should have 4 to-links, needs to identify the thru link 22333 too.
    
    #==================================================================================================================
    # for tuc in [1, 5625, 14043, 112893, 19072, 97018, 27524, 5724, 11508, 19544, 4061, 21440, 13352, 10612, 
    #             77553, 169639]:
    #     for i in findConflictingLinks(tuc, links_df, nodes_df,shortlink_df):
    #         print i
    # 
    #==================================================================================================================
    for i in findConflictingLinks(31409, links_df, nodes_df,shortlink_df):
            print i
    