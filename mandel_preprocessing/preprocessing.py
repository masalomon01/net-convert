import csv
import json
import os
import sys
import time
from collections import defaultdict
from copy import deepcopy
from operator import itemgetter

from geometry_calculations import calc_angle
from mutual_turns import find_mutuals
from numpy import array, save
from read_data import read_signal_locations, read_intersection_links, read_restrictions


def read_sys_args(args):
    try:
        folder_path = args[1]
        city_name = args[2]
    except IndexError:
        raise IndexError('Incorrect inputs.  Arg1 should be a path to folder and arg2 should be city name')
    return folder_path, city_name


def read_wkt(infile):
    reader = csv.DictReader(open(infile, 'rb'))
    for row in reader:
        parade_id = int(row['LinkID_parade'])
        gid = int(row['LinkID_ptv'])
        successors = [int(x) for x in row['successors'].split(" ")[:-1]]  # wkt has a space at end of successor field
        links_successors[parade_id] = successors
        predecessors = [int(x) for x in row['predecessors'].split(" ")[:-1]]
        links_predecessors[parade_id] = predecessors
        gid_to_parade[gid] = parade_id
        parade_to_gid[parade_id] = gid
        geom = parse_wkt(row['WKT'])
        link_geom[parade_id] = geom
        ltype = int(row['ltype'])
        link_ltype[parade_id] = int(ltype)
        link_nodes[parade_id] = (int(row['fromNodeID_parade']), int(row['toNodeID_parade']))
        nodes_to_link[(int(row['fromNodeID_parade']), int(row['toNodeID_parade']))] = parade_id

        category = int(row['category'])
        if category <= 5:
            time_depen_links.add(parade_id)
        lanes_in_wkt_order.append(int(row['numLanes']))


def parse_wkt(wkt):
    stripped = wkt[12:-1]
    points = stripped.split(",")
    point_list = []
    for p in points:
        longlat = p.split(" ")
        if longlat[0] == '':
            longlat = longlat[1:]
        lon = float(longlat[0])
        lat = float(longlat[1])
        formatted_point = (lat, lon)
        point_list.append(formatted_point)
    return point_list


def type_from_pair(pair, mega=None):
    angle = calc_angle(pair[0], pair[1], link_geom)
    connected = is_connected(pair)
    # TODO: need to consider more factor than just angle
    turn_type = type_from_angle(angle, connected)

    # check if it's texas u
    if turn_type == 3 and mega is not None:
        for parade_link in mega:
            if parade_link in texas_u_links:
                turn_type = 5

    """
    # u-turn detection
    from_geom = link_geom[pair[0]]
    to_geom = link_geom[pair[1]]
    start_to_mid_dist = dist_from_to(from_geom[0][0], from_geom[0][1], from_geom[-1][0], from_geom[-1][1])
    start_to_end_dist = dist_from_to(from_geom[0][0], from_geom[0][1], to_geom[-1][0], to_geom[-1][1])
    if start_to_end_dist / start_to_mid_dist < 0.2:
        print "turn_type should be 3"
    """

    return turn_type


def type_from_angle(angle, connected):
    turn_type = None
    if -180 <= angle < -170:
        turn_type = 3
    elif -170 <= angle < -40:
        turn_type = 1
    elif -40 <= angle < 40:
        turn_type = 4
    elif 40 <= angle < 150:
        turn_type = 2
    elif 150 <= angle <= 180:
        turn_type = 3
    if turn_type is None:
        print 'WARNING: angle out of bounds'
    # allowing u turn threshold to be bigger when passing through intersection
    # this is to account for case below where maneuver starts at bottom right, passes through dotted intersection line
    # and ends on the link angled slightly to the right in bottom left
    #       |   |
    #       |   |
    #    -------------
    #       \   |
    #        |  |
    #        |  |
    # comparatively this case where user starts on bottom vertical link and continues to the \ isn't a u turn
    #         |
    #         |\
    #         | \
    #         |  \
    #
    if (not connected) and (-180 <= angle <= -150):
        turn_type = 3
    return turn_type


def is_connected(link_pair):
    # return true if the two links are directly connected, i.e. no intersection links
    link1 = link_pair[0]
    link2 = link_pair[1]
    return link2 in links_successors[link1]


