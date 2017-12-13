import dbf
import csv
import time
from itertools import groupby, izip
import math
import sys


def read_sys_args(args):
    try:
        folder_path = args[1]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be a path to folder')
    if folder_path[-1] != '/':
        folder_path += '/'
    return folder_path


def read_network_mapping(objfile):
    # {(von,nach):id, (von2.nach2):id2,...}
    network = {}
    table = dbf.Table(objfile)
    records  = table.open()
    for record in records:
        network[int(float(record['von'])), int(float(record['nach']))] = int(float(record['id']))
    table.close()
    return network

def read_link_csv(objfile):
    #    [(63376, 1), (256180, 1), (53294, 4), (93343, 4)]
    #
    links  = []
    for each in csv.DictReader(objfile):
        links += [(int(float(each['VON(f0)'])), int(float(each['NACH(f0)'])))]
    return links

def read_node_csv(objfile):
    # {1: (33.27093, -111.77359)}
    nodes = {}
    new2orig = {}   # mapping from new id to original id
    for each in csv.DictReader(objfile):
        nodes[int(float(each['#NEW_ID(f0)']))] = (float(each['X_COORD(f0)'])/1000000, float(each['Y_COORD(f0)'])/1000000)
        new2orig[int(each['NODE_ID(f0)'])] = int(float(each['#NEW_ID(f0)']))
    return nodes, new2orig

def read_restrict(objfile):
    # {(41076661, 30372, 852003796): 1, (102009838, 142321, 102009837): 1, (85442839, 153124, 85442847): 1}
    restricts = {}
    for each in objfile:
        restrict = map(lambda x: int(x), each.strip('\n').split(','))
        restricts[(restrict[0], restrict[1], restrict[2])] = restrict[-1]
    return restricts

def read_features(objfile):
    # {(fromnode, to node): [y1,x1,y2,x2,...], (fromnode, tonode): [y1,x1,y2.x2...],...}  !!!! Be careful y infront of x !!!!
    #  {(392175, 410376): [-111.989592, 33.33358, -111.989584, 33.33371, -111.989232, 33.334],
    #   (410376, 392175): [-111.989232, 33.334, -111.989584, 33.33371, -111.989592, 33.33358], ...}
    # here link id represented by new id system  10032013

    features = {}
    objfile.readline()
    objfile.readline()      # read the first two lines
#    for each in objfile:
#        list_all += [each.strip('\n').split(',')]
#    lk, index, content = zip(*list_all)
#
#    lk=map(lambda x: int(x),lk)
#    content = map(lambda x: float(x),  content)
#
#    for key, group in groupby(list_all, lambda x: x[0]):
#        value = []
#        for each in group:
#            value += [float(each[2])]
#        features[(int(value[0]), int(value[1]))]= map(lambda x: x/1e+6, value[3:])
    for each in objfile:
        each = each.strip('\n').split(',')
        record = [float(i) for i in each if i]
        features[(int(record[0]), int(record[1]))] = map(lambda x: x/1e+6, record[3:])
    return features


def _read_files(f):      # take 1 min to feed in all inputs
    return (read_network_mapping(f+'Strassen.dbf'),
    read_link_csv(open(f+'network - link.csv')),
    read_node_csv(open(f+'network - node.csv')),
    read_restrict(open(f+'Abbieger.csv')),
    read_features(open(f+'LinkXY.csv')))

def inbound_outbound(links):
    '''
    >>> links = [[63376, 1], [256180, 1], [53294, 4], [93343, 4],[53294, 100]]
    >>> inbound_outbound(links)
    {63376: (1,), 256180: (1,), 53294: (4, 100), 93343: (4,)}
    '''
    outbound = {}
    for start, group in groupby(sorted(links), lambda x:x[0]):
        keys, values = izip(*group)
        outbound[start] = values
    return outbound


def angle_calcu(a_point_x, b_point_x, c_point_x, a_point_y, b_point_y, c_point_y):
    #compute angle
    # cos(Theta) = vector_ab . vector_bc/(mod_ab*mod_bc)
    # SINind = vector_ab X vector_bc  used to determine is anti-clockwise or clockwise angle
    # the angle standard direction is from_link's direction, angle goes with counterclockwise direciton [0,360]

   #another option
    # calcuate the angle from v1 to v2 in 2d coordinate system
    v1_y = float(b_point_y)- float(a_point_y)
    v1_x = float(b_point_x)- float(a_point_x)
    v2_y = float(c_point_y)- float(b_point_y)
    v2_x = float(c_point_x)-float(b_point_x)
