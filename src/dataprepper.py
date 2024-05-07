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

def fetch_annotations(grafanaconfigfile):
    with open(grafanaconfigfile, "r") as f:
        config = json.load(f)
    auth_header = {"Authorization": f"Bearer {config['grafana_token']}"}

    annotation_url = f"{config['grafana_base_url']}/api/annotations?from=0&to=180656035630300&limit=10000&matchAny=false&dashboardUID={config['grafana_dashboard_uid']}"
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


@cli.command()
@click.option("--grafanaConfigfile", default="config.json", help="path to the config-file containing the grafana config-data.")
@click.option("--tagFilter", default="", help="filter the annotations by their tag")
@click.option("--mergeThreshold", default=-1, help="time in ms when two labels with matching filter should be merged together. -1 = switched off = default.")
def list_annotations(grafanaconfigfile, tagfilter, mergethreshold):  
    
    annotation_list = fetch_annotations(grafanaconfigfile)

    cumulated_tag_time = 0.0
    cumulated_tag_count = 0

    # variables needed for merging
    last_end_timestamp = 0
    last_matched = False

    print("LEGEND")
    print("\033[92m[x]\033[0m = a new section begins at the start of this element")
    print("\033[94m[|]\033[0m = in the middle of a section")
    print("\033[91m[-]\033[0m = the section ended at the end of the element before this one")
    print()
    print("\033[92m[o]\033[0m = a section ended at the element in the row above AND a new section begins at the start of this element")
    print("\033[91m[ ]\033[0m = this element did not match any filter so it isn't part of the export.")
    print("")
    print("     StartTime          EndTime           Description                                Tags")
    for a in annotation_list:
        filter_match = filter_function(tagfilter, a)

        merge_thresh = mergethreshold > 0 and a["time"] - last_end_timestamp < mergethreshold and last_matched == True

        if filter_match:
            if merge_thresh:
                selstr = "\033[94m[|]\033[0m" # blue pipesymbol
            else:
                if last_matched:
                    selstr = "\033[92m[o]\033[0m" # green o
                else:
                    selstr = "\033[92m[x]\033[0m" # green x
                
            cumulated_tag_time += a["timeEnd"] - a["time"]
            cumulated_tag_count += 1
            
            last_matched = True
            last_end_timestamp = a["timeEnd"]
        else:
            if last_matched:
                selstr = "\033[91m[-]\033[0m" # red bracket
            else:
                selstr = "\033[91m[ ]\033[0m" # red bracket
            last_matched = False

        date_string_format = '%y-%m-%dT%H:%M:%S'
        start_time_str = datetime.datetime.utcfromtimestamp(a["time"] / 1000).strftime(date_string_format)
        end_time_str = datetime.datetime.utcfromtimestamp(a["timeEnd"]/1000).strftime(date_string_format)
        a["tags"].sort()
        print(selstr, str(start_time_str).rjust(18), str(end_time_str).rjust(18), a["text"][:42].ljust(42), a["tags"])

    print("\n")
    print(f"cumulated duration of {cumulated_tag_count} selected tags: {round(cumulated_tag_time/1000, 1)} seconds")


@cli.command()
@click.option("--grafanaConfigfile", default="config.json", help="path to the config-file containing the grafana config-data.")
@click.option("--tagFilter", default="", help="filter the annotations by their tag")
@click.option("--outputFile", default="data/rawExport.csv", help="Filename to output the data to")
@click.option("--mergeThreshold", default=-1, help="time in ms when two labels with matching filter should be merged together. -1 = switched off = default.")
def load_data_to_csv(grafanaconfigfile, tagfilter, outputfile, mergethreshold):
    with open(grafanaconfigfile, "r") as f:
        config = json.load(f)
        auth_header = {"Authorization": f"Bearer {config['grafana_token']}"}

    print(f"Exporting selected regions to {outputfile}…")
    annotation_list = fetch_annotations(grafanaconfigfile)

    data = []
    if tagfilter == "":
        print("no tagFilter supplied, using all tagged data existing")

     # variables needed for merging
    last_end_timestamp = 0
    last_matched = False

    upload_start_time = 0
    # upload_end_time = 0
    upload_description = ""
    for a in annotation_list:
        filter_match = filter_function(tagfilter, a)
        merge_thresh = mergethreshold > 0 and a["time"] - last_end_timestamp < mergethreshold and last_matched == True
        
        if filter_match:
            if merge_thresh:
                # piping through this segment, no upload action needed, just extending the description
                upload_description += f'={a["text"]}'
            else:
                if last_matched: # upload last segment
                    data.extend(fetch_dataseries(grafanaconfigfile, upload_start_time, last_end_timestamp, upload_description))
                # … and start next segment
                upload_start_time = a["time"]
                upload_description = a["text"]

            last_matched = True
            last_end_timestamp = a["timeEnd"]
        else:
            if last_matched:
                # upload last segment
                data.extend(fetch_dataseries(grafanaconfigfile, upload_start_time, last_end_timestamp, upload_description))
            else:
                pass # reset

            last_matched = False           

    data_df = pd.DataFrame(data)

    data_df.to_csv(outputfile)