def links_is_restricted(pair):
    # just throwing this in a function so code is more readable elsewhere
    if pair in restrictions:  # IDs in the restrictions object have already been converted to parade IDs
        return True
    else:
        return False


def node_sequence_to_links(node_sequence):
    link_seq = []
    iterator = iter(node_sequence)
    first = next(iterator)
    for each in iterator:
        link_seq.append(nodes_to_link[(first, each)])
        first = each
    return link_seq


# TODO: qaqc this function
def nodes_is_restricted(node_seq1, node_seq2):
    # convert the nodes to links, then check if any link combo is restricted
    link_seq1 = node_sequence_to_links(node_seq1)
    link_seq2 = node_sequence_to_links(node_seq2)

    is_restricted = False
    for link1 in link_seq1:
        for link2 in link_seq2:
            if (link1, link2) in restrictions:
                is_restricted = True
                return is_restricted

    return is_restricted


# TODO: read type codes from config file for easier future editing
def calc_signal_type(links):
    # currently we only have traffic signals mapped
    intersection_codes = {'traffic_signal': 1,
                          'stop_sign': 2,
                          'yield': 3,
                          'pedestrian_crossing': 4}
    signal_code = 0  # default code when there is no traffic light, stop sign, etc

    # we only care about a signal after the start and before the end of the turn pair
    # links are tagged as signalized if there is a signal at the end of them
    # so if end link is signalized, it is actually referring to a different intersection and we should ignore it
    for each in links[:-1]:
        try:
            signal_type = signalized_links[each]
            signal_code = intersection_codes[signal_type]
        except KeyError:  # occurs whenever the link is not signalized (99% of cases)
            pass

    return signal_code


def iterate(mega_set, pair_set):
    set2 = set()
    for each in mega_set:
        if each[-1] in intersection_links:
            new_succs = [x for x in links_successors[each[-1]] if
                         link_geom[x][::-1] != link_geom[each[-1]] and x not in each]
            for succ in new_succs:
                temp = list(each)
                temp.append(succ)
                temp = tuple(temp)
                if (temp[0], temp[-1]) not in pair_set and not links_is_restricted((temp[0], temp[-1])):
                    set2.add(temp)
        # this mega link is good if it hasn't already been added
        elif (each[0], each[-1]) not in pair_set:
            pair_set.add((each[0], each[-1]))
            mega_links.append(each)
    return set2


def generate_mega_links():
    iteration1 = set()
    pairs = set()
    # TODO this leads to links which have 0 successors never being added if it has no successors
    for link, successors in links_successors.items():
        if link in intersection_links:
            continue
        for succ in successors:
            mega = (link, succ)
            iteration1.add(mega)
    iteration2 = iterate(iteration1, pairs)  # there should never be a case with 4 intersection links in a row
    iteration3 = iterate(iteration2, pairs)
    iteration4 = iterate(iteration3, pairs)
    iteration5 = iterate(iteration4, pairs)
    # anything left in iteration 5 that isnt a roundabout will be a bug so delete them then iterate again
    temp = set()
    for mega in iteration5:
        all_roundabout = True
        for link in mega[1:1]:  # skip first element because we know it is not an intersection link
            if link not in roundabout_links:
                print 'WARNING: {} is not being included as a mega link due to link {} '.format(mega, link)
                all_roundabout = False
        if all_roundabout:
            temp.add(mega)

    iteration6 = iterate(temp, pairs)
    iteration7 = iterate(iteration6, pairs)
    iteration8 = iterate(iteration7, pairs)
    # anything left in iteration8 is likely a bug


