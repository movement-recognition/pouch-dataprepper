#!/usr/bin/python3
__author__ = "Leon Schnieber"
__version__ = "1.0.1"
__maintainer__ = "Leon Schnieber"
__email__ = "leon@faler.ch"
__status__ = "Development"

import json
import requests
import pandas as pd

with open("config.json", "r") as f:
    config = json.load(f)

auth_header = {"Authorization": f"Bearer {config['grafana_token']}"}

annotation_url = f"{config['grafana_base_url']}/api/annotations?from=1406556756303&to=1806560356303&limit=100&matchAny=false&dashboardUID={config['grafana_dashboard_uid']}"
annotation_req = requests.get(annotation_url, headers=auth_header)

annotation_list = annotation_req.json()

for a in annotation_list:
    print(a["time"], a["timeEnd"], a["text"], a["tags"])
    startTime = a["time"]
    endTime = a["timeEnd"]
    data_query = f'SELECT "x","y","z" FROM "autogen"."schnieboard_meas" WHERE time >= {startTime}ms and time <= {endTime}ms;'
    data_url = f"{config['grafana_base_url']}/api/datasources/proxy/uid/{config['grafana_datasource_uid']}/query?db=master&q={requests.utils.quote(data_query)}"
    data_req = requests.get(data_url, headers=auth_header)

    data_list = data_req.json()
    data_subset = data_list["results"][0]["series"][0]
    data_cols = data_subset["columns"]
    data = []
    for row in data_subset["values"]:
        data.append(dict(zip(data_cols, row)))


    data_df = pd.DataFrame(data)

    # print(data_df.describe())
    data_df.to_csv(f'data/raw_{a["text"].replace(" ", "_")}_.txt')