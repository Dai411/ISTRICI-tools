#!/bin/bash
# ============================================================================ #
# Tool: Conduct Kirchhoff Migration 
# Author: Lining YANG @CNR-ISMAR, Bologna
# License: BSD 3-Clause License
# Last Modified: 2025-11-15 22:30
#
# Description:
#    This script conduct the 2 Dimensional Pre-stack Krichhoff Depth Migration 
#    from a processed SU (Seismic Unix) data with a provided velocity model. 
#    The main output data is also in SU format, with migrated z-domain traces. 
#    if the velocity anlaysis is needed (set 'npv>0'), the additional output  
#    contains extra amplitude. 
#
# Usage: 
#    chmod +x PerformPSDM.sh
#    ./PerformPSDM.sh
#
# Requirements:
#    - Key SU tools: unif2, rayt2d, sukdmig2d
#    - Optional SU tools: sudivcor (optional), sustack
#
# Suggestion:
#    Read the tutorial documents for the key SU tools in understanding how key
#    parameters shoud be set and manually changed for depth migration. Type 
#    the above tools command to see the information.
#
# Note:
#    - Memory requirements is about:			
#    	 = [ns*nxt*nzt+noff*nxo*nzo+4*nr*nzt+5*nxt*nzt+npa*(2*ns*nxt*nzt
#      +noff*nxo*nzo+4*nxt*nzt)]*4 bytes				
#      where nr = 1+min(nxt*dxt,0.5*offmax+aperx)/dxo. 
#    - The real used memory can be checked by calculating the tota lvolume of 
#      midlle files: input_unif, pvfile, csfile, tvfile, tfile
#    - The current Migration can only utilized single-core. The nulti-core 
#      Migration scripts is listed in this folder.   
#
# Original version:
#    - https://github.com/Dai411/ISTRICI-OGS/blob/main/TRAD_V1/PerformPSDM
# ============================================================================ #
set -e
set -u

# ============================================================================ #
# STAGE0: Read User's inputs and grid parameters
# ============================================================================ #
echo ">>> STAGE 0: SET PARAMETERS"
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
echo "Suggest greater or you may encounter failure in allocating memroy"
read ntr

echo "What do you want to name the output files of current migration"
read VERSION
echo "The output stacked SU files will be named with the "${VERSION}""
outputsu="stackPSDM_${VERSION}.su"
outputsu_no="stackPSDM_${VERSION}_no1000"

# ============================================================================ #
# STAGE0： Or you can hard-core it
# ============================================================================ #
#inputsu="../MEDOC9_compart_mute100.su"
#vfile="vfile_m0_c1.52k"

## Output files names
#VERSION="l0_mute100"
#outputsu="stackPSDM_${VERSION}.su"
#outputsu_no="stackPSDM_${VERSION}_no1000"
## Sample parameters
#nt=1626
#dt=0.004
## Velocity model parameters (grid sizes)
#nz=251
#dz=20
#fz=0
#nx=1201
#dx=25
#fx=65000

# Ray trace parameters (shot parameters)
#fs=65000
#ns=601
#ds=50

# Migration Parameters, Channels, check by surange<inputsu
#off0=-1552
#doff=25
#noff=55
#dxm=12.5
#offmax=1552
#ntr=28000

## Velocity model file parameters
#xini=65000
#xfin=95000

# ============================================================================ #
# STAGE 1: Pre-processing: Set grid, generate vfile, ray tracing, amplitude correction(optional) 
# You can change the parameters but before change, please check the tutorial documents
# ============================================================================ #
echo ">>> STAGE 1: Pre-processing..."
echo "--> Generating 2D uniform velocity model..."
echo $xini 0 >input_unif
echo $xfin 0 >>input_unif
echo 1.0 -99999 >>input_unif
unif2 < input_unif > pvfile  ninf=0 npmax=5000 nz=$nz \
 dz=$dz fz=$fz nx=$nx dx=$dx fx=$fx v00=1
echo "   - maximum number of points on interfaces is $npmax"

echo "--> Performing 2D ray tracing..."
rayt2d <"$vfile" nt=$nt dt=$dt fz=$fz nz=$nz dz=$dz fx=$fx nx=$nx dx=$dx aperx=10000 \
 fxo=$fx nxo=$nx dxo=$dx fzo=$fz nzo=$nz dzo=$dz fxs=$fs nxs=$ns dxs=$ds \
 fa=-90 na=91 \
 verbose=1 npv=1 tfile=tfile pvfile=pvfile csfile=csfile tvfile=tvfile
echo "   - the ray tracing aperature in x-direction is $aperx"
echo "   - the first take-off angle of rays (degrees) is $fa"
echo "   - the number of rays is $na"

# Amplitude correction is optional. If not pleae keep "cp "$inputsu" input_cor.su" and comment others
echo "--> Applying amplitude correction..."
sudivcor < "$inputsu" trms=0.0 vrms=1500 > input_cor.su
# cp "$inputsu" input_cor.su

# ============================================================================ #
# STAGE 2: Parallel Migration on a GLOBAL Grid
# The default migration lateral aperture is: 0.5*nxt*dxt
# The default migration angle aperature from vertical is 60
# ============================================================================ #
echo ">>> STAGE 2: Performing Migration..."
sukdmig2d < input_cor.su offmax=$offmax dxm=$dxm >kd.data_complete fzt=$fz nzt=$nz dzt=$dz fxt=$fx nxt=$nx dxt=$dx\
 aperx=10000 angmax=90 \
 fs=$fs ns=$ns ds=$ds ntr=$ntr off0=$off0 noff=$noff doff=$doff ttfile=tfile mtr=100\
 verbose=1 npv=1 tvfile=tvfile csfile=csfile outfile1=outfile1_complete
echo "   - the migration lateral aperature is $aperx "
echo "   - the	migration angle aperature from vertical is $angmax"

# ============================================================================ #
# STAGE 3: Merging, Sorting Results, Final Stacking, and Cleanup
# ============================================================================ #
suwind < kd.data_complete | sustack > $outputsu
suwind < kd.data_complete key=offset min=-1000 | sustack > $outputsu_no

echo ">>> Migration outputs:"
echo "    - kd.data_complete   (prestack depth migrated gathers)"
echo "    - outfile1_complete  (auxiliary output)"
echo "    - ${outputsu}        (stacked PSDM section)"
echo "    - ${outputsu_no}     (stacked only near offset)"

echo "--> Cleaning up calculation temporary files..."  
rm -f input_unif pvfile csfile tvfile
rm -f input_cor.su
rm -f tfile

echo ">>> PSDM processing completed successfully!"
echo "--- The input SU file is [$inputsu]"
echo "--- The input velocity model (vfile) is [$vfile]"
echo ">>>>>>>> Wish you a great result! <<<<<<<<"

exit 0