def prepare_mega_for_output():
    """
    this function will take the previously created mega links and format them, then output them to outfile3
    """
    formatted = set()
    for each in mega_links:
        first_element = (each[0],)
        rest_of_ele = tuple(list(each)[1:])
        formatted.add(first_element)
        formatted.add(rest_of_ele)

    temp = []
    for each in formatted:
        nodes = []
        for i, item in enumerate(each):
            nds = link_nodes[item]
            if i == 0:
                nodes.append(nds[0])
                nodes.append(nds[1])
            else:
                nodes.append(nds[1])
        while len(nodes) < 8:
            nodes.append(-1)
        temp.append(nodes)
    sorted_output = sorted(temp, key=itemgetter(0, 1, 2, 3, 4, 5, 6, 7))

    # remove the -1s for the new format
    sorted_output2 = []
    for each in sorted_output:
        cleaned = [x for x in each if x != -1]
        sorted_output2.append(cleaned)

    mega_link_nodes = {}  # id : node list
    mega_start = defaultdict(list)
    mega_id = 0
    for node_sequence in sorted_output2:
        if node_sequence[0] == node_sequence[-1]:
            print 'WARNING: Mega link with node sequence {} has same from/to node'.format(node_sequence)

        mega_link_nodes[mega_id] = node_sequence
        mega_start[node_sequence[0]].append(mega_id)
        mega_id += 1

    mega_rows_to_write = []
    for mega_id, node_sequence in mega_link_nodes.items():
        to_write = [mega_id]
        # format node sequence the way parade likes it
        node_seq_string = ''
        for item in node_sequence:
            node_seq_string += str(item) + ' '
        node_seq_string = node_seq_string[:-1]
        to_write.append(node_seq_string)
        # now get successors - all mega links that start where previous link ends
        last_node = node_sequence[-1]
        successors = mega_start[last_node]
        # check to make sure this successor is not restricted
        successor_string = ''
        restricted_successors = ''
        for each in successors:
            if nodes_is_restricted(node_sequence, mega_link_nodes[each]):
                restricted_successors += str(each) + ' '
            else:
                successor_string += str(each) + ' '
        successor_string = successor_string[:-1]  # just removing the space added to the end in previous loop
        restricted_successors = restricted_successors[:-1]
        to_write.append(successor_string)
        to_write.append(restricted_successors)
        # now need to get the ltype of the mega link
        mega_ltype = determine_mega_ltype(node_sequence)
        to_write.append(mega_ltype)
        mega_rows_to_write.append(to_write)

    return mega_rows_to_write


def determine_mega_ltype(node_seq):
    # start by getting each ltype present in the mega link
    possible_ltypes = set()
    iterator = iter(node_seq)
    first_nd = next(iterator)
    for each in iterator:
        second_nd = each
        link_id = nodes_to_link[(first_nd, second_nd)]
        ltype = link_ltype[link_id]
        possible_ltypes.add(ltype)

        first_nd = second_nd

    # now use ranked ltypes and once one is found in possible_ltypes() break and that ltype is assigned to whole mega
    # since these ltypes are read from wkt file, normally only 1 3 5 7 11 are possible
    ranked_ltypes = [1, 7, 5, 3, 11]
    for each in ranked_ltypes:
        if each in possible_ltypes:
            return each

    # this exception only thrown if the ltype is not in ranked_ltypes
    if 9 in possible_ltypes:  # temp patch for buggy 10-18 el paso network version
        return 11
    if 4 in possible_ltypes:
        return 5
    raise ValueError('INVALID LTYPE {} at node sequence {}'.format(possible_ltypes, node_seq))


def is_bidirectional(link):
    # link is bidirectional if it has a successor with exactly the opposite geometry
    successors = links_successors[link]
    for each in successors:
        if link_geom[each][::-1] == link_geom[link]:
            return True
    return False


