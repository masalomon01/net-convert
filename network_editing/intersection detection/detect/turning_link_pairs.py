'''
Created on Sep 11, 2015

@author: asifrehan
'''
import math
from intersectionTurnType import intersectionTurnType
from complex_intersection_uTurn_bay import leftTurnMajLink, findMajNodeParentSiblingSpouseOffsp
from shortlink_identification import parentOffspringTurnBin
    
def findTargetLinkRecurse(fromLinkID, currentLinkID, currentNodeID, visitedNodes, visitedLinks,
                          links_df, shortlink_df, linksB, node_subpath={}):
    '''
    Most important function which does most of the heavy-lifting
    
    pseudo code (incomplete, need to update for the node_subpath and nodeTrees)
    ===========
    
    FUNCTION findTargetLinkRecurse()

    1. initialize <-- actually done in findTargetLinkPairsWithNodeLinkSeq()
    -------------
    linksB = []         is the set of links which are reachable from the fromLink by 
                        making some maneuvers at the intersection
    currentLinkID = [fromLink ID]
    visitedNodes = [toNode of fromLink]
    visitedLinks = [fromLink ID]
    
    2. Search
    ---------
    SET node_subpath = {}
    SET link_subpath = {}
    SET nodeTrees = []
    SET all_leaf_children_links_under_current_node = [] 

    FOR eachlink of the successor links:
        IF the toNode of the link is not in visitedNodes and link is not invisitedLinks
            IF the link is intersection link
                P = recursive call self and pass this current link    <-- returns from bottom up
                combine all `immediately next leaf children links under current node` with all the ones from P
                merge all the current nodesubpaths with the ones returned from P
                merge all the current linksubpaths with the ones returned from P   
            ELSE
                add the link to linksB
                add the link as a key in nodesubpath and linksubpath
                add the link to all_leaf_children_links_under_current_node
        FOR each of the maneuver toLinks found below the currentLinkID
            add the currentLinkID to each of the link subpaths
            add the currentNodeID to each of the node subpaths
    **args**
    --------
        fromLinkID: *int*
            the root linkID from which search starts
        currentLinkID: *int* 
            current link from which search is expanding. Current link is downstream of fromLinkID
        currentLinkID: *int* 
            current toNode from which search is expanding
        visitedNodes: *list*
            list of nodes visited
        visitedLinks: *list*
            list of links visited
        links_df: *pandas.DataFrame*
            Original link_wkt file converted to an DataFrame
        shortlink_df: *pandas.DataFrame*
            Dataframe of the appended WKT file from step#1   
        linksB: *nested list*
            Holds the link ID's to which maneuvers are possible. 
        node_subpath_dict: *dict*
            sequence of nodes in the subpaths. Initiate with empty dict. Gets filled bottom up.
        
        **returns**
        -----------
        linksB: *nested list*
            same as above
        nodeTree:*nested list of list*
            a nested list representing the search tree of the nodes to reach the end node of the toLinks (leaf links)
            See findTargetLinkPairsWithNodeLinkSeq() for details
        link_subpath_dict:*dict*
            sequence of nodes in the subpaths. See findTargetLinkPairsWithNodeLinkSeq() for details
        all_leaf_children_links_under_current_node: *nested list* 
            stores all the toLinks that makes maneuvers from the root `fromLinkID`. Only used to feed into the 
            recursion.
            
    '''
    node_subpath = {}
    link_subpath = {}
    nodeTrees = []
    all_leaf_children_links_under_current_node = []
    try:
        offsprings = links_df.at[currentLinkID, "successors"].split()
        reverseID = links_df.at[currentLinkID, "reverseID_parade"]
        #need to include reverseID for first link or when depth of linkB==1
        try:
            binned = parentOffspringTurnBin(currentLinkID, 'successor', links_df)
        except:
            binned = []
        if currentLinkID != fromLinkID:
            offsprings = [int(i) for i in offsprings 
                      if int(i)!= reverseID and 
                        not (shortlink_df.iloc[int(i)].values[0]==True and 
                         int(i) in binned[0])]
        else:
            offsprings = [int(i) for i in offsprings 
                      if not (shortlink_df.iloc[int(i)].values[0]==True and 
                         int(i) in binned[0])]
        #offsprings do not contain any reverse link or intersection links which are to
        #the right of the current link
        succ_nodeseq = []
        
        leaf_children_links_under_current_node = []
        for link_ in offsprings:
            node_ = links_df.at[link_, "toNodeID_parade"]
            if node_ not in visitedNodes and link_ not in visitedLinks:
                visitedLinks.append(link_)
                visitedNodes.append(node_)
                if shortlink_df.iloc[int(link_)].values[0]==True:
                    linksB, succ, x, y,z = findTargetLinkRecurse(fromLinkID, link_, node_, visitedNodes, visitedLinks, 
                                                            links_df, shortlink_df, linksB, node_subpath)
                    node_subpath = dict(node_subpath, **y)
                    link_subpath = dict(link_subpath, **x)
                    succ_nodeseq.append(succ)
                    all_leaf_children_links_under_current_node += z
                     
                else:
                    leaf_children_links_under_current_node.append(link_)
                    succ_nodeseq.append([node_, "manID here"])
                    node_subpath[link_] = [node_]
                    link_subpath[link_] = [link_]
                    
        all_leaf_children_links_under_current_node += leaf_children_links_under_current_node
        for subpath in all_leaf_children_links_under_current_node:
            node_subpath[subpath].insert(0, currentNodeID)
            link_subpath[subpath].insert(0, currentLinkID)
        nodeTrees  = [currentNodeID, succ_nodeseq]
        linksB += leaf_children_links_under_current_node
    except AttributeError:  
        # handles corner cases if link does not have successors
        pass
    return linksB, nodeTrees, link_subpath, node_subpath, all_leaf_children_links_under_current_node
    #linksB has depth equal to the number of intersection shortlinks
    #needed to be crossed to reach the target links from the current link 

