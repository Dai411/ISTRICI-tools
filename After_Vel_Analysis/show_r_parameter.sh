#!/bin/bash
# =============================================================================
# Mini Tool: Display r-parameter Analysis for a Specific CDP Gather
# Author: Lining YANG, CNR-ISMAR Bologna
# Version: 1.2
# License: BSD 3-Clause License
# Date: 2025-07-08 19：47
# Last Modified: 2025-11-12 20:10
#
# Description:
#   This script extracts a specific Common Depth Point (CDP) gather from a seismic
#   SU (Seismic Unix) dataset, performs r-parameter scanning to analyze velocity
#   errors, and displays the results graphically using SU visualization tools.
#
#   The r-parameter scan helps identify velocity deviations by scanning through
#   different r-values (velocity perturbations) and highlighting energy focusing.
#   Bright spots in the output image indicate optimal r-values:
#     - r = 0 means the velocity is correctly estimated.
#     - r > 0 indicates velocity is too low and should be increased.
#     - r < 0 indicates velocity is too high and should be decreased.
#
# Usage:
#   ./show_r_parameter.sh [CDP] [Input SU File] [--save (optional)]
#
# Arguments:
#   CDP          : The Common Depth Point number to analyze (integer).
#   Input SU File: The input seismic data file in SU format. Default is "kd.data".
#   --save       : Optional flag to automatically save picking results without prompting.
#
# Example:
#   ./show_r_parameter.sh 10000 kd.data --save
#
# Requirements:
#   - SU (Seismic Unix) tools: suwind, surelan, suchw, suximage, supsimage
#   - A graphical environment with X11 support for visualization.
#
# Suggestion:
#    - Increase the parameter 'DZRATIO' can affect the presentation of energy concentration  
#    - Please type 'surelan' for notes in changing Optinal Parameters
#
# Notes:
#   - Run this script in a graphical terminal session.
#   - Avoid redirecting the script output to files to prevent binary data dumping.
#   - The script cleans up temporary files automatically on exit.
#
# Contact:
#   For issues or improvements, please contact li-ning.yang@outlook.com
# =============================================================================

set -euo pipefail

# Prevent binary data dumping if user redirects output or no X11
if [ ! -t 1 ]; then
    echo "[ERROR] This script should not be redirected to a file. Run it directly in terminal."
    exit 1
fi
if [ -z "${DISPLAY:-}" ]; then
    echo "[ERROR] No X11 DISPLAY found. Please run in a graphical terminal with X11 support."
    exit 1
fi

# Function: Show usage
usage() {
    echo "Usage: $0 [CDP] [Input SU File] [--save (optional)]"
    exit 1
}

# Function to check pick file
check_pickfile() {
    local pickfile=$1
    if [ -s "$pickfile" ]; then
        echo "[INFO] Picks saved to $pickfile"
        echo "Picked points:"
        cat "$pickfile"
    else
        echo "[WARNING] No valid picks were made"
        rm -f "$pickfile"
    fi
}

# Check arguments
if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    usage
fi

CDP=$1
INPUT_FILE=$2
SAVE_MODE=${3:-"no"}

# r-scan parameters
# Please check the description of 'surelan' for more information
# You can use the below default value to see the difference of semblance
# NR=51, DR=0.01, FR=-0.25, DZRATIO=5
NR=26         # Number of r-values
DR=0.02       # r sampling interval
FR=-0.25      # Starting r-value
DZRATIO=2     # Depth ratio for scanning

# Create temp files
TMPFILE=$(mktemp /tmp/tmp_cdp_${CDP}_XXXXXX.su)
OUTFILE="r_scan_${CDP}.su"
PICKFILE="r_picks_${CDP}.txt"

# Trap to clean up on exit
trap "rm -f $TMPFILE $OUTFILE" EXIT  # Don't auto-delete PICKFILE as it's user data

# Step 1: Extract CDP gather
echo "[INFO] Extracting CDP=$CDP from $INPUT_FILE ..."
suwind key=cdp min=$CDP max=$CDP < "$INPUT_FILE" > "$TMPFILE"

if [ ! -s "$TMPFILE" ]; then
    echo "[ERROR] No data found for CDP=$CDP in $INPUT_FILE."
    exit 1
fi

# Step 2: Generate CIG gather & r-scan
echo "[INFO] Displaying CIG gather for CDP $CDP"
suxwigb < "$TMPFILE" perc=98 \
    label1="Depth (m)" label2="Offset (m)" \
    title="CIG $CDP" key=offset wbox=700 hbox=1100 &

echo "[INFO] Performing r-scan analysis..."
surelan < "$TMPFILE" dzratio=$DZRATIO nr=$NR dr=$DR fr=$FR | \
    suchw key1=dt key2=d1 b=1000 > "$OUTFILE"

# Step 3: Display summary
END_R=$(echo "scale=3; $FR + $NR * $DR" | bc)

#echo
echo "=============================================="
echo "r-parameter Analysis for CDP: $CDP"
echo "----------------------------------------------"
echo "r-range: $FR to $END_R (step $DR)"
echo "Energy Focus Areas:"
echo "  - Bright spots indicate optimal r-values."
echo "  - r=0 means velocity is correct."
echo "  - r>0: velocity too low (increase needed)."
echo "  - r<0: velocity too high (decrease needed)."
echo "=============================================="

# Step 4: Display r-scan results
echo "[INFO] Displaying r-scan results..."
suximage < "$OUTFILE" perc=98 \
    title="r-scan for CDP $CDP" \
    label1="Depth (m)" label2="r-parameter" \
    grid1=solid grid2=solid \
    legend=1 cmap=hsv2 \
    wbox=700 hbox=1100 \
    f2=$FR d2=$DR &

# Step 5: Handle picking
if [ "$SAVE_MODE" = "--save" ]; then
    echo "[INFO] Saving r-parameter picks to $PICKFILE..."
    suximage < "$OUTFILE" perc=98 mpicks="$PICKFILE" \
        title="RIGHT-click to pick, MIDDLE-click to finish" cmap=hsv2 legend=1 \
        label1="Depth (m)" label2="r-parameter" \
        grid1=solid grid2=solid \
        wbox=700 hbox=1100
    check_pickfile "$PICKFILE"
else
    # New logic: Show both windows first, then ask after they close
    echo "[INFO] Display windows opened - interact with them first"
    echo "  - In r-scan window: RIGHT-click to pick, 's' to store temporarily"
    echo "  - Close both windows when done to proceed"

    # Wait for windows to close
    wait

    # Check if any picks were made (SU stores picks in memory before writing)
    if [[ -f "$PICKFILE" ]]; then
        echo
        read -p "Do you want to save the picks you made? (y/N): " SAVE_ANSWER
        if [[ "$SAVE_ANSWER" =~ ^[Yy]$ ]]; then
            echo "[INFO] Picks saved to $PICKFILE"
            echo "Picked points:"
            cat "$PICKFILE"
        else
            rm -f "$PICKFILE"
            echo "[INFO] Picks discarded"
        fi
    else
        echo "[INFO] No picks were made during this session"
    fi
fi

exit 0