class ManeuverAnalyzer:
    """
    responsible for analyzing the type of a maneuver
    if a maneuver matches any of the following patterns, it will not be added to turn pairs
    """

    def __init__(self, mega, turn_type):
        self.mega = mega
        self.turn_type = turn_type
        self.link1 = self.mega[0]
        self.link2 = self.mega[-1]
        # format: dictionary, key: parade_id, value: turn_type
        self.other_successors = self.__calc_other_successors()
        self.other_predecessors = self.__calc_other_predecessors()

    def __calc_other_successors(self):
        # calculate successors of pair[0] that:
        # 1. is not pair[1]
        # 2. is not reverse of pair[0]
        # 3. is not a u-turn from pair[0]
        successors = deepcopy(links_successors[self.link1])
        already_iterated = set()
        other_successors = {}
        for successor in successors:
            successor_turn_type = type_from_pair((self.link1, successor), self.mega)
            if successor in intersection_links and successor not in already_iterated:
                successors += links_successors[successor]
            elif successor not in intersection_links and successor_turn_type != 3 and successor_turn_type != 5 \
                    and successor != self.link2 and link_geom[successor][::-1] != link_geom[self.link1]:
                other_successors[successor] = successor_turn_type
            already_iterated.add(successor)
        return other_successors

    def __calc_other_predecessors(self):
        # calculate predecessors of pair[1] that:
        # 1. is not pair[0]
        # 2. is not a reverse of pair [1]
        # 3. is not a turn to pair[1]
        predecessors = deepcopy(links_predecessors[self.link2])
        already_iterated = set()
        other_predecessors = {}
        for predecessor in predecessors:
            predecessor_turn_type = type_from_pair((predecessor, self.link2), self.mega)
            if predecessor in intersection_links and predecessor not in already_iterated:
                predecessors += links_predecessors[predecessor]
            elif predecessor not in intersection_links and predecessor_turn_type != 3 and predecessor_turn_type != 5 \
                    and predecessor != self.link1 and link_geom[predecessor][::-1] != link_geom[self.link2]:
                other_predecessors[predecessor] = predecessor_turn_type
            already_iterated.add(predecessor)
        return other_predecessors

    def is_all_others_minor(self):
        # check if all other successors are minor
        all_others_minor = False
        # TODO: need to check for major through minor links
        # TODO: check this all other minor detection when major road with separation between links goes through minor
        if self.turn_type == 4 and link_ltype[self.link1] != 11 and link_ltype[self.link2] != 11 \
                and len(self.other_successors) > 0:
            all_others_minor = True
            for parade_id, turn_type in self.other_successors.iteritems():
                # if not reverse link or u turn and not l-type 11 then not all successors are minor
                if link_ltype[parade_id] != 11 and turn_type != 3 and turn_type != 5:
                    all_others_minor = False
        return all_others_minor

    def is_only_one_outbound(self):
        # if there are 2 outbound links, but one is the reverse link, then we still treat it as one outbound
        # if only one outbound, check if another link is merging into it as well
        if len(self.other_successors) > 0:
            return False
        if len(self.other_predecessors) > 0:
            # this indicates that we have another incoming link that is not pair[0] or a reverse link
            # in this case it is likely the other link will cause a delay so this should be a turn pair
            return False
        return True

    def is_fork(self):
        # first check if they are connected.  if two links aren't connected, they are not a fork
        if self.link2 not in links_successors[self.link1]:
            return False
        # it is a fork if there are 2 or 3 outbound successors that only have link1 as a predecessor
        # the outbound angles can be no more than 60 degrees
        successors = links_successors[self.link1]
        if len(successors) < 2 or len(successors) > 3:
            return False
        for successor in successors:
            # should only be one link preceding the successors
            if len(links_predecessors[successor]) != 1:
                return False
            # angle should be no more than 60 degrees
            angle = calc_angle(self.link1, successor, link_geom)
            if abs(angle) > 60:
                return False
        return True

    # TODO: we might want to use this logic to add turn restrictions at these locations
    def is_through_turn_bay(self):
        # should be straight
        if self.turn_type != 4:
            return False
        # TODO: test to justify if we should remove this condition
        # link2 is bidirectional
        if not is_bidirectional(self.link2):  # fork handling already takes care of this when links are oneway
            return False
        # must be connected
        successors = [x for x in links_successors[self.link1] if link_geom[x][::-1] != link_geom[self.link1]]
        if self.link2 not in successors:  # connected
            return False
        # only 2 or 3 total successors of link1 excluding reverse link
        if len(successors) < 2 or len(successors) > 3:
            return False
        # the other successors must be intersection links
        # successors of link1 that are not link2 or the reverse of 1
        other_successors = [x for x in successors if x != self.link2]
        for each in other_successors:
            if each not in intersection_links:  # other successors must be one-way intersection links
                return False
            if is_bidirectional(each):
                return False
        return True

    def is_merge(self):
        # must be a through movement
        if self.turn_type != 4:
            return False
        # should have only one outbound
        if len(self.other_successors) != 0:
            return False
        # should have at least 1 other predecessor
        if len(self.other_predecessors) < 1:
            return False
        # TODO: consider if we should include angle as a condition
        return True

    def is_through_t_intersection(self):
        # there are 3 types of T intersection, #1 is handled in merge, only #2 & #3 will be considered here
        #  #1 ^     #2 ^     #3 ^
        #     |        |        |
        #     ^<---    ^--->    ^<-->
        #     |        |        |
        #     |        |        |

        # must be a through movement
        if self.turn_type != 4:
            return False
        # first link must have exactly 1 another 'left or right' outbound
        other_left_right = {}
        for other_succ, turn_type in self.other_successors.iteritems():
            if turn_type == 1 or turn_type == 2:
                other_left_right[other_succ] = turn_type
        if len(other_left_right) != 1:
            return False
        # end link must have either 0 or 1 other predecessor
        if len(self.other_predecessors) > 1:
            return False
        # if there's 1 other predecessor, turing from other_pred to other_succ must not be through
        #     ^                            ^
        #     |                            |
        #     |<--- other_pred   vs.   --->|--->
        #     ^---> other_succ             ^
        #     |                            |
        #     |                            |
        elif len(self.other_predecessors) == 1:
            pair = (self.other_predecessors.keys()[0], other_left_right.keys()[0])
            pred_to_succ_turn_type = type_from_pair(pair)
            if pred_to_succ_turn_type == 4:
                return False
        return True

    def is_all_through(self):
        if self.turn_type != 4:
            return False
        for turn_type in self.other_successors.itervalues():
            if turn_type != 4:
                return False
        return True


