#!/bin/bash
# ==============================================================================
# CIG extraction script
# Version:   2.0 
# Author:    Lining YANG, CNR-ISMAR Bologna
# Date:      2025-07-05 20:00
# Modified:  2025-07-15
# License:   BSD-3-Clause
# ==============================================================================
# Note:
#    The original version of this script is:
#     - https://github.com/utinivella/ISTRICI/blob/main/TRAD_V1/CIGextraction
#
# Description: Extracts CDP traces from seismic data files and creates
#              output files with simplified names. Supports progress animation.
#
# Usage:
#   ./CIG_extract.sh -f <first_cdp> -s <step> [-k <kdfile>] [-o <outfile1>] [-l <last_cdp>]
#
# Parameters:
#   -f  First CDP to extract (required)
#   -s  CDP step interval (required)
#   -k  Path to the 'kd.data_complete' file (optional, defaults to 'kd.data_complete')
#   -o  Path to the 'outfile1_complete' file (optional, defaults to 'outfile1_complete')
#   -l  Last CDP to extract (optional)
#
# Example:
#   ./CIG_extract.sh -f 1000 -s 500 
#   ./CIG_extract.sh -k custom_kd.data -o custom_out.data -f 1000 -s 500 -l 3000
# ==============================================================================

# Check if ANSI escape sequences are supported
supports_ansi() {
    [[ -t 1 ]] && [[ "$TERM" =~ xterm|screen|vt100|ansi|linux ]] && return 0
    return 1
}

# Default values
cdplast=""
kdfile="kd.data_complete"
outfile1="outfile1_complete"
using_default_k=true
using_default_o=true

# Parse command-line arguments
while getopts "k:o:f:s:l:h" opt; do
    case $opt in
        k) 
            kdfile="$OPTARG"
            using_default_k=false
            ;;
        o) 
            outfile1="$OPTARG"
            using_default_o=false
            ;;
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
if [[ -z "$cdpin" || -z "$step" ]]; then
    echo "Error: Missing required arguments -f and/or -s."
    grep '^#' "$0" | head -n 20
    exit 1
fi

# Enhanced file existence checks with helpful messages
error_occurred=false

# Check KD.DATA file
if [[ ! -f "$kdfile" ]]; then
    if [[ "$using_default_k" == true ]]; then
        echo "Error: Default KD.DATA file '$kdfile' not found." >&2
        echo "       Please specify a valid file using the -k parameter." >&2
    else
        echo "Error: Specified KD.DATA file '$kdfile' not found." >&2
    fi
    error_occurred=true
fi

# Check outfile1 file
if [[ ! -f "$outfile1" ]]; then
    if [[ "$using_default_o" == true ]]; then
        echo "Error: Default outfile1 file '$outfile1' not found." >&2
        echo "       Please specify a valid file using the -o parameter." >&2
    else
        echo "Error: Specified outfile1 file '$outfile1' not found." >&2
    fi
    error_occurred=true
fi

# Exit if any files are missing
if [[ "$error_occurred" == true ]]; then
    exit 1
fi

# Function: Process the input filename and extract numeric suffix if available
process_filename() {
    local filename=$1
    local default_prefix=$2

    local base_name=$(basename "$filename")

    # Special cases for known filenames
    if [[ "$base_name" == "kd.data_complete" ]]; then
        echo "kd.data"
        return
    elif [[ "$base_name" == "outfile1_complete" ]]; then
        echo "outfile1"
        return
    fi
    
    # Remove the file extension if it exists
    if [[ "$base_name" =~ ^(.*)_complete(_?.+)$ ]]; then
        local prefix="${BASH_REMATCH[1]}"
        local suffix="${BASH_REMATCH[2]}"
        base_name="${prefix}${suffix}"
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
