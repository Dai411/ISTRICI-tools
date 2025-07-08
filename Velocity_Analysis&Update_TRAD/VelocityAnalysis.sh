#!/bin/bash
# =============================================================================
# Seismic Unix Residual Moveout Analysis Script
# Version: 4.0 (Pure Shell Implementation)
# Author: Lining YANG, CNR-ISMAR Bologna
# Date: 2025-07-01
# 
# Description: 
#   This script performs residual moveout analysis on seismic Common Image Gathers (CIGs).
#   It processes seismic data to estimate velocity perturbations and update velocity models.
#   The workflow includes:
#     - Parameter input (hardcoded in this version)
#     - CIG display and interactive r-parameter picking
#     - Data preparation for velocity analysis
#     - Residual moveout calculation
#     - Velocity model updating
# 
# Features:
#   - Pure shell implementation (no Fortran dependencies)
#   - Interactive visualization with SU (Seismic Unix)
#   - Comprehensive error checking
#   - Automated processing pipeline
#
# Usage:
#   ./seismic_velocity_analysis.sh
# =============================================================================
# Original Author: Umberta Tinivella, OGS, Udine, Italy
# https://github.com/Dai411/ISTRICI-OGS/blob/main/TRAD_V1/VELOCITANALISYS
# Modified by: Lining YANG, CNR-ISMAR Bologna
# The previous tool is a shell script combined with two Fortran .f scripts
# The Fortran script is transfered to shell functions in this version
# There is no apparent code performance after using shell fuctions here
#
# -----------------------------------------------------------------------------
# Initialize environment
# -----------------------------------------------------------------------------
echo "Starting Seismic Velocity Analysis"
echo "================================="

# Clean previous run files
rm -f mpick.dat deltap.txt
cp vfile vfile_old  # Backup original velocity file
b2a <vfile n1=1 >vfile.a # Convert binary to ASCII for easier processing
# vfile.a will be used for UpdateV2M.sh
# -----------------------------------------------------------------------------
# Set analysis parameters (hardcoded values)
# -----------------------------------------------------------------------------
# Migration and velocity grid parameters
echo "migration and velocity parameters:"
echo "nz,dz,fz?"
read nz # Number of depth samples
read dz # Depth sampling interval (m)
read fz # Starting depth (m)

echo "nx,dx,fx?"
read nx # Number of x-position samples
read dx # X sampling interval (m)
read fx # Starting x-position (m)

# Common Image Gather (CIG) parameters
echo "near offset (absolute value in m) in the CIGs (kd.data and outfile1)"
read absoff0    # Near offset (m) - abosulte value
echo "number of offsets in the CIGs"
read noff       # Number of offsets in the CIGs
echo "offset increment (absolute value) in the CIGs"
read doff       # Offset sampling interval (m)

# Velocity analysis parameters
echo "min, max and CIG step at which you want to performe the velocity analyis"
echo "Attention: the step must be a multiple of the step used in the CIGextraction!"
read cdpmin # Starting CDP
read cdpmax # Ending CDP
read dcdp   # CDP step

# Seismic data header parameters (from kd.data)
echo "insert the values: ns, d1 e d2 in the trace header of the kd.data"
echo "Obtained from the command $ surange<kd.data"
read nzmig  # Number of samples in trace
read dzmig  # Depth sampling in migrated data (m)
read d2mig  # Trace header parameter

# ========= Preset parameters for the analysis ========= 
# Parameters can be preset here, remeber to command above
#nz=321       
#dz=25        
#fz=0         
#nx=701       
#dx=100       
#fx=0         
#absoff0=3627 
#noff=138     
#doff=25      
#cdpmin=6000 
#cdpmax=65000 
#dcdp=500     
#nzmig=1601   
#dzmig=5      
#d2mig=50     
# ========================================================
echo "file v.par generated with the parameters: nz,dz,fz,nx,dx,fx,cdpmin,cdpmx,dcdp"
# Create velocity grid parameters file
# echo "$nz $dz $fz $nx $dx $fx $cdpmin $cdpmax $dcdp" > v.par # Data in a single line
printf "%s\n" "$nz" "$dz" "$fz" "$nx" "$dx" "$fx" "$cdpmin" "$cdpmax" "$dcdp" > v.par # Data in multiple lines
echo "v.par file created with the above parameters"
# -----------------------------------------------------------------------------
# Fixed parameters for r-parameter scanning
nr=51        # Number of r-parameters
dr=0.01      # r-parameter sampling interval
fr=-0.25     # Starting r-parameter value
dzratio=2    # Depth ratio for scanning