def calc_turn_type():
    link_pairs_type = {}  # (turn_pair) : type

    for mega in mega_links:
        signal_type = calc_signal_type(mega)
        pair = (mega[0], mega[-1])
        turn_type = type_from_pair(pair, mega)
        analyzer = ManeuverAnalyzer(mega, turn_type)

        # check if all other successors are minor
        all_others_minor = analyzer.is_all_others_minor()

        # check if there is only one outbound link
        only_one_outbound = analyzer.is_only_one_outbound()

        # check if it is a fork
        fork = analyzer.is_fork()

        # check turn bay
        turn_bay_intersection = analyzer.is_through_turn_bay()

        # check merge
        merge = analyzer.is_merge()

        # check if it is going "through" a T-intersection
        through_t = analyzer.is_through_t_intersection()

        # check if all options are through
        all_through = analyzer.is_all_through()

        # if matches any of patterns above, consider not to add to turn pairs
        to_ignore = all_others_minor or only_one_outbound or fork or turn_bay_intersection \
                    or merge or through_t or all_through

        if signal_type != 1 and signal_type != 2 and to_ignore:
            pass
        else:
            link_pairs_type[pair] = turn_type
            pair_signal_type[pair] = signal_type

    return link_pairs_type


def potential_conf_links(link_pair):
    """
    Potential conflicting links include all predecessors to the to_link
    Exclude the from_link from being returned here
    If a predecessor is an intersection link, then use its predecessors
    """
    from_link = link_pair[0]
    to_link = link_pair[1]
    initial_predecessors = links_predecessors[to_link]
    already_iterated = set()
    predecessors = []
    for link in initial_predecessors:
        if link in intersection_links and link not in already_iterated:
            initial_predecessors += links_predecessors[link]
        # if it isn't an intersection link, it's not the start of the turn pair
        #  and it isn't the reverse link of the to_link
        elif link not in intersection_links and link != from_link:
            predecessors.append(link)
        already_iterated.add(link)
    return predecessors


def crosses_major(other_inbound):
    # return true if one of the other inbound links is not ltype 11
    for link in other_inbound:
        if link_ltype[link] != 11:
            return True
    return False


def select_conflict(link, predecessors, desired_turn_type):
    # this may struggle at unusual intersections where multiple inbound links have the same turn type
    for pred in predecessors:
        if type_from_pair((pred, link)) == desired_turn_type:
            return pred
    return None


def create_maneuver_ids():
    td = []
    nontd = []
    for pair in maneuver_types:
        # should probs change this to be a little more clear but I am just grabbing the constant value of the pair
        constant = conflicts[(pair[0], pair[-1])][2]
        if constant is None:
            td.append(pair)
        else:
            nontd.append(pair)
    count = 0
    for each in td:
        maneuver_ids[each] = count
        count += 1
    for each in nontd:
        maneuver_ids[each] = count
        count += 1


