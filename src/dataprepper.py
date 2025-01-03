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
from tqdm import tqdm

from util import filter_function, fetch_annotations, fetch_dataseries, tag_list_to_struct, sanitize_tag_struct

@click.group()
def cli():
    pass

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
        start_time_str = datetime.datetime.fromtimestamp(a["time"] / 1000, tz=datetime.timezone.utc).strftime(date_string_format)
        end_time_str = datetime.datetime.fromtimestamp(a["timeEnd"] / 1000, tz=datetime.timezone.utc).strftime(date_string_format)
        tag_struct = tag_list_to_struct(a["tags"])
        tag_string = ""
        if len(tag_struct["veh_type"]) == 1:
            tag_string += f"{tag_struct['veh_type'][0][:4]:<4} "
        else:
            tag_string += f"     "

        if len(tag_struct["floor_type"]) <= 1:
            tag_string += f"{".".join(tag_struct['floor_type'])[:6]:<6}  "
        else:
            tag_string += f"{".".join([_[:3] for _ in tag_struct['floor_type']])} "
        
        if len(tag_struct["movement_type"]) <= 1:
            tag_string += f"{".".join(tag_struct['movement_type'])[:7]:>7}/"
        else:
            tag_string += f"{".".join([_[:3] for _ in tag_struct['movement_type']])}/"
        
        if len(tag_struct["movement_direction"]) <= 1:
            tag_string += f"{".".join(tag_struct['movement_direction'])[:7]:<7}"
        else:
            tag_string += f"{".".join([_[:3] for _ in tag_struct['movement_direction']])}"

        if len(tag_struct["short_event"]) <= 1:
            tag_string += f" {".".join(tag_struct['short_event'])[:7]:<7}"
        else:
            tag_string += f" {".".join([_[:3] for _ in tag_struct['short_event']])}"

        tag_string += f"{','.join(tag_struct['other'])}"
        print(selstr, str(start_time_str).rjust(18), str(end_time_str).rjust(18), a["text"][:38].strip().ljust(38), tag_string)

    print("\n")
    print(f"cumulated duration of {cumulated_tag_count} selected tags: {round(cumulated_tag_time / 1000, 1)} seconds (= {round(cumulated_tag_time / 60000, 1)} mins)")


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
                upload_description += f'={a["text"].strip()}'
            else:
                if last_matched: # upload last segment
                    data.extend(fetch_dataseries(grafanaconfigfile, upload_start_time, last_end_timestamp, upload_description))
                # … and start next segment
                upload_start_time = a["time"]
                upload_description = a["text"].strip()

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
@click.option("--oversamplingFreq", default=1000, type=float, help="Oversampling frequency for data-dejittering. Defaults to 1kHz. If set to zero or negative, oversampling is deactivated.")
@click.option("--chunkSize", default=500, type=int, help="Chunk size used for grouping and statistical analysis. defaults to 500ms.")
@click.option("--chunkOverlap", default=0, type=float, help="Overlap between two chunks/windows used for statistical analysis")
@click.option("--usedDataTracks", default="xyzH,xyzL,xyzG,abcG", help="comma seperated list of data tracks to be used. possible values: xyzH,xyzL,xyzG,abcG")
@click.option("--usedStatFilters", default="mean,std,mad,min,max,sma,iqr,entropy,energy,energy_band", help="comma seperated list of statistical features to be calculated. see doc/performance.md for further elaboration. possible values: mean,std,mad,min,max,sma,iqr,entropy,energy,energy_band")
def raw_csv_to_har_format(inputfile, outputfile, oversamplingfreq, chunksize, chunkoverlap, useddatatracks, usedstatfilters):
    import numpy as np
    import scipy as scp
    import pandas as pd
    #import spectrum as spec
    import math
    import time
    from matplotlib import pyplot as plt

    # preprocessing all parameters

    useddatatracks = [_.strip() for _ in useddatatracks.strip().split(",")]
    usedstatfilters = [_.strip() for _ in usedstatfilters.strip().split(",")]

    print("1/ reading input file")
    data_df = pd.read_csv(inputfile)
    if "ticks" in data_df:
        data_df["ticks"] = data_df["ticks"] / 1000 + time.time()
        data_df["time"] = pd.to_datetime(data_df['ticks'],unit='s')
        del data_df["ticks"]
    else:
        data_df["time"] = pd.to_datetime(data_df["time"])

    ## delete all unnamed columns (e.g. the "0"-column in the exports)
    data_df = data_df.loc[:, ~data_df.columns.str.contains('^Unnamed')]
    print(f"2/ fetched {data_df.shape[0]} lines.")
    ## set index. important!
    data_df = data_df.set_index("time")

    #### add the "magnitude columns combining xyz/abc" and filter by useddatatracks
    if "xyzH" in useddatatracks:
        data_df["xyzH"] = np.sqrt(data_df["xH"] ** 2 + data_df["yH"] ** 2 + data_df["zH"] ** 2)
    else:
        del data_df["xH"]
        del data_df["yH"]
        del data_df["zH"]
    
    if "xyzL" in useddatatracks:
        data_df["xyzL"] = np.sqrt(data_df["xL"] ** 2 + data_df["yL"] ** 2 + data_df["zL"] ** 2)
    else:
        del data_df["xL"]
        del data_df["yL"]
        del data_df["zL"]

    if "xyzG" in useddatatracks:
        data_df["xyzG"] = np.sqrt(data_df["xG"] ** 2 + data_df["yG"] ** 2 + data_df["zG"] ** 2)
    else:
        del data_df["xG"]
        del data_df["yG"]
        del data_df["zG"]
    
    if "abcG" in useddatatracks:
        data_df["abcG"] = np.sqrt(data_df["aG"] ** 2 + data_df["bG"] ** 2 + data_df["cG"] ** 2)
    else:
        del data_df["aG"]
        del data_df["bG"]
        del data_df["cG"]

    #### compensate the data-aquisition-jitter (by upsampling and interpolation)
    # Alternative: Use nearest-neighbour or spline-interpolation instead of linear one?
    # method=linear = ignores the index and treats them as equally spaced. not suitable for usecase, use method=time!
    if oversamplingfreq > 0:
        print(f"3/ resampling dataset to virtual aquisition rate of {oversamplingfreq} Hz")
        oversampling_timedelta = 1 / oversamplingfreq
        data_df = data_df.resample(f"{oversampling_timedelta}s").mean().interpolate(method='time')
    else: # do not resample (reduce RAM consumption), estimate the sampling frequency by using the first two elements
        oversampling_timedelta = (data_df.index[1] - data_df.index[0]).total_seconds()
        oversamplingfreq = 1.0 / oversampling_timedelta
        print(f"3/ NOT resampling dataset. instead assuming sample rate of {oversamplingfreq} Hz")
    # optional: downsample again to e.g. 50Hz used in HAR-Dataset?

    #### remove noise and split into "body" and "gravitation"-branches
    # define butterworth filter
    def bworth_filter(data, f_sample, order, f_corner, btype="low"):
        cutoff = f_corner / (0.5 * f_sample)
        b, a = scp.signal.butter(order, cutoff, btype=btype, analog=False)

        return scp.signal.filtfilt(b, a, data)

    print("4/ apply filters (butterworth, derivatives) to resampled data")
    # apply filter to all columns
    body_df = data_df.apply(lambda col: bworth_filter(col, oversamplingfreq, 3, 20))

    gravity_df = data_df.apply(lambda col: bworth_filter(col, oversamplingfreq, 3, 0.3))

    #baseline_df = pd.merge_asof(body_df, gravity_df, left_index=True, right_index=True, direction="nearest", suffixes=("_body", "_gravity"))
    baseline_df = pd.merge(body_df, gravity_df, left_index=True, right_index=True, how="outer", suffixes=("_body", "_gravity"))

    # derivate "acceleration to jerk" 
    derivative_df = baseline_df.apply(lambda col: np.gradient(col, edge_order=2))

    intermediate_df = pd.merge(baseline_df, derivative_df, left_index=True, right_index=True, how="outer", suffixes=("_accel", "_jerk"))

    #### Sampling/Batching for statistical feature generation
    print("5/ generate data-windows and iterate through them. this may take a while.")
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
    for group_id in tqdm(range(window_count)):
        group_start_idx = int(np.floor(group_id * (samplect * (1-chunkoverlap))))
        group_end_idx = int(np.floor(group_start_idx + samplect))

        group = intermediate_df[group_start_idx:group_end_idx]
        timestamps = list(group.index.map(lambda _: _.timestamp()))
        
        statistic_features = []
        # add basic metrics
        if "mean" in usedstatfilters:
            statistic_features.append(group.mean().add_suffix("_Tmean"))
        if "std" in usedstatfilters:
            statistic_features.append(group.std().add_suffix("_Tstd"))
        if "mad" in usedstatfilters:
            statistic_features.append(group.apply(lambda col: scp.stats.median_abs_deviation(col.values)).add_suffix("_Tmad"))
        if "min" in usedstatfilters:
            statistic_features.append(group.min().add_suffix("_Tmin"))
        if "max" in usedstatfilters:
            statistic_features.append(group.max().add_suffix("_Tmax"))
        if "sma" in usedstatfilters:
            statistic_features.append(group.apply(lambda col: scp.integrate.simpson(y=np.abs(col.values), x=timestamps)).add_suffix("_Tsma"))
        if "iqr" in usedstatfilters:
            statistic_features.append(group.apply(lambda col: np.subtract(*np.percentile(col.values, [75, 25]))).add_suffix("_Tiqr"))
        if "entropy" in usedstatfilters:
            statistic_features.append(group.apply(lambda col: scp.stats.entropy(col.values)).add_suffix("_Tentropy"))
        if "energy" in usedstatfilters:
            statistic_features.append(group.apply(lambda col: np.average(np.power(col.values, 2))).add_suffix("_Tenergy"))


        # add AR-coefficients https://pyspectrum.readthedocs.io/en/latest/ref_param.html#spectrum.burg.arburg
        #arburg_order = 4
        #for n in range(arburg_order):
        #column_list.append()
        #arburg = group.apply(lambda col: spec.arburg(np.fabs(col.values), 4)[0]).add_suffix(f"_Tarburg_coeff")
            #column_list.append(group.apply(lambda col: spec.arburg(col.values, arburg_order)[0].real[n]).add_suffix(f"_Tar_coeff_{n}"))

        # add Frequency Space information
        #def apply_fft(col, band_count=8):
        if "energy_band" in usedstatfilters:
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
            statistic_features.append(pd.concat(v_fft_list))

        # add to the output table
        combi = pd.concat(statistic_features, axis=0)
        
        output_data.append(combi)
        if group_id % (window_count/20) == 0:
            print("#", end="")

    print("6/ data generation complete.")
    final_data = pd.DataFrame(output_data)
    print(f"7/ dumping dataset of shape {final_data.shape} into file '{outputfile}'.")
    final_data.to_csv(outputfile, index=False)
    print("8/ done. quitting.")

if __name__ == "__main__":
    cli()
