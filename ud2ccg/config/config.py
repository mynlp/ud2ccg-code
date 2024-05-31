import json


def read_obliqueness_hierarchy(path):
    obliqueness_hierarchy = {}

    with open(path, 'r') as f:
        json_data = json.load(f)

        for obj in json_data:
            obliqueness_hierarchy[obj['name']] = obj['priority']

        return obliqueness_hierarchy
