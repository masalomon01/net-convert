import numpy as np
import pandas as pd
import json


def find_mutuals(turn_link_pairs_filepath, mutual_maneuvers_filepath):
    tlp = pd.read_csv(turn_link_pairs_filepath)
    # from asif

    # find mutual mans:
    # Find the manUID's which have common fromLink between major-to-major-u and major-to-minor-left
    # 1. Find the major to major u-turns, list the fromLinks
    # 2. Find the major-to-minor left-turns where fromLinks are from step#1
    # 3. Group the by the fromLink, the manID's in each group will provide the mutual ones

    # kinship#1
    maj_maj_u = tlp[(tlp['from_ltype'].isin([5, 7])) & (tlp['to_ltype'].isin([5, 7])) & (tlp['turn_type'] == 3)]
    maj_min_l = tlp[(tlp['from_ltype'].isin([5, 7])) & (tlp['to_ltype'].isin([11])) & (tlp['turn_type'] == 2)]
    intersection = pd.merge(left=maj_maj_u, right=maj_min_l, how='inner', on='from_link')

    link = intersection['from_link'].unique()
    groups = []
    for i in link:
        group = np.unique(intersection[intersection['from_link'] == i][['manID_x', 'manID_y']].as_matrix())
        # print group
        if group.size > 2:
            pass
        groups.append(group.tolist())
        # print groups
    json.dump(groups, open(mutual_maneuvers_filepath, 'w'))