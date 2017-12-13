'''
Created on Sep 9, 2015

@author: asifrehan
'''
import  os
import numpy as np
import pandas as pd

def ParentOffspringAngleChecker(offspAngleLinkZipFWSorted):
    '''
    checks the angle of a set of links and categorizes them into turn movements
    **peudocode**
        right turn:     angle<-40 and (difference with -90)<=50
        thru movement:  -40<angle<40
        leftt turn:     angle>40 and (difference with +90)<=50
        u-turn:         -145<angle or angle>145
    **inputs**
    offspAngleLinkZipFWSorted:*dict*
        dictionary where (key,value)= (angle,linkID)
    **output**
    [right, thru, left, uTurn]:*list*
        list with four elements, each of these store the linkID's which are makes right, thru, left or u-Turn
    
    '''
    right = []
    thru = []
    left = []
    uTurn = []
    for angle in offspAngleLinkZipFWSorted.keys():
        if float(angle) < -40 and abs((-90 - float(angle))) <= 50:
            right.append(int(offspAngleLinkZipFWSorted[angle]))
        if abs(float(angle)) <= 40:
            thru.append(int(offspAngleLinkZipFWSorted[angle]))
        if float(angle) > 40 and abs(float(angle) - 90) <= 50:
            left.append(int(offspAngleLinkZipFWSorted[angle]))
        if abs(float(angle)) > 145:
            uTurn.append(int(offspAngleLinkZipFWSorted[angle])) 
    
    return [right, thru, left, uTurn]

def parentOffspringTurnBin(linkID, parentOrOffsp, links_df):
    '''if searching for parent,  parentOrOffsp = "predecessor"
    if searching for offspring,  parentOrOffsp = "successor"
    '''
    linkID = int(linkID)
    try:
        angles = links_df.at[linkID, parentOrOffsp+"Angles"].split()
    except:
        angles = links_df.at[linkID, parentOrOffsp+"Angles"]
    try:
        links = links_df.at[linkID, parentOrOffsp+"s"].split()
    except:
        links = links_df.at[linkID, parentOrOffsp+"s"]
    try:
        angleLinkDict = dict(zip(angles, links))
        orien = ParentOffspringAngleChecker(angleLinkDict)
        #orientation of links format:= [right, thru, left, uTurn]
    except TypeError:
        orien = [[], [], [], []]
    return orien

def majorLinkChecker(linkID, links_df):
    linktype = links_df.at[int(linkID), 'ltype']
    return (linktype == 5) or (linktype == 7)

def minorLinkChecker(linkID, links_df):
    linktype = links_df.at[int(linkID), 'ltype']
    return linktype == 11
        
