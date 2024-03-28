#!/usr/bin/python3
__author__ = "Leon Schnieber"
__version__ = "1.0.1"
__maintainer__ = "Leon Schnieber"
__email__ = "leon@faler.ch"
__status__ = "Development"

import json
import requests
import datetime
import click
import pandas as pd

@click.group()
def cli():
    pass


@cli.command()
@click.option("--grafanaConfigfile", default="config.json", help="path to the config-file containing the grafana config-data.")
@click.option("--tagFilter", default="", help="filter the annotations by their tag")
def list_annotations(grafanaconfigfile, tagfilter):  
    with open("config.json", "r") as f:
        config = json.load(f)

    auth_header = {"Authorization": f"Bearer {config['grafana_token']}"}
    annotation_url = f"{config['grafana_base_url']}/api/annotations?from=0&to=180656035630300&limit=10000&matchAny=false&dashboardUID={config['grafana_dashboard_uid']}"
    annotation_req = requests.get(annotation_url, headers=auth_header)

    annotation_list = annotation_req.json()

    print("     StartTime          EndTime           Description            Tags")
    for a in annotation_list:
        filter_match = False
        for subfil in a["tags"]:
            if subfil in tagfilter.strip().split(","):
                filter_match = True
                break

        if filter_match or tagfilter == "":
            selstr = "\033[92m[x]\033[0m"
        else:
            selstr = "\033[91m[ ]\033[0m"

        date_string_format = '%y-%m-%dT%H:%M:%S'
        start_time_str = datetime.datetime.utcfromtimestamp(a["time"] / 1000).strftime(date_string_format)
        end_time_str = datetime.datetime.utcfromtimestamp(a["timeEnd"]/1000).strftime(date_string_format)
        print(selstr, str(start_time_str).rjust(18), str(end_time_str).rjust(18), a["text"].ljust(22), a["tags"])


@cli.command()
@click.option("--grafanaConfigfile", default="config.json", help="path to the config-file containing the grafana config-data.")
@click.option("--tagFilter", default="", help="filter the annotations by their tag")
@click.option("--outputFile", default="data/rawExport.csv", help="Filename to output the data to")
def load_data_to_csv(grafanaconfigfile, tagfilter, outputfile):
    with open("config.json", "r") as f:
        config = json.load(f)

    auth_header = {"Authorization": f"Bearer {config['grafana_token']}"}
    annotation_url = f"{config['grafana_base_url']}/api/annotations?from=0&to=180656035630300&limit=10000&matchAny=false&dashboardUID={config['grafana_dashboard_uid']}"
    annotation_req = requests.get(annotation_url, headers=auth_header)

    annotation_list = annotation_req.json()

    data = []
    for a in annotation_list:
        filter_match = False
        for subfil in a["tags"]:
            if subfil in tagfilter.strip().split(","):
                filter_match = True
                break

        if filter_match or tagfilter == "":
            date_string_format = '%y-%m-%dT%H:%M:%S'
            start_time_str = datetime.datetime.utcfromtimestamp(a["time"] / 1000).strftime(date_string_format)
            end_time_str = datetime.datetime.utcfromtimestamp(a["timeEnd"]/1000).strftime(date_string_format)
            print("\033[94madding\033[0m", a["text"], end="")

            startTime = a["time"]
            endTime = a["timeEnd"]
            data_query = f'SELECT aG, bG, cG, xG, yG, zG, xH, yH, zH, xL, yL, zL FROM "autogen"."schnieboard_meas" WHERE time >= {startTime}ms and time <= {endTime}ms;'
            data_url = f"{config['grafana_base_url']}/api/datasources/proxy/uid/{config['grafana_datasource_uid']}/query?db=master&q={requests.utils.quote(data_query)}"
            data_req = requests.get(data_url, headers=auth_header)

            data_list = data_req.json()
            if "series" in data_list["results"][0]:
                data_subset = data_list["results"][0]["series"][0]
                data_cols = data_subset["columns"]
                
                for row in data_subset["values"]:
                    data.append(dict(zip(data_cols, row)))
                print("\r\033[92m done \033[0m", a["text"])
            else:
                print("\r\033[91merror:\033[0m", "no rows in time range of", f'({a["text"]})')
            

    data_df = pd.DataFrame(data)

    data_df.to_csv(outputfile)


if __name__ == "__main__":
    cli()