#!/bin/bash
# =============================================================================
# Mini Tool: Display r-parameter Analysis for a Specific CDP Gather
# Author: Lining YANG, CNR-ISMAR Bologna
# Version: 1.0
# License: BSD 3-Clause License
# Date: 2025-07-08 19：47
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
#   Input SU File: The input seismic data file in SU format.
#   --save       : Optional flag to automatically save picking results without prompting.
#
# Example:
#   ./show_r_parameter.sh 10000 kd.data --save
#
# Requirements:
#   - SU (Seismic Unix) tools: suwind, surelan, suchw, suximage, supsimage
#   - A graphical environment with X11 support for visualization.
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

# Check arguments
if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    usage
fi

CDP=$1
INPUT_FILE=$2
SAVE_MODE=${3:-"no"}

# r-scan parameters
NR=51         # Number of r-values
DR=0.01       # r sampling interval
FR=-0.25      # Starting r-value
DZRATIO=2     # Depth ratio for scanning

# Create temp file
TMPFILE=$(mktemp /tmp/tmp_cdp_${CDP}_XXXXXX.su)

# Trap to clean up on exit
trap "rm -f $TMPFILE" EXIT

# Step 1: Extract CDP gather
echo "[INFO] Extracting CDP=$CDP from $INPUT_FILE ..."
suwind key=cdp min=$CDP max=$CDP < "$INPUT_FILE" > "$TMPFILE"

if [ ! -s "$TMPFILE" ]; then
    echo "[ERROR] No data found for CDP=$CDP in $INPUT_FILE."
    exit 1
fi

# Step 2: Generate r-scan
echo "[INFO] Performing r-scan analysis..."
OUTFILE="r_scan_${CDP}.su"
surelan < "$TMPFILE" dzratio=$DZRATIO nr=$NR dr=$DR fr=$FR | \
    suchw key1=dt key2=d1 b=1000 > "$OUTFILE"

# Step 3: Display summary
END_R=$(echo "scale=3; $FR + $NR * $DR" | bc)

echo
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

# Step 4: Display with supsimage
suximage < "$OUTFILE" perc=98 \
    title="r-scan for CDP $CDP" \
    label1="Depth (m)" label2="r-parameter" \
    grid1=1 grid2=1 \
    legend=1 cmap=hsv2 \
    f2=$FR d2=$DR

    # f2=$FR set the start of the r-parameter; d2=$DR set the step of the r-parameter

# Step 5: Save picks if requested
if [ "$SAVE_MODE" = "--save" ]; then
    PICKFILE="r_picks_$CDP.txt"
    echo "[INFO] Saving r-parameter picks to $PICKFILE..."
    suximage < "$OUTFILE" perc=98 mpicks="$PICKFILE" \
        title="Pick r-parameter for CDP $CDP" cmap=hsv2 legend=1
    echo "[INFO] Picks saved to $PICKFILE"
else
    echo
    read -p "Do you want to save picks interactively? (y/n): " SAVE_ANSWER
    if [ "$SAVE_ANSWER" = "y" ]; then
        PICKFILE="r_picks_$CDP.txt"
        suximage < "$OUTFILE" perc=98 mpicks="$PICKFILE" \
            title="Pick r-parameter for CDP $CDP" cmap=hsv2 legend=1
        echo "[INFO] Picks saved to $PICKFILE"
    else
        echo "[INFO] Picks not saved."
    fi
fi

exit 0
