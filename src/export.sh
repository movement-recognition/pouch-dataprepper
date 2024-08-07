#!/bin/bash

outXFile="data/conclusion_X.csv"
outyFile="data/conclusion_y.csv"

tempDir="/tmp/dataprepper"

CHUNK_SIZE=500
CHUNK_OVERLAP=0.6
OVERSAMPLING_FREQ=0 # disable oversampling because of heavy RAM usage

mkdir -p $tempDir

python3 dataprepper.py load-data-to-csv --tagFilter="dr-out_evt;lf-dw_evt" --mergeThreshold=100 --outputFile="$tempDir/export_down.csv"
python3 dataprepper.py load-data-to-csv --tagFilter="dr-un_evt;lf-up_evt" --mergeThreshold=100 --outputFile="$tempDir/export_up.csv"
python3 dataprepper.py load-data-to-csv --tagFilter="idl_mov" --mergeThreshold=100 --outputFile="$tempDir/export_idle.csv"
python3 dataprepper.py load-data-to-csv --tagFilter="dec_mov;acc_mov;crus_mov;turn_mov" --mergeThreshold=100 --outputFile="$tempDir/export_movement.csv" 


# run the csv-to-har process in parallel to speed up the process
pids=()
commands=(
    "python3 dataprepper.py raw-csv-to-har-format --inputFile=$tempDir/export_down.csv --outputFile=$tempDir/export_down.har.csv \
    --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ \
    --usedDataTracks=xyzH,xyzL,xyzG,abcG --usedStatFilters=mean,std,mad,min,max,sma,iqr,energy,energy_band" # entropy

    "python3 dataprepper.py raw-csv-to-har-format --inputFile=$tempDir/export_up.csv --outputFile=$tempDir/export_up.har.csv \
    --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ \
    --usedDataTracks=xyzH,xyzL,xyzG,abcG --usedStatFilters=mean,std,mad,min,max,sma,iqr,energy,energy_band" # entropy

    "python3 dataprepper.py raw-csv-to-har-format --inputFile=$tempDir/export_idle.csv --outputFile=$tempDir/export_idle.har.csv \
    --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ \
    --usedDataTracks=xyzH,xyzL,xyzG,abcG --usedStatFilters=mean,std,mad,min,max,sma,iqr,energy,energy_band" # entropy

    "python3 dataprepper.py raw-csv-to-har-format --inputFile=$tempDir/export_movement.csv --outputFile=$tempDir/export_movement.har.csv \
    --chunkSize=$CHUNK_SIZE --chunkOverlap=$CHUNK_OVERLAP --oversamplingFreq=$OVERSAMPLING_FREQ \
    --usedDataTracks=xyzH,xyzL,xyzG,abcG --usedStatFilters=mean,std,mad,min,max,sma,iqr,energy,energy_band" # entropy
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

loop_index=0
for export in $tempDir/*.har.csv; do
    # category name
    fn=$(basename $export .har.csv | sed -e 's/export_//')
    line_count=$(wc -l < "$export")

    if [[ "$loop_index" == 0 ]]; then # skip the first row in all files except the first one (only one header is needed)
        # dump to X-File
        cat $export >> $outXFile
        # dump label to y-File
        yes $fn | head -n $line_count >> $outyFile
    else
        ((line_count--)) # ignore the header line
        cat $export | tail -n+2 >> $outXFile
        # dump label to y-File
        yes $fn | head -n $line_count >> $outyFile
    fi

    loop_index=$((loop_index + 1))
done
