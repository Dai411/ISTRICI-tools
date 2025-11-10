#!/bin/bash
# ==============================================================================
# Final Production-Grade PSDM Script with Overlap Zone & User-Corrected Merging
# Author: Lining YANG @ CNR-ISMAR, Bologna, Italy
# Date: 05 Spetember 2025
# License: BSD-3-Clause
# 
# Description:
#       This script performs a robust Pre-Stack Depth Migration (PSDM) on seismic
# data, allowing for multiple cores in migration. This script was developed from
# the original version provided by Umberta Tinivella and Michela Giustiniani @OGS:
# https://github.com/utinivella/ISTRICI/blob/main/TRAD_V1/PerformPSDM
#
# Key features include:
# - Comprehensive cleanup to ensure idempotent runs.
# - Robust data splitting with a two-pass correction method.
# - Parallel processing with controlled concurrency.
# - Use of a global imaging grid for all parallel jobs to ensure consistency.
# - Merging and sorting of outputs with user-verified correctness.
# - Final stacking to produce a clean PSDM section.
# ==============================================================================
set -e
set -u

###################################################
# User inputs and grid parameters
# If you are familar, you can hard-core parameters 
###################################################
echo "Which is your input SU data?"
read inputsu
echo "Which is your velocity model (Please check the size)?"
read vfile

echo "Please insert the limit coordinates of the model"
echo "xini="
read xini
echo "xfin="
read xfin

echo "What are time Sampling Parameters for ray tracing:nt, dt(s)?"
echo "nt*dt = depth in TWTs" 
echo "nt="
read nt
echo "dt(in seconds)="
read dt

echo "What are the Depth & Spatial Grid Parameters for vfile?"
echo "nz,dz,fz?"
read nz
read dz
read fz
echo ""
echo "nx,dx,fx?"
read nx 
read dx 
read fx
echo ""

echo "What are source & Receiver Parameters (for Kirchhoff Migration)?"
echo "Suggestion: ns=nx/2 ds=2*dx fs=fx"
read fs
read ns 
read ds
echo ""

# ----------------------------------------------------------------
# Migration Parameters: These value should be available from the Report
# Please have a think what have been updated during process
# ----------------------------------------------------------------
echo "Kirchhoff Migration Parameters:"
echo "Please check if you have thinned raw data!"
echo "Absolute offset maximum:"
read offmax
echo "Sampling interval of mid points (trace header d2):"
read dxm
echo "Far-offset increment in CIG output (in metre with the sign):"
read off0
echo "Offset increments in CIG output (in metre with the sign):"
read doff
echo "Number of offsets in CIG output:"
read noff
echo "Maximumnumber of input traces to be migrated:"
echo "Note:equal or greater than the number trace in the seismic data"
echo "I suggest a bit greater or you may encounter failure in allocating memroy"
read ntr

# --- Overlap Zone Parameters ---
echo "To ensure continuity across chunks, we define an overlap zone:"
echo "Suggestion: if dx=200, cdp=50 means 10 kilometer overlapped region"
echo "What is the size for overlapped region do you want?"
echo "OVERLAP_CDPS= "
read OVERLAP_CDPS

# ==============================================================================
# STAGE 0: Initial Cleanup (make the script idempotent)
# ==============================================================================
echo ">>> STAGE 0: Initial cleanup to ensure a fresh and repeatable run..."
# Clean up all intermmediate files
rm -f job_*.tmp outfile1_*.tmp job_*.stderr.log
rm -f input_cor.su tfile pvfile csfile tvfile input_unif
# Clean up unsaved (not renamed) output files
rm -f kd.data_complete outfile1_complete stackPSDM.su
rm -f kd.data_complete_unsorted outfile1_complete_unsorted
rm -f parallel_migration.log
# clean up tmp files
rm -rf temp_split_files
echo "--> Cleanup complete. Starting a fresh run."