# 1. calculate the angle from +x to v1
    angle1 = math.atan2(v1_y, v1_x)*180.0/math.pi;
# 2. calculate the angle from +x to v2
    angle2 = math.atan2(v2_y, v2_x)*180.0/math.pi;
# 3. calcualte the angle from v1 to v2
    angle = angle2 - angle1;
    if angle < 0:
        angle = 360+angle
    return int(angle)

def generate_turns_restrict_angle(network, links, nodes, new2orig, restricts, features):

    outbound = inbound_outbound(links)
    turns = []
    features_origianl = {}
    for each in features:
        features_origianl[new2orig[each[0]], new2orig[each[1]]] = features[each]
    features = features_origianl

    for each in links:
        for item in outbound.get(each[1], []):
                fromlink = each
                tolink = (fromlink[1], item)
                if network.has_key(fromlink) and network.has_key(tolink):
                    restrict = restricts.get((network[fromlink], fromlink[1], network[tolink]), 0)
                elif network.has_key(fromlink) and not network.has_key(tolink):
                    restrict = restricts.get((network[fromlink], fromlink[1], network.get((item, fromlink[1]), 0)), 0)
                elif not network.has_key(fromlink) and network.has_key(tolink):
                    restrict = restricts.get((network.get((fromlink[1], fromlink[0]), 0), fromlink[1], network[tolink]), 0)
                elif not network.has_key(fromlink) and not network.has_key(tolink):
                    restrict = restricts.get((network.get((fromlink[1], fromlink[0]), 0), fromlink[1], network.get((item, fromlink[1]), 0)), 0)
                else:
                    print 'error!- invalid links'

                if not features.has_key(fromlink) and not features.has_key(tolink):
                    a_point_x = nodes[fromlink[0]][0]
                    b_point_x = nodes[fromlink[1]][0]
                    c_point_x = nodes[tolink[1]][0]
                    a_point_y = nodes[fromlink[0]][1]
                    b_point_y = nodes[fromlink[1]][1]
                    c_point_y = nodes[tolink[1]][1]
                elif features.has_key(fromlink) and not features.has_key(tolink):
                    a_point_x = features[fromlink][-2]
                    b_point_x = nodes[fromlink[1]][0]
                    c_point_x = nodes[tolink[1]][0]
                    a_point_y = features[fromlink][-1]
                    b_point_y = nodes[fromlink[1]][1]
                    c_point_y = nodes[tolink[1]][1]
                elif not features.has_key(fromlink) and features.has_key(tolink):
                    a_point_x = nodes[fromlink[0]][0]
                    b_point_x = nodes[fromlink[1]][0]
                    c_point_x = features[tolink][0]
                    a_point_y = nodes[fromlink[0]][1]
                    b_point_y = nodes[fromlink[1]][1]
                    c_point_y = features[tolink][1]
                else:
                    a_point_x = features[fromlink][-2]
                    b_point_x = nodes[fromlink[1]][0]
                    c_point_x = features[tolink][0]
                    a_point_y = features[fromlink][-1]
                    b_point_y = nodes[fromlink[1]][1]
                    c_point_y = features[tolink][1]
                turns += [[fromlink[0], fromlink[1], item, restrict, angle_calcu(a_point_x, b_point_x, c_point_x, a_point_y, b_point_y, c_point_y)]]
    return turns


def main():
    folder = read_sys_args(sys.argv)

    t = time.time()
    network, links, (nodes, new2orig), restricts, features = _read_files(folder)
    turns = generate_turns_restrict_angle(network, links, nodes, new2orig, restricts, features)
    print 'start save!...'
################
#    wr = open('nn_angle.json', 'wb')
#    json.dump(turns, wr)
#    wr.flush()
#    wr.close()
##################
    wr_csv = open(folder + 'nn_angle.csv', 'wb')
    w = csv.writer(wr_csv)
    w.writerow(['A_Node', 'B_Node', 'C_Node', 'restrict', 'angle'])
    for each in turns:
        w.writerow(each)
        wr_csv.flush()
    wr_csv.close()
#####################
# product origial linkxy file
    wr_features = open(folder + '#linkxy_orig.csv', 'wb')
    w = csv.writer(wr_features)
    for each in features:
        w.writerow([new2orig[each[0]],new2orig[each[1]], len(features[each])/2] + features[each])
        wr_features.flush()
    wr_features.close()

    print 'elapse time is: ', time.time() - t   #takes about 4369.7sec = 72 mins = 1.2 hr, too long time to run.
    print 'done'



if __name__=='__main__':
    import doctest
    doctest.testmod()
    main()
