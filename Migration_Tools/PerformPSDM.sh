#!/bin/bash
# =========================================
# Tool: Conduct Kirchhoff Migration 
# Author: Lining YANG @CNR-ISMAR, Bologna
# License: BSD 3-Clause License
# Last Modified: 2025-11-13 20:30
#
# Description:
#    This script conduct the 2 Dimensional Pre-stack Krichhoff Depth migration  
#    from a processed SU (Seismic Unix) data with a provided velocity model. The 
#    main output data is a migrated z-domain traces. if the velocity anlaysis is  
#    needed (set 'npv>0'), the additional output contains extra amplitude.  
#    
#
# 
# Original version:
#    - https://github.com/Dai411/ISTRICI-OGS/blob/main/TRAD_V1/PerformPSDM
#
#

set -e
set -u

#########################################
#Input files: *.su and vfile
#########################################
inputsu="../MEDOC9_compart_mute100.su"
vfile="vfile_m0_c1.52k"

#########################################
#Output files names
#########################################
VERSION="l0_mute100"
outputsu="stackPSDM_${VERSION}.su"
outputsu_no="stackPSDM_${VERSION}_no1000"

#########################################
# Sample parameters
#########################################
nt=1626
dt=0.004

#########################################
# Velocity model parameters (grid sizes)
#########################################
nz=251
dz=20
fz=0
nx=1201
dx=25
fx=65000

#########################################
# Ray trace parameters (shot parameters)
#########################################
#ns=2547
#ds=50
fs=65000
ns=601
ds=50

#########################################
# Migration Parameters
# Channels 1 - ?
# check by surange<inputsu
#########################################
off0=-1552
doff=25
noff=55
dxm=12.5
offmax=1552
ntr=28000

# --------------------------------------
# Generating uniform velocity model
# --------------------------------------
xini=65000
xfin=95000
echo $xini 0 >input_unif
echo $xfin 0 >>input_unif
echo 1.0 -99999 >>input_unif

unif2 < input_unif > pvfile  ninf=0 npmax=5000 nz=$nz \
 dz=$dz fz=$fz nx=$nx dx=$dx fx=$fx v00=1

# --------------------------------------
# Ray trace
# --------------------------------------
rayt2d <"$vfile" nt=$nt dt=$dt fz=$fz nz=$nz dz=$dz fx=$fx nx=$nx dx=$dx aperx=10000 \
 fxo=$fx nxo=$nx dxo=$dx fzo=$fz nzo=$nz dzo=$dz fxs=$fs nxs=$ns dxs=$ds \
 fa=-90 na=91 \
 verbose=1 npv=1 tfile=tfile pvfile=pvfile csfile=csfile tvfile=tvfile

# --------------------------------------
# Amplitude correction
# --------------------------------------
sudivcor < "$inputsu" trms=0.0 vrms=1510 > input_cor.su
# cp "$inputsu" input_cor.su

# --------------------------------------
# Kirchhoff PSDM
# --------------------------------------
sukdmig2d < input_cor.su offmax=$offmax dxm=$dxm >kd.data_complete fzt=$fz nzt=$nz dzt=$dz fxt=$fx nxt=$nx dxt=$dx\
 aperx=10000 angmax=90 \
 fs=$fs ns=$ns ds=$ds ntr=$ntr off0=$off0 noff=$noff doff=$doff ttfile=tfile mtr=100\
 verbose=1 npv=1 tvfile=tvfile csfile=csfile outfile1=outfile1_complete

# --------------------------------------
# Stack CIG images (with near-offset)
# --------------------------------------
suwind < kd.data_complete | sustack > $outputsu
suwind < kd.data_complete key=offset min=-1000 | sustack > $outputsu_no

echo ">>> Migration outputs:"
echo "    kd.data_complete   (prestack depth migrated gathers)"
echo "    outfile1_complete  (auxiliary output)"
echo "    stackPSDM.su       (stacked PSDM section)"
echo "    stackPSDM_no.su    (near offset)"

# -----------------------------
# Clean tmp files
# -----------------------------
rm -f input_unif pvfile csfile tvfile
rm -f input_cor.su
rm -f tfile

echo ">>> PSDM processing completed successfully!"
echo "--- The input SU file is [$inputsu]"
echo "--- The input velocity model (vfile) is [$vfile]"

exit 0