def adjLinktypeChecker(linkID, offspOrien, parentOrien,
                            rightSpouse,rightSibling, links_df):
    fromNodeLR = parentOrien[2], rightSibling
    toNodeLR = offspOrien[2], rightSpouse
    connectedToMajor = []
    for left,right in [fromNodeLR, toNodeLR]:
        leftConnTyp = False
        rightConnTyp = False
        
        for l in left:
            y = majorLinkChecker(l, links_df)
            if y==True: 
                leftConnTyp = y 
                break
            else:
                y = minorLinkChecker(l, links_df)
                if y==True: leftConnTyp = -1
                else: leftConnTyp = 0  
        for r in right:
            y = majorLinkChecker(r, links_df)
            if y==True: 
                rightConnTyp = y 
                break
            else:
                y = minorLinkChecker(r, links_df)
                if y==True: rightConnTyp = -1
                else: rightConnTyp = 0
        condLR = [leftConnTyp, rightConnTyp]
        connectedToMajor.append(condLR)
    twoEndConnTyp = np.array(connectedToMajor)
    
    if twoEndConnTyp.sum()==4: 
        betweenMajorLinksScore = 1
    elif (twoEndConnTyp[:,0].sum()==0 and twoEndConnTyp[:,1].sum()==2) or  \
        (twoEndConnTyp[:,0].sum()==2 and twoEndConnTyp[:,1].sum()==0):
        betweenMajorLinksScore = 2
    elif ((twoEndConnTyp[:,0].sum()==-1 or twoEndConnTyp[:,0].sum()==1) and  \
                                    twoEndConnTyp[:,1].sum()==2) or  \
        (twoEndConnTyp[:,0].sum()==2 and 
            (twoEndConnTyp[:,1].sum()==-1 or twoEndConnTyp[:,1].sum()==1)):
        betweenMajorLinksScore = 2.5
    elif twoEndConnTyp[:,0].sum()==0 and twoEndConnTyp[:,1].sum()==-2 or  \
        twoEndConnTyp[:,0].sum()==-2 and twoEndConnTyp[:,1].sum()==0:
        betweenMajorLinksScore = 3
    elif ((twoEndConnTyp[:,0].sum()==-1 or twoEndConnTyp[:,0].sum()==1) and  \
                                    twoEndConnTyp[:,1].sum()==-2) or  \
        (twoEndConnTyp[:,0].sum()==-2 and 
            (twoEndConnTyp[:,1].sum()==-1 or twoEndConnTyp[:,1].sum()==1)):
        betweenMajorLinksScore = 3.5
    else:
        betweenMajorLinksScore = 0
    #betweenMajorLinksScore values 
    #    1 := major roads on both node and both right-left side
    #    2 := between two divided major roads (possibly maj-maj T-intersctn)
    #    2.5 := two divided major roads on one side, on other side one major 
    #    or minor 
    #    3 := minor roads on one side (possibly T-intersctn with minor)
    #    3.5 := two minor roads on one side, on other side one major 
    #    or minor
    
    startThru = parentOrien[1]
    endThru = offspOrien[1]
    for stt,end in [(startThru, endThru)]:
        sttConnToMajor = False
        endConnToMajor = False
        for l in stt:
            y = majorLinkChecker(l, links_df)
            if y==True: 
                sttConnToMajor = y 
                break
        for r in end:
            y = majorLinkChecker(r, links_df)
            if y==True: 
                endConnToMajor = y 
                break
    onMajorLink = sttConnToMajor and endConnToMajor
    #shortlinks either between major links or on one-way major links
    adjLinkTypeCond = 1<=betweenMajorLinksScore<=2 or  \
                        onMajorLink or majorLinkChecker(linkID, links_df)
    return adjLinkTypeCond, betweenMajorLinksScore

def sameDirectionChecker(sibOrien, leftParentOrie):
    angularDif = abs(sibOrien - leftParentOrie)
    angularDifFromNorth = min(360-angularDif,angularDif) 
    return abs(angularDifFromNorth)

def findSiblingOrSpouseLinks(linkID, links_df, nodes_df, 
                             spouseOrSibling="sibling"):
    if spouseOrSibling == 'sibling':
        fromOrTo = "from"
        succOrPred = "successor"
    if spouseOrSibling == 'spouse':
        fromOrTo = "to"
        succOrPred = "predecessor"
    fromOrTonode = links_df.at[linkID, fromOrTo+"NodeID_parade"]
    try:
        predLinksAtNode = nodes_df.at[fromOrTonode, succOrPred+  \
                                                      "Links"].split()
    except:
        predLinksAtNode = nodes_df.at[fromOrTonode, succOrPred+"Links"]
    SiblingOrSpousesLinks = [int(x) for x in predLinksAtNode if 
        int(x) != linkID]
    return SiblingOrSpousesLinks

def findRightSpouseOrSibling(links_df, offspOrParentOrien,SiblingOrSpouseLinks,
                             SiblingOrSpouse='sibling'):
    '''
    Finds the single linkID of
        * the spouse link going out to the right or 
        * the sibling link coming in making a right turn
    
    **definitions**
    Parents := predecessor links for the current link
    Offspring := successor links for the current link
    Spouse := predecessor links at the to-node for the current link
    Sibling := successor links at the from-node for the current link

    **inputs**:
    offspOrParentOrien:*list*
        list of links which are either offspring or parent links
    SiblingOrSpouseLinks: *list*
        list of links which are either siblings or spouse links
    SiblingOrSpouse:*str*, default 'sibling'
        By default finds the sibling link which makes the right turn, if 'spouse', finds spouse link
        
    **returns**
    rightSpouseOrSibling:*list*
        a list with single int link ID
    '''
    if SiblingOrSpouse == 'sibling':
        a = 'first'
        b = 'last'
    if SiblingOrSpouse == 'spouse':
        a = 'last'
        b = 'first'
    rightSpouseOrSibling = -1
    for sp in SiblingOrSpouseLinks:
        deviation = 999
        spOrSiblingOrien = links_df.at[sp, a+"Orientation(deg)"]
        for leftParOrOffsp in offspOrParentOrien[2]:
            leftOffspOrParentOrie =   \
                    links_df.at[int(leftParOrOffsp), b+"Orientation(deg)"]
            dev = sameDirectionChecker(spOrSiblingOrien, leftOffspOrParentOrie)
            if dev <= 40 and dev <= deviation:
                rightSpouseOrSibling = [int(sp)]
                deviation = dev
    if rightSpouseOrSibling == -1:
        rightSpouseOrSibling = []

    return rightSpouseOrSibling 

    
