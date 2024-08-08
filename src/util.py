__author__ = "Leon Schnieber"
__version__ = "1.0.1"
__maintainer__ = "Leon Schnieber"
__email__ = "leon@faler.ch"
__status__ = "Development"

import json
import requests

def filter_function(tagfilter, annotation):
    if tagfilter == "":
        return True
    for and_filter in tagfilter.strip().split(";"):
        filter_match = True
        for subfil in and_filter.split(","):
            if subfil not in annotation["tags"]:
                filter_match = False
                break
        if filter_match:
            return True
    return filter_match

def tag_list_to_struct(tag_list):
    struct = {
        "veh_type": [],
        "floor_type": [],
        "movement_type": [],
        "movement_direction": [],
        "short_event": [],
        "other": []
    }
    for t in tag_list:
        if t[-4:] == "_veh":
            struct["veh_type"].append(t.split("_veh")[0].strip())
        elif t[-4:] == "_flo":
            struct["floor_type"].append(t.split("_flo")[0].strip())
        elif t[-4:] == "_mov":
            struct["movement_type"].append(t.split("_mov")[0].strip())
        elif t[-4:] == "_dir":
            struct["movement_direction"].append(t.split("_dir")[0].strip())
        elif t[-4:] == "_evt":
            struct["short_event"].append(t.split("_evt")[0].strip())
        else:
            struct["other"].append(t)
    return struct

def sanitize_tag_struct(tag_struct):
    errors = []
    # sanitizer rules

    if "idl" not in tag_struct["movement_type"] and tag_struct["movement_type"] != []:
        if tag_struct["movement_direction"] == []:
            errors.append("[001] not idling but no direction is set?")
        if tag_struct["veh_type"] == []:
            errors.append("[002] not idling but no vehicle tagged?")

    if "flo-chng" in tag_struct["short_event"] and len(tag_struct["floor_type"]) != 2:
        errors.append("[003] floor-change event needs two floor types.")

    if "turn" in tag_struct["movement_type"]:
        if len(tag_struct["movement_direction"]) == 0:
            erorrs.append("[004] turn movements should have a direction attached.")

        tmp = tag_struct["movement_type"].copy()
        tmp.remove("turn")
        if len(tmp) < 1:
            errors.append("[005] misses another movement-type-tag. ('turn' is an overlay)")

    if "counw" in tag_struct["movement_direction"] or "clocw" in tag_struct["movement_direction"]:
        tmp = tag_struct["movement_direction"].copy()
        tmp.remove("counw") if "counw" in tmp else True
        tmp.remove("clocw") if "clocw" in tmp else True
        if len(tmp) < 1:
            errors.append("[006] misses another directionality-layer (forward, backward, …)")

    # last check: sanity!
    if "sane" in tag_struct["other"]:
        errors = [f"[000] sane-flag is set. ignoring {len(erorrs)} errors/warnings."]

    return errors

def fetch_annotations(grafanaconfigfile):
    with open(grafanaconfigfile, "r") as f:
        config = json.load(f)
    auth_header = {"Authorization": f"Bearer {config['grafana_token']}"}

    annotation_url = f"{config['grafana_base_url']}/api/annotations?from=0&to=180656035630300&limit=1000000&matchAny=false" #&dashboardUID={config['grafana_dashboard_uid']}"
    annotation_req = requests.get(annotation_url, headers=auth_header)

    annotation_list = annotation_req.json()
    annotation_list = sorted(annotation_list, key=lambda d: d['time']) # sort time-ascending
    return annotation_list

def fetch_dataseries(grafanaconfigfile, startTime, endTime, description=""):
    with open(grafanaconfigfile, "r") as f:
        config = json.load(f)
    auth_header = {"Authorization": f"Bearer {config['grafana_token']}"}


    print("\033[94madding\033[0m", description, end="")

    data_query = f'SELECT aG, bG, cG, xG, yG, zG, xH, yH, zH, xL, yL, zL FROM "autogen"."schnieboard_meas" WHERE time >= {startTime}ms and time <= {endTime}ms;'
    data_url = f"{config['grafana_base_url']}/api/datasources/proxy/uid/{config['grafana_datasource_uid']}/query?db=master&q={requests.utils.quote(data_query)}"
    data_req = requests.get(data_url, headers=auth_header)

    data_list = data_req.json()
    data = []
    if "series" in data_list["results"][0]:
        data_subset = data_list["results"][0]["series"][0]
        data_cols = data_subset["columns"]
        
        for row in data_subset["values"]:
            data.append(dict(zip(data_cols, row)))
        print("\r\033[92m done \033[0m", description)
    else:
        print("\r\033[91merror:\033[0m", "no rows in time range of", f'({description})')
    return data