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

@click.group()
def cli():
    pass


@cli.command()
@click.option("--grafanaConfigfile", default="config.json", help="path to the config-file containing the grafana config-data.")
@click.option("--outputFile", default="index.html", help="file to output the html overview of all tags")
def sanitize_tags(grafanaconfigfile, outputfile):
    annotation_list = fetch_annotations(grafanaconfigfile)
    generation_time_string = datetime.datetime.now(datetime.UTC).isoformat() + " (UTC)"
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

        date_string_format = '%y-%m-%dT%H:%M:%S'
        duration = a["timeEnd"] - a["time"]
        clickable_url = f"https://smartpouch.foobar.rocks/d/be583447-7432-4ed2-b95d-bf6261b94c27/label-dashboard-don-t-delete?orgId=1&from={a['time']-duration*0.2}&to={a['timeEnd']+duration*0.2}"
        start_time_str = datetime.datetime.fromtimestamp(a["time"] / 1000, tz=datetime.timezone.utc).strftime(date_string_format)
        end_time_str = datetime.datetime.fromtimestamp(a["timeEnd"] / 1000, tz=datetime.timezone.utc).strftime(date_string_format)
        tag_struct = tag_list_to_struct(a["tags"])

        output_str += f"<tr><td>{start_time_str}</td><td>{end_time_str}</td><td><a href='{clickable_url}'>{a['text']}</a></td>"
        output_str += f"<td>{", ".join(tag_struct['veh_type'])}</td><td>{", ".join(tag_struct['floor_type'])}</td>"
        output_str += f"<td>{", ".join(tag_struct['movement_type'])}</td><td>{", ".join(tag_struct['movement_direction'])}</td>"
        output_str += f"<td>{", ".join(tag_struct['short_event'])}</td><td>{', '.join(tag_struct['other'])}</td>"

        output_str += f"<td>{"<br />".join(sanitize_tag_struct(tag_struct))}</td>"
        output_str += "</tr>"

    output_str += "</tbody></table>"
    output_str += """
    <link href="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@latest/sortable.min.css" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@latest/sortable.min.js"></script>
    """
    output_str += "</body></html>"
    with open(outputfile, "w") as f:
        f.write(output_str)

if __name__ == "__main__":
    cli()