# Input/output files
input="kd.data"        # Input seismic data (SU format)
rpicks="res.p1"        # Temporary picks file

# -----------------------------------------------------------------------------
# Function: faicigpar - Replaces the Fortran program of the same name
# 
# Purpose: Processes pick data to generate CIG parameters
# Inputs: 
#   - nciclo.txt: Contains pick index and CDP number
#   - mpicks.txt: Contains depth and r-value picks
# Outputs:
#   - cig.txt: Formatted CIG parameters
# -----------------------------------------------------------------------------
faicigpar() {
    # Verify required input files exist
    if [[ ! -f "nciclo.txt" || ! -f "mpicks.txt" ]]; then
        echo "ERROR: [faicigpar] Required files (nciclo.txt, mpicks.txt) not found"
        exit 1
    fi
    
    # Read values from input files
    local nc=$(head -1 nciclo.txt)        # Pick index
    local ncdp=$(tail -1 nciclo.txt)      # CDP number
    
    # Validate pick index
    local total_picks=$(wc -l < mpicks.txt)
    if [[ $nc -le 0 || $nc -gt $total_picks ]]; then
        echo "ERROR: [faicigpar] Invalid pick index: $nc (valid range: 1-$total_picks)"
        exit 1
    fi
    
    # Read depth and r-value from the specified pick
    read -r z r < <(sed -n "${nc}p" mpicks.txt)
    
    # Format output parameters (preserving decimal precision)
    printf "cip=%d,%.4f,%.8f\n" "$ncdp" "$z" "$r" > cig.txt
    
    echo "Generated cig.txt for CDP $ncdp, pick $nc"
}

# -----------------------------------------------------------------------------
# Function: aggiungilambda - Replaces the Fortran program of the same name
# 
# Purpose: Combines pick data with velocity perturbations
# Inputs:
#   - numeropick.txt: CDP number and pick count
#   - mpicks.txt: Depth and r-value picks
#   - deltap.txt: Velocity perturbation values
# Outputs:
#   - residuo.txt: Residual data file
# -----------------------------------------------------------------------------
aggiungilambda() {
    # Verify required input files exist
    if [[ ! -f "numeropick.txt" || ! -f "mpicks.txt" || ! -f "deltap.txt" ]]; then
        echo "ERROR: [aggiungilambda] Required files not found"
        exit 1
    fi
    
    # Read CDP number and pick count
    IFS=',' read -r cdp npick < numeropick.txt
    
    # Validate pick count
    if ! [[ "$npick" =~ ^[0-9]+$ ]] || [[ $npick -le 0 ]]; then
        echo "ERROR: [aggiungilambda] Invalid pick count: $npick"
        exit 1
    fi
    
    # Check file consistency
    local mpick_lines=$(wc -l < mpicks.txt)
    local delta_lines=$(wc -l < deltap.txt)
    
    if [[ $npick -ne $mpick_lines || $npick -ne $delta_lines ]]; then
        echo "ERROR: [aggiungilambda] Line count mismatch:"
        echo "  Expected picks: $npick"
        echo "  mpicks.txt lines: $mpick_lines"
        echo "  deltap.txt lines: $delta_lines"
        exit 1
    fi
    
    # Create output file with pick count header
    echo "$npick" > residuo.txt
    
    # Process each pick
    for ((i=1; i<=npick; i++)); do
        # Read depth and r-value
        read -r z r < <(sed -n "${i}p" mpicks.txt)
        
        # Read delta value (velocity perturbation)
        local delta=$(sed -n "${i}p" deltap.txt)
        
        # Format output line (preserve decimal precision)
        printf "%d %.4f %.8f %.8f\n" "$cdp" "$z" "$r" "$delta" >> residuo.txt
    done
    
    echo "Generated residuo.txt with $npick records for CDP $cdp"
}