def findTargetLinkPairsWithNodeLinkSeq(fromLinkID, links_df, shortlink_df):
    '''
    given a link, it find all the other links to which maneuvers are possible. Provides all such target links, 
    and the subpaths. For the heavy-lifting, it calls a recursive function and passes the initial values for process. 
    
    **args**
    --------
        fromLinkID: *int*
            linkID 
        links_df: *pandas.DataFrame*
            Original link_wkt file converted to an DataFrame
        shortlink_df: *pandas.DataFrame*
            Dataframe of the appended WKT file from step#1   
    
    **returns**
    -----------
        flat_turn_links: *list*
            a flat list of links to which legal turns are possible
        nodeTree:*nested list of list*
            a nested list representing the search tree of the nodes to reach the end node of the toLinks (leaf links)
            format:
                nested lists store the node ID's that was traversed to find the target maneuver link. If the last node
                is the end of a maneuver, it puts a flag 'manID here'. For example:
                [fistNode_of_fromLink, [
                                        [toNode_of_fromLink, 'manID here'], 
                                        [toNode_of_toLink1, 'manID here'], 
                                        [toNode_of_an_intersectionLink, [
                                                                         [toNode_of_toLink2, 'manID here']]]]]
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
    '''
    fromNodeID = links_df.at[fromLinkID, "fromNodeID_parade"]
    toNodeID = links_df.at[fromLinkID, "toNodeID_parade"]
    visitedNodes = [toNodeID]
    visitedLinks = [fromLinkID]
    deepLinksB,nodeTree,link_subpath, node_subpath  = findTargetLinkRecurse(fromLinkID, fromLinkID, toNodeID, visitedNodes, 
                                                                            visitedLinks, links_df, shortlink_df, 
                                                                            linksB=[])[:-1]
    flat = deepListFlattener(deepLinksB, [])
    node_subpath_dict = {fromNodeID:node_subpath}
    link_subpath_dict = {fromLinkID:link_subpath}
    flat_turn_links = list(set(flat))
    return flat_turn_links, nodeTree, node_subpath_dict, link_subpath_dict

def deepListFlattener(L, flatList):
    for i in L:
        if type(i) != list:
            flatList.append(i)
        if type(i) == list:
            deepListFlattener(i, flatList)
    return flatList

def fromNodeLatLon(linkA, links_df, nodes_df):
    fromNode = links_df.at[linkA, 'fromNodeID_parade']
    idx_lon = nodes_df.at[fromNode, 'WKT'].find('(') + 1
    fromLonLat = [float(i) for i in nodes_df.at[fromNode, 'WKT'][idx_lon:-1].split()]
    x = fromLonLat[0]
    y = fromLonLat[1]
    return x, y


def toNodeLatLon(linkB, links_df, nodes_df):
    toNode = links_df.at[linkB, 'toNodeID_parade']
    idx_lon = nodes_df.at[toNode, 'WKT'].find('(') + 1
    toLonLat = [float(i) for i in nodes_df.at[toNode,'WKT'][idx_lon:-1].split()]
    x = toLonLat[0]
    y = toLonLat[1]
    return x, y


