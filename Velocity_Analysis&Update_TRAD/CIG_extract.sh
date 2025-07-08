#!/bin/bash
# ==============================================================================
# Script Name: CIG_extract.sh
# Version: 1.1
# Author: Lining YANG, CNR-ISMAR Bologna
# Date: 2025-07-08 20:00
#
# Description: Extracts CDP traces from seismic data files and creates
#              output files with simplified names. Supports progress animation.
#
# Usage:
#   ./extract_cdp.sh -k <kdfile> -o <outfile1> -s <step> -f <first_cdp> [-l <last_cdp>]
#
# Parameters:
#   -k  Path to the 'kd.data_complete' file
#   -o  Path to the 'outfile1_complete' file
#   -f  First CDP to extract
#   -s  CDP step interval
#   -l  Last CDP to extract (optional; if omitted, all remaining CDPs will be extracted)
#
# Example:
#   ./CIG_extract.sh -k kd.data_complete -o outfile1_complete -f 100 -s 5 -l 300
# ==============================================================================

# Check if ANSI escape sequences are supported
supports_ansi() {
    [[ -t 1 ]] && [[ "$TERM" =~ xterm|screen|vt100|ansi|linux ]] && return 0
    return 1
}

# Default values
cdplast=""

# Parse command-line arguments
while getopts "k:o:f:s:l:h" opt; do
    case $opt in
        k) kdfile="$OPTARG" ;;
        o) outfile1="$OPTARG" ;;
        f) cdpin="$OPTARG" ;;
        s) step="$OPTARG" ;;
        l) cdplast="$OPTARG" ;;
        h)
            grep '^#' "$0" | head -n 20
            exit 0
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$kdfile" || -z "$outfile1" || -z "$cdpin" || -z "$step" ]]; then
    echo "Error: Missing required arguments."
    grep '^#' "$0" | head -n 20
    exit 1
fi

if [[ ! -f "$kdfile" || ! -f "$outfile1" ]]; then
    echo "Error: One or both input files do not exist!"
    exit 1
fi

# Function: Process the input filename and extract numeric suffix if available
process_filename() {
    local filename=$1
    local default_prefix=$2

    local base_name=$(basename "$filename")

    if [[ "$base_name" =~ ^(.*)_complete([0-9]+)(\..*)?$ ]]; then
        local prefix="${BASH_REMATCH[1]}"
        local number="${BASH_REMATCH[2]}"
        base_name="${prefix}_${number}"
    else
        base_name="${default_prefix}_"
    fi

    echo "$base_name"
}

kddata_output=$(process_filename "$kdfile" "kd.data")
outfile1_output=$(process_filename "$outfile1" "outfile1")

echo "Processing KD.DATA: $kdfile -> $kddata_output"
echo "Processing DATAOUT: $outfile1 -> $outfile1_output"

# Function: Display animated progress while a background job is running
show_progress() {
    local pid=$1
    local label=$2
    local delay=0.2
    local spin_chars=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0

    printf "%s: " "$label"

    if supports_ansi; then
        while ps -p $pid >/dev/null; do
            printf "\e[36m%s\e[0m" "${spin_chars[i]}"
            sleep $delay
            printf "\b"
            i=$(( (i+1) % ${#spin_chars[@]} ))
        done
        printf "\e[32m✓\e[0m\n"
    else
        while ps -p $pid >/dev/null; do
            printf "."
            sleep $delay
        done
        printf "✓\n"
    fi
}

# Function: Get file size (not currently used, kept for future use)
get_file_size() {
    if [[ -f "$1" ]]; then
        du -b "$1" | awk '{print $1}'
    else
        echo 0
    fi
}

echo

# Start background process for KD.DATA
(
sushw <"$kdfile" key=trid a=1 b=0 | \
suchw key1=dt key2=d1 b=1000 | \
suwind key=cdp min="$cdpin" max="$cdplast" | \
suwind j="$step" key=cdp >"$kddata_output"
) & pid1=$!

# Start background process for outfile1
(
sushw <"$outfile1" key=trid a=1 b=0 | \
suchw key1=dt key2=d1 b=1000 | \
suwind key=cdp min="$cdpin" max="$cdplast" | \
suwind j="$step" key=cdp >"$outfile1_output"
) & pid2=$!

# Show progress for both processes
show_progress $pid1 "Processing KD.DATA"
show_progress $pid2 "Processing DATAOUT"

echo -e "\nThe files '$kddata_output' and '$outfile1_output' have been created successfully."
exit 0
