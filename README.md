## recording data
see [existing pouch-sw repo](https://github.com/movement-recognition/pouch-sw) for base-files and the [pouch-ucboard](https://github.com/movement-recognition/pouch-ucboard) repository for a short architectural overview. The script used for uploading the raw data the _ucboard_ (also called _Schnieboard_ internally) writes to its SD-card is placed inside this repo.

Due to reliability issues, the process doesn't rely on this method anymore. instead it uses the raspberry-pi-SBC inside the normal pouch-casing. The _ucboard_ is therefor connected to the Pi via USB and appears as a serial device there.

The `process_orange.py`-Script ([see here](https://github.com/movement-recognition/pouch-sw/blob/main/process_orange.py)) was refactored. First of all it's now called `purple.py`. Instead of pushing only the tris- and anal-Datapoints to the local influx-Database of the raspberry pi it now dumps all the incoming datapoints (so primarily the meas-datapoints are of big interest) directly to the console. By piping this output to a file a log is created automatically:

`python3 purple.py > logfile.jsonl`

Make sure, the system-time of the device is in sync either to UTC or your other time bases used in your lab setup. The data outputted is not completely conform to the [JSON line format](https://jsonlines.org/) because of disturbing print-outputs of the program. For parsing, lines containing no valid json-objects can just be ignored for now.

The `logupload.py` program should be used for ingesting the data to the influx database. 

!2024-04-04 TODO: usage examples!


## preparing videos

`ffmpeg -i VID_20240327_112204Z.mp4 -vf "drawtext=fontfile=/usr/share/fonts/TTF/Inconsolata-Medium.ttf: text='%{pts} |%{frame_num}/%{nb_frames}': start_number=1: x=(w-tw)/2: y=h-(2*lh): fontcolor=black: fontsize=20: box=1: boxcolor=white: boxborderw=5" -c:a copy output_video.mp4`


## annotating data

## download/generate training datasets

- column format is similar to the columns/statistical features used in the [HAR-Dataset](https://doi.org/10.24432/C54S4K)/[or here](https://www.semanticscholar.org/paper/A-Public-Domain-Dataset-for-Human-Activity-using-Anguita-Ghio/83de43bc849ad3d9579ccf540e6fe566ef90a58e)