@cli.command()
@click.option("--inputFile", default="data/rawExport.csv", help="Filename read the data from in 'raw' column format")
@click.option("--outputFile", default="data/harExport.csv", help="Filename to output the data to. Outputs in 'few-hundret-column'-format")
@click.option("--oversamplingFreq", default=1000, type=float, help="Oversampling frequency for data-dejittering. Defaults to 1kHz")
@click.option("--chunkSize", default=500, type=int, help="Chunk size used for grouping and statistical analysis. defaults to 500ms.")
@click.option("--chunkOverlap", default=0, type=float, help="Overlap between two chunks/windows used for statistical analysis")
def raw_csv_to_har_format(inputfile, outputfile, oversamplingfreq, chunksize, chunkoverlap):
    import numpy as np
    import scipy as scp
    import pandas as pd
    #import spectrum as spec
    import math
    import time
    from matplotlib import pyplot as plt

    data_df = pd.read_csv(inputfile)
    if "ticks" in data_df:
        data_df["ticks"] = data_df["ticks"] / 1000 + time.time()
        data_df["time"] = pd.to_datetime(data_df['ticks'],unit='s')
        del data_df["ticks"]
    else:
        data_df["time"] = pd.to_datetime(data_df["time"])

    ## delete all unnamed columns (e.g. the "0"-column in the exports)
    data_df = data_df.loc[:, ~data_df.columns.str.contains('^Unnamed')]
    
    ## set index. important!
    data_df = data_df.set_index("time")

    #### add the "magnitude columns combining xyz/abc"
    data_df["xyzH"] = np.sqrt(data_df["xH"] ** 2 + data_df["yH"] ** 2 + data_df["zH"] ** 2)
    data_df["xyzL"] = np.sqrt(data_df["xL"] ** 2 + data_df["yL"] ** 2 + data_df["zL"] ** 2)
    data_df["xyzG"] = np.sqrt(data_df["xG"] ** 2 + data_df["yG"] ** 2 + data_df["zG"] ** 2)
    data_df["abcG"] = np.sqrt(data_df["aG"] ** 2 + data_df["bG"] ** 2 + data_df["cG"] ** 2)

    #### compensate the data-aquisition-jitter (by upsampling and interpolation)
    # Alternative: Use nearest-neighbour or spline-interpolation instead of linear one?
    # method=linear = ignores the index and treats them as equally spaced. not suitable for usecase, use method=time!
    oversampling_timedelta = 1 / oversamplingfreq
    data_df = data_df.resample(f"{oversampling_timedelta}s").mean().interpolate(method='time')
    # optional: downsample again to e.g. 50Hz used in HAR-Dataset?

    #### remove noise and split into "body" and "gravitation"-branches
    # define butterworth filter
    def bworth_filter(data, f_sample, order, f_corner, btype="low"):
        cutoff = f_corner / (0.5 * f_sample)
        b, a = scp.signal.butter(order, cutoff, btype=btype, analog=False)

        return scp.signal.filtfilt(b, a, data)

    # apply filter to all columns
    body_df = data_df.apply(lambda col: bworth_filter(col, oversamplingfreq, 3, 20))

    gravity_df = data_df.apply(lambda col: bworth_filter(col, oversamplingfreq, 3, 0.3))

    #baseline_df = pd.merge_asof(body_df, gravity_df, left_index=True, right_index=True, direction="nearest", suffixes=("_body", "_gravity"))
    baseline_df = pd.merge(body_df, gravity_df, left_index=True, right_index=True, how="outer", suffixes=("_body", "_gravity"))

    # derivate "acceleration to jerk" 
    derivative_df = baseline_df.apply(lambda col: np.gradient(col, edge_order=2))

    intermediate_df = pd.merge(baseline_df, derivative_df, left_index=True, right_index=True, how="outer", suffixes=("_accel", "_jerk"))

    #### Sampling/Batching for statistical feature generation
    ## sample by time duration
    TIME_DURATION = f"{chunksize/1000}s"
    window_width = pd.Timedelta(milliseconds=chunksize)

    #intermediate_df["time_tmp"] = intermediate_df.index
    #intermediate_df['window_label'] = intermediate_df["time_tmp"].apply(lambda ts: ts.floor(window_width))

    ## sample by count
        #BATCH_SIZE = 128
        #intermediate_df['window_label'] = np.arange(len(intermediate_df)) // BATCH_SIZE

    #### process the groups one after another
    output_data = []

    # prepare the indexing for the data blocks
    samplect = (chunksize / 1000) / oversampling_timedelta
    window_count = math.ceil(intermediate_df.shape[0] / (samplect * (1-chunkoverlap)))
    for group_id in range(window_count):
        group_start_idx = int(np.floor(group_id * (samplect * (1-chunkoverlap))))
        group_end_idx = int(np.floor(group_start_idx + samplect))

        group = intermediate_df[group_start_idx:group_end_idx]
        timestamps = list(group.index.map(lambda _: _.timestamp()))
        
        # add basic metrics
        v_mean = group.mean().add_suffix("_Tmean")
        v_std = group.std().add_suffix("_Tstd")
        v_mad = group.apply(lambda col: scp.stats.median_abs_deviation(col.values)).add_suffix("_Tmad")
        v_min = group.min().add_suffix("_Tmin")
        v_max = group.max().add_suffix("_Tmax")
        v_sma = group.apply(lambda col: scp.integrate.simpson(y=np.abs(col.values), x=timestamps)).add_suffix("_Tsma")
        v_iqr = group.apply(lambda col: np.subtract(*np.percentile(col.values, [75, 25]))).add_suffix("_Tiqr")
        v_entropy = group.apply(lambda col: scp.stats.entropy(col.values)).add_suffix("_Tentropy")
        v_energy = group.apply(lambda col: np.average(np.power(col.values, 2))).add_suffix("_Tenergy")


        # add AR-coefficients https://pyspectrum.readthedocs.io/en/latest/ref_param.html#spectrum.burg.arburg
        #arburg_order = 4
        #for n in range(arburg_order):
        #column_list.append()
        #arburg = group.apply(lambda col: spec.arburg(np.fabs(col.values), 4)[0]).add_suffix(f"_Tarburg_coeff")
            #column_list.append(group.apply(lambda col: spec.arburg(col.values, arburg_order)[0].real[n]).add_suffix(f"_Tar_coeff_{n}"))

        # add Frequency Space information
        #def apply_fft(col, band_count=8):
        v_fft_list = []
        fft_band_count = 8
        for col_name in group:
            col = group[col_name]
            bands_data = scp.fft.fft(col.values)
            energy_spectrum = np.abs(bands_data[:len(bands_data)//2])**2
            band_width = math.ceil(len(bands_data) / (fft_band_count * 2))
            bands_energy = {}
            for i in range(fft_band_count):
                if i == 0: # ignore the DC-Part of FFT
                    s_idx = 1
                else:
                    s_idx = i * band_width
                e_idx = min(len(energy_spectrum), (i+1)*band_width)
                subband_energy = np.sum(energy_spectrum[s_idx:e_idx])
                bands_energy[col.name + f"_FenergyBand_{i}"] = subband_energy
            v_fft_list.append(pd.Series(bands_energy))
        v_fft = pd.concat(v_fft_list)

        # add to the output table
        combi = pd.concat([v_mean, v_std, v_mad, v_min, v_max, v_sma, v_iqr, v_entropy, v_energy, v_fft], axis=0)
        
        output_data.append(combi)

    final_data = pd.DataFrame(output_data)
    print("SHAPE", final_data.shape)
    final_data.to_csv(outputfile)

if __name__ == "__main__":
    cli()
