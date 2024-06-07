#!/bin/bash

outXFile="/tmp/conclusion_X.har"
outyFile="/tmp/conclusion_y.har"

CHUNK_SIZE=500
CHUNK_OVERLAP=0.6
OVERSAMPLING_FREQ=1000

python3 dataprepper.py load-data-to-csv --tagFilter="dr-out_evt;lf-dw_evt" --mergeThreshold=100 --outputFile="data/export_down.csv"
python3 dataprepper.py load-data-to-csv --tagFilter="dr-un_evt;lf-up_evt" --mergeThreshold=100 --outputFile="data/export_up.csv"
python3 dataprepper.py load-data-to-csv --tagFilter="idl_mov" --mergeThreshold=100 --outputFile="data/export_idle.csv"
python3 dataprepper.py load-data-to-csv --tagFilter="dec_mov;acc_mov;crus_mov;turn_mov" --mergeThreshold=100 --outputFile="data/export_movement.csv" 


# run the csv-to-har process in parallel to speed up the process
pids=()
commands=(
    "python3 dataprepper.py raw-csv-to-har-format --inputFile=data/export_down.csv --outputFile=data/export_down.har --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ"
    "python3 dataprepper.py raw-csv-to-har-format --inputFile=data/export_up.csv --outputFile=data/export_up.har --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ"
    "python3 dataprepper.py raw-csv-to-har-format --inputFile=data/export_idle.csv --outputFile=data/export_idle.har --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ"
    "python3 dataprepper.py raw-csv-to-har-format --inputFile=data/export_movement.csv --outputFile=data/export_movement.har --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ"
)

for cmd in "${commands[@]}"; do
    $cmd &
    pids+=($!)
done
for pid in "${pids[@]}"; do
    wait $pid
done

# clear output files
echo "" > $outXFile
echo "" > $outyFile

for export in data/*.har; do
    # category name
    fn=$(basename $export .har | sed -e 's/export_//')
    line_count=$(wc -l < "$export")

    
    if [$LOOP_INDEX -eq 1]; then # skip the first row in all files except the first one (only one header is needed)
        # dump to X-File
        cat $export >> $outXFile
        # dump label to y-File
        yes $fn | head -n $line_count >> $outyFile
    else
        ((line_count--)) # ignore the header line
        cat $export | tail -n+2 >> $outXFile
        # dump label to y-File
        yes $fn | head -n $line_count >> $outyFile
    
done