def conflicting_links():
    # logic for this came from asif's code
    # TODO: document how ltype interaction leads to different conflicts
    # TODO: should probably have this stuff (at least constants) in config file for easier changes in future
    conflicting_link_pairs = {}
    for pair, t in maneuver_types.items():
        inbound_links = potential_conf_links(pair)
        from_link = pair[0]
        to_link = pair[1]
        ltype1 = link_ltype[from_link]
        ltype2 = link_ltype[to_link]
        conflicting_x = None
        conflicting_y = None
        constant = None

        # use case 1: Both minor streets
        if ltype1 == ltype2 == 11:
            if crosses_major(inbound_links):
                conflicting_x = select_conflict(to_link, inbound_links, 2)
                conflicting_y = select_conflict(to_link, inbound_links, 1)
            else:
                if t == 1:
                    constant = 4
                elif t == 2:
                    constant = 4
                elif t == 3:
                    constant = 10
                elif t == 4:
                    constant = 2

        # use case 2 : Major to Major
        elif ltype1 != 11 and ltype2 != 11:
            # for major to major conflictingX always = from_link
            conflicting_x = from_link
            if t == 1 or t == 3:  # right turn or u turn have same conflicting link logic for major to major
                # conflictingY = straight into to_link
                conflicting_y = select_conflict(to_link, inbound_links, 4)
            elif t == 2:  # left turn
                # conflictingY = straight into to_link
                conflicting_y = select_conflict(to_link, inbound_links, 1)
            elif t == 4:  # straight
                # no conflictingY for straight maneuver
                pass

        # use case 3 : Major to Minor
        elif ltype1 != 11 and ltype2 == 11:
            if t == 1:  # right turn
                constant = 3
            elif t == 2:  # left turn
                conflicting_x = select_conflict(to_link, inbound_links, 1)
            elif t == 3:  # u turn
                conflicting_x = select_conflict(to_link, inbound_links, 4)
            elif t == 4:  # straight
                pass

        # use case 4 : Minor to Major
        elif ltype1 == 11 and ltype2 != 11:
            conflicting_x = select_conflict(to_link, inbound_links, 4)
            if t == 1:  # right turn
                pass
            elif t == 2 or t == 3:  # left turn and u turn have same conflicts for minor to major
                conflicting_y = select_conflict(to_link, inbound_links, 3)
            elif t == 4:  # straight
                pass
        conflicting_link_pairs[pair] = [conflicting_x, conflicting_y, constant]

    return conflicting_link_pairs


def write_subpaths(td_file, nontd_file):
    """
    Return number of time dependent maneuvers
    """
    time_depen_writer = csv.writer(open(td_file, 'wb'))
    nontd_writer = csv.writer(open(nontd_file, 'wb'))
    headers = ['manID', 'fromNodeID_trace', 'node0', 'node1', 'node2', 'node3', 'node4']
    time_depen_writer.writerow(headers)
    nontd_writer.writerow(headers)
    td_to_write = []
    nontd_to_write = []
    for each in mega_links:
        # convert to nodes and get maneuver ID
        try:
            man_id = maneuver_ids[(each[0], each[-1])]
        except KeyError:
            # if there is no maneuver ID then we previously decided that there will be no delay here
            # since there is no delay it does not need to be in the subpath file
            continue

        node_sequence = []
        for i, item in enumerate(each):
            nodes = link_nodes[item]
            if i == 0:  # this is just to make sure we arent adding the same node multiple times
                node_sequence.append(nodes[0])
                node_sequence.append(nodes[1])
            else:
                node_sequence.append(nodes[1])
        while len(node_sequence) < 6:
            node_sequence.append(-1)
        # need to determine if it is time dependent
        # should probs change this to be a little more clear but I am just grabbing the constant value of the pair
        constant = conflicts[(each[0], each[-1])][2]
        if constant is None:
            # time dependent links will not have a constant delay
            td_to_write.append([man_id] + node_sequence)
        else:
            nontd_to_write.append([man_id] + node_sequence)

    td_to_write = sorted(td_to_write, key=itemgetter(0))
    nontd_to_write = sorted(nontd_to_write, key=itemgetter(0))
    for each in td_to_write:
        time_depen_writer.writerow(each)
    for each in nontd_to_write:
        nontd_writer.writerow(each)

    return len(td_to_write)