def magneticBearingFromNodeToNodeStraightLine(linkA, links_df, nodes_df):
    x1, y1 = fromNodeLatLon(linkA, links_df, nodes_df)
    x2, y2 = toNodeLatLon(linkA, links_df, nodes_df)
    angle = math.degrees(math.atan2(x2 - x1, y2 - y1))
    bearing = (angle + 360) % 360
    return bearing

def linkPairBWithTurnTypeNodeLinkSeq(linkA, links_df, nodes_df, shortlink_df):
    '''
    gets the list of links to which maneuvers can be made based on the topological information. 
    Also finds the node and link subpaths
    
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
    ----------- 
        pairB:*list* 
            a flat list of links to which legal turns are possible
        findLinkFromTurn:*list of list*
            left, right, thru and u-turns are grouped in the list
            format:
                [[rightTurnLink1,...],[lefttTurnLink1,...], [uTurnLink1,...], [thruMovementLink1,...]]
        findTurnForLink:*dict*
            stores turn type for the target maneuver link
            format:
                {toLink1:turnType, toLink2:turnType, toLink3:turnType, ...}
            
            turnType Code:
            
                * turnType = 1 if right turn
                * turnType = 2 if left turn
                * turnType = 3 if u-turn
                * turnType = 4 if thru turn
        nodeTree:*nested list of list*
            a nested list representing the search tree of the nodes to reach the end node of the toLinks (leaf links)
            format:
                nested lists store the node ID's that was traversed to find the target maneuver link. If the last node
                is the end of a maneuver, it puts a flag 'manID here'. For example:
                [fistNode_of_fromLink, [
                                        [toNode_of_fromLink, 'manID here'], 
                                        [toNode_of_toLink1, 'manID here'], 
                                        [toNode_of_an_intersectionLink, [
                                                                         [toNode_of_toLink2, 'manID here']]]]]
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
    '''
    findLinkFromTurn = [[], [], [], []]     #[right, left, u-turn, thru]
    findTurnForLink = {}
    pairB, nodeTree, node_subpath_dict, link_subpath_dict = findTargetLinkPairsWithNodeLinkSeq(linkA, links_df, 
                                                                                               shortlink_df)
    #ususal cases
    linkA_orien = links_df.at[int(linkA), 'lastOrientation(deg)']
    #if left turn lane,linkB_orien is straight line angle between
    #fromNode and toNode
    #Lef turn lane is identified as
    #firstOrientation  > last orientation (indicates left bend)
    #major spouse and major offspring lining up.
    #existence of a successor link which is major and seems thru and is not
    #major spouse or major offspring
    leftTurnTo = findMajNodeParentSiblingSpouseOffsp(linkA, links_df, 
                                                     nodes_df)[4]
    lftTurnLn = leftTurnMajLink(leftTurnTo, links_df)
    if lftTurnLn:
        bearing = magneticBearingFromNodeToNodeStraightLine(linkA, links_df, 
                                                            nodes_df)        
        linkA_orien = bearing  
    
    for link in pairB:    
        linkB_orien = links_df.at[int(link), 'firstOrientation(deg)']
        turn = intersectionTurnType(linkA_orien, linkB_orien)
        findLinkFromTurn[turn-1].append(int(link))
        findTurnForLink[int(link)] = turn
    return pairB, findLinkFromTurn, findTurnForLink, nodeTree, node_subpath_dict, link_subpath_dict

if __name__=='__main__':
    import pandas as pd
    import os
    city = 'Tucson'
    fldr = os.path.join("D:\Metropia_docs\P1\{}_WKT".format(city))
    links_df = pd.read_csv(fldr+"/links_wkt.csv")
    nodes_df = pd.read_csv(fldr+"/nodes_wkt.csv")
    newWriteToFile = fldr+"/checkShortlinkTucson.txt".format(city)
    shortlink_df = pd.read_csv(newWriteToFile,
                               usecols=["intersectionShortlinkCheck", 
                                        'leftTurnOnlyLane'])
    for lnk in [7700, 1118, 1, 12987,16929]:
        for out in linkPairBWithTurnTypeNodeLinkSeq(lnk, links_df, nodes_df, shortlink_df):
            print out
        print "\n"
    print "linkPairBWithTurnTypeNodeLinkSeq()\n-----------------------------"
    for linkA in [7700, 1118, 1, 12987,16929]:
        for out in linkPairBWithTurnTypeNodeLinkSeq(linkA, links_df, nodes_df, shortlink_df):
            print out
        print "\n\n"
    