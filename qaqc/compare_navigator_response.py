import requests
from os import listdir
from os.path import isfile, join
import json


def get_nav_response(url):
    route_data = requests.get(url).json()
    navigator_url = route_data['data']['navigation_url']
    return requests.get(navigator_url).json()

def compare_instructions(old_instructions, new_instructions, outfile):
    if old_instructions == new_instructions:
        outfile.write('instructions are exactly the same\n')
        return
    link_sequence1 = [x['link'] for x in old_instructions]
    link_sequence2 = [x['link'] for x in new_instructions]
    if link_sequence1 != link_sequence2:
        outfile.write('link sequences are different\n')
    voice_sequence1 = [x['voice'] for x in old_instructions]
    voice_sequence2 = [x['voice'] for x in new_instructions]
    for v1, v2 in zip(voice_sequence1,voice_sequence2):
        if v1 != v2:
           outfile.write('{} \n became \n {} \n\n').format(v1,v2)




def read_nav_response(response):
    links = response['data']
    iterator = iter(links)
    all_links = []  # list of dictionaries that contain relevant attributes
    for item in iterator:
        link_attributes = {'link_id': item['link']}
        try:
            link_attributes['voice'] = item['voice']
        except KeyError:
            link_attributes['voice'] = None
        all_links.append(link_attributes)
    return all_links

if __name__ == '__main__':
    # get all the input files; must be named routeX.json
    in_folder = 'D:/Will/Python Projects/Network Conversions/QAQC/navigator responses/'
    files = [f for f in listdir(in_folder) if isfile(join(in_folder, f)) and f[-5:]=='.json' and f[:5] == 'route']
    for f in files:
        info = json.load(open(in_folder+f,'r'))
        route_url = info['route_url']
        old_data = info['data']

        new_navigator_response = get_nav_response(route_url)
        new_data = read_nav_response(new_navigator_response)

        out_changelog = open(in_folder+f[:-5]+'_changelog.txt','w')
        compare_instructions(old_data, new_data, out_changelog)