def output(turn_pair_file, turn_pair_gid_file, maneuver_size_file, mega_file):
    # next chunk of code just gets all the turn pairs, their associated maneuver ID, then sorts them in order of manID
    temp1 = []
    temp2 = []
    for pair, man_type in maneuver_types.items():
        from_link = pair[0]
        to_link = pair[1]
        t = [maneuver_ids[pair], from_link, to_link, man_type, link_ltype[from_link], link_ltype[to_link]] \
            + conflicts[pair] + [pair_signal_type[pair]]
        t2 = [maneuver_ids[pair], parade_to_gid[from_link], parade_to_gid[to_link]]
        temp1.append(t)
        temp2.append(t2)
    ordered1 = sorted(temp1, key=itemgetter(0))
    ordered2 = sorted(temp2, key=itemgetter(0))

    with open(turn_pair_file, 'wb') as out:
        writer = csv.writer(out)
        writer.writerow(['manID', 'from_link', 'to_link', 'turn_type', 'from_ltype', 'to_ltype', 'conflictingX',
                         'conflictingY', 'constant', 'signal_type'])
        for item in ordered1:
            writer.writerow(item)

    with open(turn_pair_gid_file, 'wb') as out:
        writer = csv.writer(out)
        for item in ordered2:
            writer.writerow(item)

    # now create td_maneuver_size.json
    size = {'num_of_td_maneuvers': num_td_maneuvers}
    with open(maneuver_size_file, 'wb') as out:
        json.dump(size, out)

    # write numpy lane file
    lanes = array(lanes_in_wkt_order)
    save(num_lane_file, lanes)

    # write mega links
    with open(mega_file, 'wb') as out:
        writer = csv.writer(out)
        writer.writerow(['megaLinkId', 'nodes', 'successors', 'restrictedSuccessors', 'lType'])
        for row in mega_links_to_output:
            writer.writerow(row)


if __name__ == '__main__':
    # TODO: save warnings to a log file instead of printing
    # TODO: read database credentials from a config file
    start_time = time.time()
    # declare a bunch of variables that will be used by different functions
    # maybe better practice to not use all these globals but passing them as parameters everywhere will be annoying
    folder, city = read_sys_args(sys.argv)
    in_folder = folder + '{}/'.format(city)
    in_wkt = in_folder + 'links_wkt.csv'
    if not os.path.isdir(folder + 'mandel'):  # create the mandel folder if it doesnt already exist
        os.mkdir(folder + 'mandel')
    folder += 'mandel/'
    turn_link_pair_file = folder + 'turn_link_pairs.csv'
    turn_link_pair_gid_file = folder + 'turn_pair_gid.csv'
    mega_link_file = folder + 'mega_f_star.csv'
    td_subpath_file = folder + 'node_maneuver_subpath_td.csv'
    nontd_subpath_file = folder + 'node_maneuver_subpath_nontd.csv'
    td_maneuver_size_file = folder + 'td_maneuver_size.json'
    num_lane_file = folder + 'num_lane.npy'
    lanes_in_wkt_order = []
    time_depen_links = set()
    mega_links = []
    maneuver_ids = {}  # (pair) : id
    link_nodes = {}
    links_successors = {}  # it might make more sense to store everything in once dictionary of dictionaries
    links_predecessors = {}
    gid_to_parade = {}
    link_geom = {}
    link_ltype = {}
    parade_to_gid = {}
    nodes_to_link = {}
    pair_signal_type = {}

    read_wkt(in_wkt)
    signalized_links = read_signal_locations(city, gid_to_parade)
    intersection_links, roundabout_links, texas_u_links = read_intersection_links(city, gid_to_parade)
    restrictions = read_restrictions(city, gid_to_parade)
    generate_mega_links()  # this must be before turn pair generation
    maneuver_types = calc_turn_type()
    conflicts = conflicting_links()
    create_maneuver_ids()
    # start output
    mega_links_to_output = prepare_mega_for_output()
    num_td_maneuvers = write_subpaths(td_subpath_file, nontd_subpath_file)
    output(turn_link_pair_file, turn_link_pair_gid_file, td_maneuver_size_file, mega_link_file)
    # new file added by asif 1-4-2017
    mutual_maneuvers_filepath = folder + 'mutual_maneuvers.json'
    find_mutuals(turn_link_pair_file, mutual_maneuvers_filepath)

    end_time = time.time()
    print "--- finished in %.2f seconds ---" % (end_time - start_time)
