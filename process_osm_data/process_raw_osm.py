from __future__ import print_function
import xml.etree.cElementTree as cElementTree
import time
from sys import getsizeof, stderr
from itertools import chain
from collections import deque
import unicodecsv as csv

# TODO: account for lanes:forward and lanes:backward
# used to check memory consumption
# see http://code.activestate.com/recipes/577504/ for explanation
def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)

def represents_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_through_nodes(way_id, first_nd, second_nd):
    if first_nd == second_nd:
        all_nodes = orig_ways[way_id].nodes
        first_idx = all_nodes.index(first_nd)
        second_idx = all_nodes[first_idx+1:].index(second_nd) + first_idx + 1  # list slice makes the sec index off by (first_index + 1)
        return all_nodes[first_idx+1:second_idx]
    else:
        if first_nd < 0 or second_nd < 0:
            return []
        all_nodes = orig_ways[way_id].nodes
        first_idx = all_nodes.index(first_nd)
        second_idx = all_nodes.index(second_nd)
        if second_idx < first_idx and all_nodes.count(second_nd) > 1:  # account for links referencing same node twice
            second_idx = all_nodes[first_idx+1:].index(second_nd) + first_idx + 1
        return all_nodes[first_idx+1:second_idx]  # return everything between first and last node


def nodes_to_wkt(node_list):
    wkt = 'LINESTRING ('
    for node in node_list:
        x = nodes[node].longitude
        y = nodes[node].latitude
        wkt += str(x) + ' ' + str(y) + ','
    wkt = wkt[:-1] + ')'
    return wkt


class Node(object):
    __slots__ = 'osmid', 'latitude', 'longitude', 'count'

    def __init__(self, osmid, latitude, longitude):
        self.osmid = int(osmid)
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.count = 0

    def get_geom(self):
        return [self.longitude, self.latitude]


class Link(object):
    __slots__ = 'osmid', 'name', 'speed', 'lane', 'highway', 'oneway', 'nodes', 'ltype', 'category'

    def __init__(self, osmid, nm, sp, ln, hghwy, onew, nds, lt, cat):
        self.osmid = int(osmid)
        self.name = nm
        self.speed = sp
        self.lane = ln
        self.highway = hghwy
        self.oneway = onew
        self.nodes = nds
        self.ltype = lt
        self.category = cat
print('...')
start_time = time.time()

folder = 'D:/Will/GIS Data/Raw OSM Data/Houston/'
raw_osm_file = folder + 'Houston.osm'


nodes = {}  # id : Node(osm_id, lat, lon)
orig_ways = {}  # osmid : Link

# Need an XML parser that does not load everything into memory in order to handle bigger networks
# See http://effbot.org/zone/element-iterparse.htm for explanation of this parser
print('reading data...')
context = cElementTree.iterparse(raw_osm_file, events=("start", "end"))
context = iter(context)
event, root = context.next()
print('starting loop')
for event, elem in context:
    # build a dictionary of node info
    if event == "end" and elem.tag == "node":
        lat = float(elem.get('lat'))
        lon = float(elem.get('lon'))
        osm_id = int(elem.get('id'))
        nodes[osm_id] = Node(osm_id, lat, lon)
        root.clear()  # This will clear entire ElementTree that the parser builds to save memory
    elif event == "end" and elem.tag == "way":
        osm_id = int(elem.get('id'))
        name = None
        speed = None
        lanes = None
        highway = None
        oneway = None
        ltype = None
        category = None
        ref = None
        way_nodes = []
        create_link = True
        iterator = elem.iter()
        nodes_to_iterate = []
        for child in iterator:
            if child.tag == "nd":
                nd = int(child.get('ref'))
                if nd in nodes:
                    way_nodes.append(nd)
                    nodes_to_iterate.append(nd)  # this might be a footpath or railroad in which case this is not something we want to split on
                else:
                    create_link = False  # don't create link that references node outside bounding box
            elif child.tag == "tag":
                if child.get('k') == 'name':
                    name = child.get('v')
                elif child.get('k') == 'maxspeed':
                    string_stripped = child.get('v').replace("mph", "").strip()
                    if represents_int(string_stripped):
                        speed = int(string_stripped)
                elif child.get('k') == 'lanes':
                    if represents_int(child.get('v')):
                        lanes = int(child.get('v'))
                elif child.get('k') == 'highway':
                    highway = child.get('v')
                elif child.get('k') == 'oneway':
                    oneway = child.get('v')
                elif child.get('k') == 'amenity' and child.get('v') == 'parking':
                    highway = 'parking'
                elif child.get('k') == 'service' and (child.get('v') == 'parking' or child.get('v') == 'parking_aisle'):
                    highway = 'parking'
                elif child.get('k') == 'ref':
                    ref = child.get('v')
        # way needs to have one of these highway tags in order to be useful to us
        if oneway == '-1':  # this tag means the link was drawn in opposite direction
            way_nodes.reverse()
            oneway = 'yes'
        if oneway != 'yes' and oneway != 'true':
            # lanes
            lanes = None
        # motorway name field is usually colloquial (i.e. Patriot Freeway) while ref is the official name (i.e. I-10)
        if highway == 'motorway' and ref is not None:
            name = ref

        if (highway == 'motorway' or highway == 'motorway_link' or highway == 'trunk' or highway == 'trunk_link' or
                highway == 'primary' or highway == 'secondary' or highway == 'tertiary'or highway == 'primary_link'or
                highway == 'secondary_link' or highway == 'tertiary_link' or highway == 'track' or highway == 'road' or
                highway == 'residential' or highway == 'living_street' or highway == 'service' or
                highway == 'unclassified' or highway == 'parking') and create_link:

            ltype = 0
            category = 0
            orig_ways[osm_id] = (Link(osm_id, name, speed, lanes, highway, oneway, way_nodes, ltype, category))
            for each in nodes_to_iterate:
                nodes[each].count += 1
        root.clear()
    elif event == "end" and elem.tag == "relation":
        # restrictions handled in separate script
        root.clear()

