## recording data
see [existing pouch-sw repo](https://github.com/movement-recognition/pouch-sw) for base-files and the [pouch-ucboard](https://github.com/movement-recognition/pouch-ucboard) repository for a short architectural overview. The script used for uploading the raw data the _ucboard_ (also called _Schnieboard_ internally) writes to its SD-card is placed inside this repo.

Due to reliability issues, the process doesn't rely on this method anymore. instead it uses the raspberry-pi-SBC inside the normal pouch-casing. The _ucboard_ is therefor connected to the Pi via USB and appears as a serial device there.

The `process_orange.py`-Script ([see here](https://github.com/movement-recognition/pouch-sw/blob/main/process_orange.py)) was refactored. First of all it's now called `purple.py`. Instead of pushing only the tris- and anal-Datapoints to the local influx-Database of the raspberry pi it now dumps all the incoming datapoints (so primarily the meas-datapoints are of big interest) directly to the console. By piping this output to a file a log is created automatically:

`python3 purple.py > logfile.jsonl`

Make sure, the system-time of the device is in sync either to UTC or your other time bases used in your lab setup. The data outputted is not completely conform to the [JSON line format](https://jsonlines.org/) because of disturbing print-outputs of the program. For parsing, lines containing no valid json-objects can just be ignored for now.

## uploading data

### directly from schnieboard-SD-card

### using `purple.py`

The `logupload.py` program should be used for ingesting the data to the influx database:

`python3 logupload.py upload-ljson --inputFile "test.json"`

After the upload is complete, data should now appear in the grafana-dashboard:
![Grafana Dashboard after file upload](grafana_upload_file.png)

If you can't see anything, use the time selector at the top right corner to select the date range you need. It helps to start with a bigger range and then zoom in to the ROI you want to work.

The dashed red lines mark the start- and endpoints of the file you just uploaded. if you hover over them you can see the filename.

## preparing videos

how to embed frame numbers into existing videos:
```
ffmpeg -i VID_20240327_112204Z.mp4 -vf " drawtext=fontfile=/usr/share/fonts/TTF/Inconsolata-Medium.ttf: text='%{pts} |%{frame_num}/%{nb_frames}': start_number=1: x=(w-tw)/2: y=h-(2*lh): fontcolor=black: fontsize=20: box=1: boxcolor=white: boxborderw=5" -c:a copy output_video.mp4
```

If you have timestamps in your video, also upload those to the database by also using the `logupload.py`-file by using the `upload-videostamps` method:

`python3 logupload.py upload-videostamps --inputFile="VID20233foobar.mp4" --startMarkerTime 2019-03-27T17:38:40.00 --startmarkerframe=100 --endmarkerframe=13785 --framerate 15.03`

If the upload was successful, you can go back to the grafana window and scroll down to the "Camera"-Plot. There you'll see a bunch of dots (if you are on big zoom levels it looks more like a thicker line). If you hover over them, you can extract the framenumer in the tooltip as well as compare it to the recorded data in the diagrams above by using the synchronized crosshairs displayed in all diagrams.
![hovering over a video frame](hover_videoframe.png)

## annotating data

To annotate the data, select the range you want to label by keeping the Ctrl-Key pressed while dragging the desired range with your mouse. When stopping this dragging motion, a popup-window appears as showed below. In there you can add a short description if you want, and most importantly add one or more tags from the list below.

![Adding tags to a time range](adding_tags.png)

| level | short | long form | description |
|-------|-------|-----------|-------------|
| basic | idle  | idling    | device is not moved, placed still on ground |
| tbd   | tbd   | tbd       | tbd         |

It helps, if you are only using one diagram for annotating (e.g. the one for "gyro") to avoid overlapping tagging -- but for the further steps it doesn't matter, all ranges are thrown together into one big dataset.


## download/generate training datasets

The dataset labeled in the grafana+influxDB-Stack can be extracted by the following chain of micro-tools:
First of all you need to download the raw sensor data, filtered by a selection of tags you want:

`python3 dataprepper.py list-annotations --tagFilter=idle,truck`

In the list below you'll get a preview of what tagged regions you'll get in your export.

```
     StartTime          EndTime           Description                                Tags
[ ]  24-03-27T11:36:11  24-03-27T11:36:11 Test005endofdata                           []
[ ]  24-03-27T11:35:36  24-03-27T11:35:36 actual end marker/end of video 005         ['end']
[ ]  24-02-15T15:23:38  24-02-15T15:23:39 main idle                                  ['idle']
[ ]  19-03-27T16:40:09  19-03-27T16:40:21 Idle drölf                                 ['idle']
[x]  19-03-27T16:38:46  19-03-27T16:39:01 Idle 1                                     ['idle', 'truck']
```

If you think, this selection fits your needs, you then can use your filter-query with the following command:

`python3 dataprepper.py load-data-to-csv --tagFilter=idle,truck --outputFile="data_idle.csv"`

This results in a kind of raw-file-format containing all raw data captured by the sensors -- but filtered by the filter.
```
,time,aG,bG,cG,xG,yG,zG,xH,yH,zH,xL,yL,zL
0,2019-03-27T11:36:11.622Z,-705,279,-161,-340,-1324,-14072,1879,1878,1859,-234,0,-9438
1,2019-03-27T16:40:09.37Z,-288,603,737,-272,-1856,-16656,1883,1877,1865,-702,-234,-11154
2,2019-03-27T16:40:09.375Z,-783,562,779,332,-2028,-16356,1874,1881,1865,0,-312,-11154
3,2019-03-27T16:40:09.38Z,-1275,153,872,736,-1120,-14868,1889,1877,1851,78,390,-9984
```

With a third processing method you can then convert this intermediate file into a format which is similar to the columns/statistical features used in the [HAR-Dataset](https://doi.org/10.24432/C54S4K)/[or here](https://www.semanticscholar.org/paper/A-Public-Domain-Dataset-for-Human-Activity-using-Anguita-Ghio/83de43bc849ad3d9579ccf540e6fe566ef90a58e):

`python3 dataprepper.py raw-csv-to-har-format --inputFile=data_idle.csv --outputFile=idle_data_har.csv`

If you want, you can use the following parameters to apply some basic kinds of augmentation: 
```
--chunkSize INTEGER       Chunk size used for grouping and statistical analysis. defaults to 500ms.
--chunkOverlap FLOAT      Overlap between two chunks/windows used for statistical analysis
```

You can get also get help or short explanation-texts for the parameters by calling all of the listed commands above with the `--help`-suffix.