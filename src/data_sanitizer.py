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

from util import filter_function, fetch_annotations, tag_list_to_struct, sanitize_tag_struct

date_string_format = '%y-%m-%dT%H:%M:%S'

@click.group()
def cli():
    pass


@cli.command()
@click.option("--grafanaConfigfile", default="config.json", help="path to the config-file containing the grafana config-data.")
@click.option("--outputFile", default="index.html", help="file to output the html overview of all tags")
def sanitize_tags(grafanaconfigfile, outputfile):
    annotation_list = fetch_annotations(grafanaconfigfile)
    try:
        generation_time_string = datetime.datetime.now(datetime.UTC).isoformat() + " (UTC)"
    except BaseException:
        generation_time_string = datetime.datetime.utcnow().isoformat() + " (UTC)"
    output_str = f"""<html><meta charset="utf-8">
    <head>
        <title>Tagging sanitizer</title>
    </head>
    <body>
        <h1>Tagging sanitizer <small>generated at {generation_time_string}</small></h1>
        <table class="sortable">
            <thead>
            <tr>
                <th>start time</th>
                <th>end time</th>
                <th>description</th>
                <th>vehicle</th>
                <th>flooring</th>
                <th>mov. type</th>
                <th>mov. direction</th>
                <th>event</th>
                <th>other tags</th>
                <th>sanitizer comment</th>
            </tr>
            </thead>
            <tbody>
    """
    for a in annotation_list:
        tag_struct = tag_list_to_struct(a["tags"])

        duration = a["timeEnd"] - a["time"]
        clickable_url = f"https://smartpouch.foobar.rocks/d/be583447-7432-4ed2-b95d-bf6261b94c27/label-dashboard-don-t-delete?orgId=1&from={a['time']-duration*0.2}&to={a['timeEnd']+duration*0.2}"
        start_time_str = datetime.datetime.fromtimestamp(a["time"] / 1000, tz=datetime.timezone.utc).strftime(date_string_format)
        end_time_str = datetime.datetime.fromtimestamp(a["timeEnd"] / 1000, tz=datetime.timezone.utc).strftime(date_string_format)
        tag_struct = tag_list_to_struct(a["tags"])

        output_str += f"<tr><td>{start_time_str}</td><td>{end_time_str}</td><td><a href='{clickable_url}'>{a['text']}</a></td>"
        output_str += f"<td>{', '.join(tag_struct['veh_type'])}</td><td>{', '.join(tag_struct['floor_type'])}</td>"
        output_str += f"<td>{', '.join(tag_struct['movement_type'])}</td><td>{', '.join(tag_struct['movement_direction'])}</td>"
        output_str += f"<td>{', '.join(tag_struct['short_event'])}</td><td>{', '.join(tag_struct['other'])}</td>"

        output_str += f"<td>{'<br />'.join(sanitize_tag_struct(tag_struct))}</td>"
        output_str += "</tr>"

    output_str += "</tbody></table>"
    output_str += """
    <link href="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@latest/sortable.min.css" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@latest/sortable.min.js"></script>
    """
    output_str += "</body></html>"
    with open(outputfile, "w") as f:
        f.write(output_str)



@cli.command()
@click.option("--grafanaConfigfile", default="config.json", help="path to the config-file containing the grafana config-data.")
@click.option("--outputFile", default="statistics.html", help="file to output the statistics-view")
def calc_statistics(grafanaconfigfile, outputfile):
    import io
    import base64
    from matplotlib import pyplot as plt
    import numpy as np

    raw_struct = {"errors": {}}
    annotation_list = fetch_annotations(grafanaconfigfile)
    try:
        generation_time_string = datetime.datetime.now(datetime.UTC).isoformat() + " (UTC)"
    except BaseException:
        generation_time_string = datetime.datetime.utcnow().isoformat() + " (UTC)"

    # generate statistics-struct
    for a in annotation_list:
        tag_struct = tag_list_to_struct(a["tags"])
        start_time = datetime.datetime.fromtimestamp(a["time"] / 1000, tz=datetime.timezone.utc)
        end_time = datetime.datetime.fromtimestamp(a["timeEnd"] / 1000, tz=datetime.timezone.utc)
        delta = end_time - start_time

        for t in tag_struct:
            if t not in raw_struct:
                raw_struct[t] = {}
            for t_i in tag_struct[t]:
                if t_i not in raw_struct[t]:
                    raw_struct[t][t_i] = 0
                raw_struct[t][t_i] += delta.total_seconds()
        
        errors = sanitize_tag_struct(tag_struct)
        for er in errors:
            er = er.split("]")[0] + "]"
            if er not in raw_struct["errors"]:
                raw_struct["errors"][er] = 0
            raw_struct["errors"][er] += delta.total_seconds()
    
    raw_struct["errors"] = dict(sorted(raw_struct["errors"].items()))

    # generate report
    output_str = f"""
    <html><meta charset="utf-8">
    <head>
        <title>Tagging Statistics</title>
    </head>
    <body>
        <h1>Tagging Statistics <small>generated at {generation_time_string}</small></h1>
    """

    for t in raw_struct:
        plt.clf()
        plt.title(f"{t}")
        if t != "errors":
            plt.pie(raw_struct[t].values(), labels=raw_struct[t].keys(), autopct=lambda x: f"{(x * 0.01 / 60 * sum(raw_struct[t].values())):2.1f} min")
        else:
            plt.bar(raw_struct[t].keys(), height=(np.array(list(raw_struct[t].values())) / 60.0))
            plt.ylabel("time in [min]")

        file_handler = io.BytesIO()
        plt.savefig(file_handler, format='png')
        file_handler.seek(0)
        file_base64 = base64.b64encode(file_handler.read()).decode()
        
        output_str += f"<img src='data:image/png;base64,{file_base64}' />"

    output_str += "</body></html>"
    with open(outputfile, "w") as f:
        f.write(output_str)


if __name__ == "__main__":
    cli()
