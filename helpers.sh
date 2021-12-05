#!/usr/bin/env bash
IFS=""
mapfile -t dirlist < <(find ./raw -maxdepth 1 -mindepth 1 -type d -printf '%f\n');
for DIR in ${dirlist[@]}; do
    echo $DIR
    DRIVE=$(find "raw/$DIR" -name "DRIVE-*.txt" | tr -d '[:blank:]' | tr '/' ' ' | awk '{print $3}' | sed 's/DRIVE\-//g' | sed 's/\.txt//g')
    touch "raw/$DIR/${1}-${DRIVE}.txt"
done