# ==============================================================================
# STAGE 1: Pre-processing (Set grid, generate vfile, ray tracing, amplitude correction)
# Required Seismic Unix components: unif2, rayt2d, sudivcor
# ==============================================================================
echo ">>> STAGE 1: Pre-processing..."
echo "--> Generating 2D uniform velocity model..."

echo "$xini 0" > input_unif; echo "$xfin 0" >> input_unif; echo "1.0 -99999" >> input_unif
unif2 < input_unif > pvfile ninf=0 npmax=50000 nz=$nz dz=$dz fz=$fz nx=$nx dx=$dx fx=$fx v00=1

echo "--> Performing 2D ray tracing..."
rayt2d <"$vfile" nt=$nt dt=$dt fz=$fz nz=$nz dz=$dz fx=$fx nx=$nx dx=$dx aperx=5000 \
 fxo=$fx nxo=$nx dxo=$dx fzo=$fz nzo=$nz dzo=$dz fxs=$fs nxs=$ns dxs=$ds \
 verbose=1 npv=1 tfile=tfile pvfile=pvfile csfile=csfile tvfile=tvfile

echo "--> Applying amplitude correction..."
sudivcor < "$inputsu" trms=0.0 vrms=1507.5 > input_cor.su

# ==============================================================================
# STAGE 2: Robust Data Splitting with Two-Pass Correction
# Required Seismic Unix components: sugethw, suwind
# ==============================================================================
echo ">>> STAGE 2: Splitting input data robustly..."
SPLIT_DIR="temp_split_files"
mkdir -p $SPLIT_DIR
# ... the value of sugethw is double as surange ...
echo "--> Counting total traces in input file (with 2x correction)..."
RAW_LINE_COUNT=$(sugethw key=tracl < input_cor.su | wc -l)
if [ -z "$RAW_LINE_COUNT" ]; then RAW_LINE_COUNT=0; fi
ESTIMATED_TRACES=$(( RAW_LINE_COUNT / 2 ))
echo "--> Corrected estimated traces from headers: $ESTIMATED_TRACES"

if [ "$ESTIMATED_TRACES" -eq 0 ]; then
    echo "--> Warning: input_cor.su is empty. Creating empty split file list."
    # New empty file to indicate no splits
    touch ${SPLIT_DIR}/split_files.list
else
    # You can manually set how many cores you want to use
    # for splitting and later for parallel processing.
    NCORES=4
    #NCORES=%(nproc)d  # or set to the number of available processors
    TRACES_PER_JOB=$(( (ESTIMATED_TRACES + NCORES - 1) / NCORES ))
    echo "--> Aiming for $NCORES chunks of approx. $TRACES_PER_JOB traces each..."
    i=1
    while true; do
        TRACES_TO_SKIP=$(( (i - 1) * TRACES_PER_JOB ))
        OUTPUT_FILE="${SPLIT_DIR}/split_${i}.su"
        suwind < input_cor.su skip=$TRACES_TO_SKIP count=$TRACES_PER_JOB > "$OUTPUT_FILE" || true
        if [ ! -s "$OUTPUT_FILE" ]; then
            echo "--> Reached end of effective data. Deleting empty chunk ${i} and stopping."
            rm "$OUTPUT_FILE"
            break
        fi
        echo "--> Successfully created chunk ${i}."
        i=$((i + 1))
    done
fi

# ==============================================================================
# STAGE 3: Parallel Migration on a GLOBAL Grid
# Required Seismic Unix components: sukdmig2d
# ==============================================================================
echo ">>> STAGE 3: Processing chunks in parallel on a GLOBAL grid..."
SPLIT_FILES=$(ls ${SPLIT_DIR}/split_*.su 2>/dev/null)

if [ -z "$SPLIT_FILES" ]; then
    echo "--> No data chunks were created. Skipping migration."