# -----------------------------------------------------------------------------
# Main Processing Loop
# -----------------------------------------------------------------------------
echo "Starting processing from CDP $cdpmin to $cdpmax (step $dcdp)"
rm -f picking_cig  # Remove previous picks file

cdp=$cdpmin
while [[ $cdp -le $cdpmax ]]; do
    echo "Processing CDP: $cdp"
    
    # ---------------------------------------------------------
    # Section 1: CIG Display and Interactive Picking
    # ---------------------------------------------------------
    pick_valid=false
    until $pick_valid; do
        # Extract current CDP data
        suwind key=cdp min=$cdp max=$cdp < "$input" > tmp.su
        
        # Display CIG gather
        echo "Displaying CIG gather for CDP $cdp"
        suxwigb < tmp.su perc=98 \
            label1="Depth (m)" label2="Offset (m)" \
            title="CIG $cdp" key=offset wbox=700 hbox=500 &
        
        # Create r-parameter scan data
        surelan < tmp.su dzratio=$dzratio nr=$nr dr=$dr fr=$fr | \
            suchw key1=dt key2=d1 b=1000 > filecigtot.su
        
        # Display r-scan and collect picks
        echo "Starting r-parameter scan - Pick reflections (right-click + 's')"
        suximage < filecigtot.su perc=97 f2=$fr d2=$dr \
            label1="Depth (m)" label2="r-parameter" \
            title="r-scan: CIP $cdp" \
            grid1=solid grid2=solid \
            mpicks="mpicks.$cdp" cmap=hsv2 wbox=700 hbox=1100 -N
        
        # Pause to allow user interaction
        read -p "Press Enter after picking is complete..."
        
        # Verify picks were made
        if [[ ! -s "mpicks.$cdp" ]]; then
            echo "WARNING: No picks saved for CDP $cdp"
            read -p "Retry picking? (y/n): " retry
            [[ "$retry" != "y" ]] && pick_valid=true
        else
            pick_valid=true
        fi
    done
    
    # ---------------------------------------------------------
    # Section 2: Prepare Pick Data
    # ---------------------------------------------------------
    # Save pick information
    echo -n "$cdp," >> picking_cig
    cat "mpicks.$cdp" >> picking_cig
    
    # Record number of picks
    num_picks=$(wc -l < "mpicks.$cdp")
    echo "$cdp,$num_picks" > numeropick.txt
    
    # Create CIG parameter file
    echo "cip=$cdp," > temp
    cat temp "mpicks.$cdp" > "$rpicks"
    sed "s/  /,/g" < "$rpicks" > cig.par
    cp cig.par "cig.par.$cdp"
    
    # Prepare correction data
    echo -n "$cdp " > corr
    sed "s/  / /g" < "mpicks.$cdp" >> corr
    awk '{print $3,$1}' corr >> mpick.dat
    cp "mpicks.$cdp" mpicks.txt  # For current CDP processing

    # ---------------------------------------------------------
    # Section 3: Prepare Input Data
    # ---------------------------------------------------------
    echo "Preparing input data for CDP $cdp"
    
    # Prepare CIG gather data
    suwind key=cdp min=$cdp max=$cdp < "$input" > dati_tmp0
    susort < dati_tmp0 -offset | sustrip > infile
    
    # Prepare reference migrated section
    suwind key=cdp min=$cdp max=$cdp < outfile1 > dati_tmp1
    susort < dati_tmp1 -offset | sustrip > afile
    
    # Clean temporary files
    rm -f dati_tmp0 dati_tmp1
    
    # ---------------------------------------------------------
    # Section 4: Velocity Analysis per Pick
    # ---------------------------------------------------------
    echo "Starting velocity analysis for $num_picks picks"

    # Initialize perturbation file
    > deltap.txt  # Create empty file

    # Process each pick
    for ((pick_idx=1; pick_idx<=num_picks; pick_idx++)); do
        pick_success=false
        while ! $pick_success; do
            echo "Processing pick $pick_idx/$num_picks"
            
            # Create pick index file
            echo $pick_idx > nciclo.txt
            echo $cdp >> nciclo.txt
            
            # Generate CIG parameters
            faicigpar
            sed "s/ //g" cig.txt > cig.par
            
            # Clean previous run files
            rm -f dfile dzfile deltap.$cdp deltap.tmp
            
            # Calculate depth derivatives
            dzdv < infile par=cig.par nx=1 nz=$nzmig fx=$cdp fz=$fz \
                dx=$d2mig dz=$dzmig afile=afile dfile=dfile \
                off0=$absoff0 noff=$noff doff=$doff nxw=0 nzw=0 > dzfile
            
            # Check dzdv execution
            if [[ $? -ne 0 || ! -s dfile ]]; then
                echo "ERROR: dzdv failed for CDP $cdp, pick $pick_idx"
                echo "Please re-pick for this CDP and pick index."
                read -p "Press Enter after re-picking (edit mpicks.$cdp as needed)..."
                continue
            fi
            
            # Estimate velocity perturbation
            velpert < dfile dzfile=dzfile ncip=1 noff=$noff moff=$noff > "deltap.$cdp"
            
            # Check velpert execution
            if [[ $? -ne 0 || ! -s "deltap.$cdp" ]]; then
                echo "ERROR: velpert failed for CDP $cdp, pick $pick_idx"
                echo "Please re-pick for this CDP and pick index."
                read -p "Press Enter after re-picking (edit mpicks.$cdp as needed)..."
                continue
            fi

            # --- extract delta values ---
            sed "2,3d" "deltap.$cdp" > deltap.tmp 
            awk '{print $6}' deltap.tmp >> deltap.txt
            # Check if the $6 colum is the value of delta v?

            # Clean intermediate files
            rm dzfile

            pick_success=true
        done
    done
    
    # ---------------------------------------------------------
    # Section 5: Velocity Model Update
    # ---------------------------------------------------------
    echo "Updating velocity model for CDP $cdp"
    
    # Clean temporary files
    rm -f infile afile
    
    # Combine results
    aggiungilambda
    
    # Archive results
    cp residuo.txt "residuo.$cdp"
    cat residuo.txt >> residuotot.dat
    rm -f deltap.txt
    
    # Clear temporary files 
    rm -f "mpicks.$cdp" "cig.par.$cdp" "residuo.$cdp" "deltap.$cdp" deltap.tmp
    rm -f dzfile dfile afile infile tmp.su filecigtot.su corr temp nciclo.txt mpicks.txt numeropick.txt cig.txt 
    rm -f res.p1

    # Move to next CDP
    cdp=$((cdp + dcdp))
    echo "Completed CDP $((cdp - dcdp)), moving to $cdp"
done

# -----------------------------------------------------------------------------
# Finalize Output
# -----------------------------------------------------------------------------
# Create velocity parameter file
echo "n1=$nz d1=$dz f2=$fx n2=$nx d2=$dx" > par_velres

echo "============================================="
echo "Velocity analysis completed successfully!"
echo "Processed CDPs: $cdpmin to $cdpmax"
echo "Output files:"
echo "  - vfile_old: Original velocity model backup"
echo "  - vfile.a: ASCII velocity model"
echo "  - residuotot.dat: Complete residual data"
echo "  - par_velres: Velocity grid parameters"
echo "  - picking_cig: All pick coordinates"
echo "  - cig.par.*: CIG parameters per CDP"
echo "  - residuo.*: Residual data per CDP (Deleted during cleanup)"
echo "============================================="

exit 0
