import csv
import requests
import json


def get_navigator_response(url):
    route_data = requests.get(url).json()
    navigator_url = route_data['data']['navigation_url']
    return requests.get(navigator_url).json()

if __name__ == '__main__':
    in_file = open('test_routes.csv', 'rb')
    reader = csv.DictReader(in_file)
    i = 1
    for row in reader:
        route_url = row['url']
        navigation_response = get_navigator_response(route_url)
        links = navigation_response['data']
        iterator = iter(links)
        all_links = []  # list of dictionaries that contain relevant attributes
        for item in iterator:
            link_attributes = {'link_id': item['link']}
            try:
                link_attributes['voice'] = item['voice']
            except KeyError:
                link_attributes['voice'] = None
            all_links.append(link_attributes)
        info = {'route_url': route_url, 'data': all_links}
        out_file = open('route'+str(i)+'.json', 'w')
        json.dump(info, out_file)