else
    NCORES_TO_USE=$NCORES # Default Setting: equal to splitting cores
    #NCORES_TO_USE=4 # You can manually set this to control parallelism
    echo "--> Execution parallelism: Running up to $NCORES_TO_USE jobs simultaneously."

    for INPUT_CHUNK in $SPLIT_FILES; do
        # Control the number of concurrent jobs
        if (( $(jobs -p | wc -l) >= NCORES_TO_USE )); then
            wait -n
        fi
        
        JOB_NUM=$(basename "$INPUT_CHUNK" | sed 's/split_//;s/.su//')
        OUTPUT_JOB_TMP="job_${JOB_NUM}.tmp"
        OUTPUT_OUTFILE1_TMP="outfile1_${JOB_NUM}.tmp"
        OUTPUT_STDERR_LOG="job_${JOB_NUM}.stderr.log"

        echo "--> Submitting Migration Job ${JOB_NUM} for chunk ${INPUT_CHUNK}..."

        # Note: Using GLOBAL imaging grid parameters (fx, nx, dx) for all jobs

        {
        sukdmig2d < "$INPUT_CHUNK" \
            fxt=$fx nxt=$nx dxt=$dx \
            offmax=$offmax dxm=$dxm fzt=$fz nzt=$nz dzt=$dz \
            fs=$fs ns=$ns ds=$ds ntr=$ntr off0=$off0 noff=$noff doff=$doff \
            ttfile=tfile mtr=500 verbose=0 npv=1 tvfile=tvfile csfile=csfile \
            outfile1="$OUTPUT_OUTFILE1_TMP" > "$OUTPUT_JOB_TMP" 2> "$OUTPUT_STDERR_LOG"
	} &
    done

    # Wait for all background jobs to finish
    echo "--> All jobs submitted. Waiting for all jobs to complete..."
    wait
    echo "--> All jobs completed."
fi

# ==============================================================================
# STAGE 4: Merging, Sorting Results, Final Stacking, and Cleanup
# Required Seismic Unix components: susort, suwind, sustack
# ==============================================================================
echo ">>> STAGE 4: Merging, sorting results and cleaning up..."
echo "--> Cleaning up split files to free up disk space..."
rm -rf $SPLIT_DIR
echo "--> Cleaning up calculation temporary files..."  
rm -f input_unif pvfile csfile tvfile
rm -f input_cor.su
rm -f tfile

# --- Merge kd.data_complete ---
echo "--> Merging and sorting main output files..."
rm -f kd.data_complete_unsorted kd.data_complete
JOB_FILES=$(ls job_*.tmp 2>/dev/null)
if [ -n "$JOB_FILES" ]; then
    cat $JOB_FILES > kd.data_complete_unsorted
    susort < kd.data_complete_unsorted > kd.data_complete cdp
    rm -f kd.data_complete_unsorted
fi

# --- Merge outfile1_complete ---
echo "--> Merging and sorting auxiliary output files..."
rm -f outfile1_complete_unsorted outfile1_complete
OUTFILE1_FILES=$(ls outfile1_*.tmp 2>/dev/null)
if [ -n "$OUTFILE1_FILES" ]; then
    cat $OUTFILE1_FILES > outfile1_complete_unsorted
    susort < outfile1_complete_unsorted > outfile1_complete cdp
    rm -f outfile1_complete_unsorted
fi

# --- Final Stacking: Or we can stack only near offset traces ---
echo "--> Stacking..."
if [ -s "kd.data_complete" ]; then
    suwind < kd.data_complete | sustack > stackPSDM.su
    suwind < kd.data_complete key=offset min=0 max=1300 | sustack > stackPSDM_no.su
fi

echo ">>> Migration outputs:"
echo "    kd.data_complete   (prestack depth migrated gathers)"
echo "    outfile1_complete  (auxiliary output)"
echo "    stackPSDM.su       (stacked PSDM section)"
echo "    stackPSDM_no.su    (optional: stacked near-offset section)"

# --- Final Clean up ---
echo "--> Cleaning up remaining temporary files..."
rm -f job_*.tmp
rm -f outfile1_*.tmp
rm -f job_*.stderr.log

echo ">>> PSDM processing completed successfully!"
echo ">>>>>>>> Wish you a great result! <<<<<<<<"
exit 0
