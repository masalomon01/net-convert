import csv


def succ_with_diff_name(link_id):
    name = all_links[link_id]['primaryName']
    successors = all_links[link_id]['successors'].split(" ")[:-1] + all_links[link_id]['restrictedSuccessors'].split(" ")[:-1]
    for each in successors:
        if all_links[each]['primaryName'] != name:
            return True
    return False


def pred_with_diff_name(link_id):
    name = all_links[link_id]['primaryName']
    predecessors = all_links[link_id]['predecessors'].split(" ")[:-1] + all_links[link_id]['restrictedPredecessors'].split(" ")[:-1]
    for each in predecessors:
        if all_links[each]['primaryName'] != name:
            return True
    return False


def preds_succs_same_name(link_id):
    successors = all_links[link_id]['successors'].split(" ")[:-1] + all_links[link_id]['restrictedSuccessors'].split(" ")[:-1]
    predecessors = all_links[link_id]['predecessors'].split(" ")[:-1] + all_links[link_id]['restrictedPredecessors'].split(" ")[:-1]
    succ_names = [all_links[each]['primaryName'] for each in successors]
    pred_names = [all_links[each]['primaryName'] for each in predecessors]
    for i, each in enumerate(succ_names):
        if each in pred_names and each != '' and each != all_links[link_id]['primaryName']:
            succ_link = successors[i]
            if isOneWay(succ_link):
                return True
    return False


def isOneWay(link_id):
    if all_links[link_id]['reverseID_parade'] == '-1':
        return True
    else:
        return False

if __name__ == '__main__':
    folder = 'D:/Will/Metropia/Network Updates/EP_Juarez/Update 9-29-2016/elpaso_juarez/'
    in_wkt = folder + 'links_wkt.csv'
    out_file = folder + 'intersection_links.csv'
    out_file2 = folder + 'intersection_links_gid.csv'
    reader = csv.DictReader(open(in_wkt, 'rb'))
    writer = csv.writer(open(out_file, 'wb'))
    writer2 = csv.writer(open(out_file2, 'wb'))
    writer.writerow(['linkID', 'intersection'])
    writer2.writerow(['gid', 'intersection'])
    all_links = {}  # linkID_parade : {link_attribute_dict}
    short_links = []

    for row in reader:
        all_links[row['LinkID_parade']] = row

    already_printed = []
    not_intersection = []
    for parade_id, value in all_links.items():
        if float(value['length(feet)']) < 100 and succ_with_diff_name(parade_id) and pred_with_diff_name(parade_id) and preds_succs_same_name(parade_id) and parade_id not in already_printed:
            writer.writerow([parade_id, '1'])
            writer2.writerow([all_links[parade_id]['LinkID_ptv'], '1'])
            already_printed.append(parade_id)
            if all_links[parade_id]['reverseID_parade'] != '-1' and all_links[parade_id]['reverseID_parade'] not in already_printed:
                reverseID = all_links[parade_id]['reverseID_parade']
                writer.writerow([reverseID, '1'])
                writer2.writerow([all_links[reverseID]['LinkID_ptv'], '1'])
                already_printed.append(all_links[parade_id]['reverseID_parade'])
        else:
            not_intersection.append(parade_id)