def checkNotInsignificant(rightSiblOrSpouse, rightParentOrOffspring, links_df):
    siblOrSpouseNameOK = False
    for l in rightSiblOrSpouse:
        
        if majorLinkChecker(l, links_df) or  \
                links_df.at[l, 'primaryName'] is not np.nan:
            siblOrSpouseNameOK = True
            break
    parentOrOffspNameOK = False
    for r in rightParentOrOffspring:
        if majorLinkChecker(r, links_df) or  \
                links_df.at[r, 'primaryName'] is not np.nan:
            parentOrOffspNameOK = True
            break
    return siblOrSpouseNameOK and parentOrOffspNameOK

def checkSibSpRamp(rightSiblOrSpouse, rightParentOrOffspring, links_df):
    sibSpouseRampOK = False
    for l in rightSiblOrSpouse:
        if links_df.at[l, 'ltype']==3:
            sibSpouseRampOK = True
            break
    parentOrOffspRampOK = False
    for r in rightParentOrOffspring:
        if links_df.at[r, 'ltype']==3:
            parentOrOffspRampOK = True
            break
    return sibSpouseRampOK and parentOrOffspRampOK
            

def checkSimpleIntersecShortlink(linkID, offspOrien, parentOrien, links_df, 
                                 nodes_df):
    possibleSpouses = findSiblingOrSpouseLinks(linkID, links_df, nodes_df, 
                                               spouseOrSibling='spouse')
    rightSpouse = findRightSpouseOrSibling(links_df, offspOrien, 
        possibleSpouses, SiblingOrSpouse='spouse')
    possibleSiblings = findSiblingOrSpouseLinks(linkID, links_df, 
        nodes_df, spouseOrSibling='sibling')
    rightSibling = findRightSpouseOrSibling(links_df, parentOrien, 
        possibleSiblings, SiblingOrSpouse='sibling')
    lengthCond = links_df.at[linkID, "length(feet)"] <= 100
    siblingSpouseCond = len(rightSibling) >= 1 and len(rightSpouse) >= 1
    parentOffspCond = len(offspOrien[2]) >= 1 and len(parentOrien[2]) >= 1
    adjLypeInfo = adjLinktypeChecker(linkID, offspOrien, parentOrien, 
        rightSpouse, rightSibling, links_df)
    adjLinkTypeCond = adjLypeInfo[0]
    betweenMajorLinksScore = adjLypeInfo[1]
    oneWayMajor = links_df.at[linkID, 'reverseID_parade'] == -1
    hasImpSibSpouse = siblingSpouseCond and   \
                (checkNotInsignificant(rightSibling,rightSpouse, links_df) or 
                        checkSibSpRamp(rightSibling, rightSpouse, links_df))
    hasImpParentOffspr = parentOffspCond and  \
            (checkNotInsignificant(parentOrien[2], offspOrien[2], links_df) or 
                    checkSibSpRamp(parentOrien[2], offspOrien[2], links_df))
    if 3 <= betweenMajorLinksScore <= 3.5:
        shortlinkCondition = lengthCond and adjLinkTypeCond and   \
                        (hasImpSibSpouse or hasImpParentOffspr) and oneWayMajor
    else:
        shortlinkCondition = lengthCond and adjLinkTypeCond and   \
                                    (hasImpSibSpouse or hasImpParentOffspr)
    return shortlinkCondition

