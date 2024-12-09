#!/bin/bash

CONFIG_FILE="config.json"

dir="$1"

if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
fi

cp "$CONFIG_FILE" "$dir/$CONFIG_FILE"