print ('size of nodes', (total_size(nodes) / 1000000))
print ('size of links', (total_size(orig_ways) / 1000000))
print ('data parsed')
# Should now have all OSM data parsed into nodes, orig_ways, orig_restrictions
# Nodes to split on have count > 1
# Need to deal with links that reference the same node twice
new_links = {}  # (fromNode, toNode) : Link
current_new_node_id = -1
for key, link in orig_ways.iteritems():
    first_node = link.nodes[0]
    temp = first_node
    for nd in link.nodes[1:]:
        if (nodes[nd].count > 1) or (nd is link.nodes[-1]):  # if it is an intersection or last node, create a link
            # if another link already has the same from and to nodes
            if (first_node, nd) in new_links or (first_node == nd):
                between_nodes = get_through_nodes(key, first_node, nd)
                # if it has feature points then use one of those as the from/to node
                if len(between_nodes) > 0:
                    middle_node = between_nodes[len(between_nodes) // 2]
                    new_links[(first_node, middle_node)] = Link(link.osmid, link.name, link.speed, link.lane, link.highway, link.oneway, ([first_node] + get_through_nodes(key, first_node, middle_node) + [middle_node]), link.ltype, link.category)
                    new_links[(middle_node, nd)] = Link(link.osmid, link.name, link.speed, link.lane, link.highway, link.oneway, ([middle_node] + get_through_nodes(key, middle_node, nd) + [nd]), link.ltype, link.category)
                else:
                    mid_lat = (nodes[first_node].latitude + nodes[nd].latitude) / 2  # creating artificial node
                    mid_lon = (nodes[first_node].longitude + nodes[nd].longitude) / 2
                    nodes[current_new_node_id] = Node(current_new_node_id, mid_lat, mid_lon)
                    new_links[(first_node, current_new_node_id)] = Link(link.osmid, link.name, link.speed, link.lane, link.highway, link.oneway, ([first_node, current_new_node_id]), link.ltype, link.category)
                    new_links[(current_new_node_id, nd)] = Link(link.osmid, link.name, link.speed, link.lane, link.highway, link.oneway, ([current_new_node_id, nd]), link.ltype, link.category)
                    current_new_node_id -= 1  # iterate to maintain unique link id's
            else:
                new_links[(first_node, nd)] = Link(link.osmid, link.name, link.speed, link.lane, link.highway, link.oneway, ([first_node] + get_through_nodes(key, first_node, nd)) + [nd], link.ltype, link.category)
            first_node = nd  # dont need to update first_node if it is just a feature point
print ('links split')
# now create reverse links
for key, value in new_links.items():
    if value.oneway == 'yes' or value.oneway == 'true' or value.highway == 'motorway':
        pass
    else:
        if (key[1], key[0]) in new_links:
            between_nodes = get_through_nodes(value.osmid, key[0], key[1])
            if len(between_nodes) > 0:
                middle_node = between_nodes[len(between_nodes) // 2]
                new_links[key[1], middle_node] = Link(value.osmid, value.name, value.speed, value.lane, value.highway, value.oneway, ([key[1]] + get_through_nodes(value.osmid, middle_node, key[1])[::-1] + [middle_node]), value.ltype, value.category)
                new_links[middle_node, key[0]] = Link(value.osmid, value.name, value.speed, value.lane, value.highway, value.oneway, ([middle_node] + get_through_nodes(value.osmid, key[0], middle_node)[::-1] + [key[0]]), value.ltype, value.category)
            else:
                mid_lat = (nodes[key[1]].latitude + nodes[key[0]].latitude) / 2
                mid_lon = (nodes[key[1]].longitude + nodes[key[0]].longitude) / 2
                nodes[current_new_node_id] = Node(current_new_node_id, mid_lat, mid_lon)
                new_links[key[1], current_new_node_id] = Link(value.osmid, value.name, value.speed, value.lane, value.highway, value.oneway, [key[1], current_new_node_id], value.ltype, value.category)
                new_links[current_new_node_id, key[0]] = Link(value.osmid, value.name, value.speed, value.lane, value.highway, value.oneway, [current_new_node_id, key[0]], value.ltype, value.category)
                current_new_node_id -= 1
        else:
            new_links[(key[1], key[0])] = Link(value.osmid, value.name, value.speed, value.lane, value.highway, value.oneway, value.nodes[::-1], value.ltype, value.category)
print ('reverse links created')

with open((folder + 'wkt.csv'), 'wb') as outfile:
    writer = csv.writer(outfile, delimiter=',')
    writer.writerow(['MetropiaID', 'OSMID', 'street_name', 'speed', 'lane', 'highway', 'ltype', 'category', 'wkt'])
    metropia_id = 0
    for value in new_links.itervalues():
        metropia_id += 1
        try:
            writer.writerow([metropia_id, value.osmid, value.name, value.speed, value.lane, value.highway, value.ltype, value.category, nodes_to_wkt(value.nodes)])
        except UnicodeEncodeError:
            writer.writerow([metropia_id, value.osmid, '', value.speed, value.lane, value.highway, value.ltype, value.category, nodes_to_wkt(value.nodes)])
            print (str(value.osmid) + ' is missing a name due to UnicodeEncodeError')

print("Elapsed time... %s seconds" % (time.time() - start_time))