def checkShortLink(linkID, links_df, nodes_df):
    '''
    Conditions for identifying intersection shortlinks
    ==================================================
    
    1. Length:
        Length of link has to be less or equal to 100 ft
    2. From End Orientation:
        Has at least one sibling link to right and at least one parent link from left direction
    3. To End Orientation:
        Has at least one spouse link from right and at least one offspring link to left direction
    4. Adjacency to major links:
        Either of the conditions below has to be true
    
    Condition 1:
    ------------
    
    * shortlink is in between major links
    * Satisfies condition a and b below
        a. has major link as left-parent and major link as right-sibling
        b. has major link as left-offspring and major link as right-spouse
    
    Condition 2: 
    ------------
    
    * shortlink is on a major link
    * Has major link as thru-parent and major link as thru offspring
    
    Condition 3: 
    ------------
    
    * Major link itself
    * shortlinks is itself a major link 
    
    
    **inputs**
    ------
    
    linkID:*int*
        linkID
    links_df:*Pandas.DataFrame*
        Original link_wkt file converted to an DataFrame
    nodes_df:*Pandas.DataFrame*
        Original node_wkt file converted to an DataFrame
    
    **outputs**
    ------
    
    shortlinkCondition:*bool*
        True if detected, False if not
    
    '''
    offspOrien = parentOffspringTurnBin(linkID,"successor", links_df)
    parentOrien = parentOffspringTurnBin(linkID,"predecessor", links_df)    
    shortlinkCondition = checkSimpleIntersecShortlink(linkID, offspOrien, 
                                            parentOrien, links_df, nodes_df)
    #for links at intersections with left turn lane, shortlinks may not have 
    #leftParent (restricted). So update parent list and check
    if shortlinkCondition != True:
        try:
            restrParent = links_df.at[linkID, 'restrictedPredecessors'].split()
            restPar = [int(i) for i in restrParent] 
            if len(restPar)==1:
                rstAng=links_df.at[linkID, 'restrictedPredecessorAngles']
                rstAngleLeft = abs( 90 - float(rstAng) ) <= 15
                rstMajRestLeft = majorLinkChecker(restPar[0], links_df)
                if rstAngleLeft and rstMajRestLeft:
                    parentOrien[2] += restPar
            shortlinkCondition = checkSimpleIntersecShortlink(linkID, 
                                offspOrien, parentOrien, links_df, nodes_df)
        except:
            pass
    return shortlinkCondition


def findThruSiblingOrSpouse(linkID, links_df, parentOrOffspring, 
                            siblingOrSpouse='sibling'):
    if siblingOrSpouse=='sibling':
        thruLinksInclCurrent =parentOffspringTurnBin(parentOrOffspring,
                                                'successor', links_df)[1]
    if siblingOrSpouse=='spouse':
        thruLinksInclCurrent = parentOffspringTurnBin(parentOrOffspring, 
                                                'predecessor', links_df)[1]
    thruOnesExceptCurrent = [i for i in thruLinksInclCurrent if i != linkID]
    if (len(thruOnesExceptCurrent)==1) and (thruOnesExceptCurrent[0]!=linkID):
        thruSiblingOrSpouse = thruOnesExceptCurrent[0]
        return thruSiblingOrSpouse
    else:
        return None

        
if __name__ == '__main__':
    city = 'Tucson'
    fldr = os.path.join("/media/asifrehan/shared_data_folder",
                            "Metropia_docs/{}_WKT".format(city))
    links_df = pd.read_csv(fldr+"/links_wkt.csv")
    nodes_df = pd.read_csv(fldr+"/nodes_wkt.csv")
    appendToFile = fldr + "/links_wkt.csv"
    newWriteToFile = fldr+"/checkShortlink{}3.1.5.txt".format(city)
    #appendToFile = fldr+"/checkShortlink2.3.txt"
    columnName = "shortlinkCheckWithLType"
    #main(newWriteToFile, columnName, appendToFile, links_df, nodes_df)
    #print checkShortLink(13240, links_df, nodes_df)
    #print checkShortLink(23928, links_df, nodes_df)

    #Tucson
    #==========================================================================
    for i in [20401, 19555, 290, 5721, 7927, 15845, 282, 27046,7545, 4270, 17729,5177, 10517, 22780, 21299, 20629]:
    #   #290, 7927, 15845 == true 
        #22780==true, 21299==false 20629==true
        print i, checkShortLink(i, links_df, nodes_df)     
    #==========================================================================
    #Austin
    #==========================================================================
    # for i in [1221]:
    #     #1221==True
    #     print i, checkShortLink(i, links_df, nodes_df)
    #==========================================================================