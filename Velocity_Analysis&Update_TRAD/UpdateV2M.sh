#!/bin/bash
# =============================================================================
# Marine Seismic Velocity Model Update
# Version: 5.1 (Enhanced File Validation)
# Author: Lining YANG, CNR-ISMAR Bologna
# Date: 2025-07-04 20:00
# 
# Note:
#   The original version of the script is:
#    - https://github.com/utinivella/ISTRICI/blob/main/TRAD_V1/UPDATEvelocity2marinedata_detail
#
# Description: 
#   Comprehensive workflow for updating marine seismic velocity models
#   Combines Fortran for complex computations and Shell for efficient workflow
#   Automatic compilation and installation with intelligent caching
#
# Key Features:
#   - Single-script deployment
#   - Automatic Fortran compiler installation
#   - Smart compilation caching
#   - Hybrid performance optimization
#   - Comprehensive error handling
#   - Water bottom file validation
#
# This script should be used after ./VelocityAnalysis.sh
# Usage: ./UpdateV2M.sh
# =============================================================================

# -----------------------------------------------------------------------------
# Initialization and Configuration
# -----------------------------------------------------------------------------

# Set script name and version
SCRIPT_NAME="UpdateV2M.sh"
VERSION="5.1"
AUTHOR="Lining YANG CNR-ISMAR Bologna"

# Display header
echo "================================================================"
echo "$SCRIPT_NAME - Marine Seismic Velocity Model Updater"
echo "Version: $VERSION | Author: $AUTHOR"
echo "================================================================"

# -----------------------------------------------------------------------------
# Function: Install Fortran Compiler
# -----------------------------------------------------------------------------
install_fortran_compiler() {
    echo "===== Fortran Compiler Check ====="
    
    # Check if compiler already exists
    if command -v gfortran >/dev/null 2>&1; then
        echo "Fortran compiler found: $(gfortran --version | head -n1)"
        return 0
    fi
    
    echo "Fortran compiler not found. Installing..."
    
    # Detect OS and install appropriate compiler
    if [ -f /etc/redhat-release ]; then
        echo "Installing on RedHat-based system"
        sudo yum install -y gcc-gfortran
    elif [ -f /etc/debian_version ]; then
        echo "Installing on Debian-based system"
        sudo apt-get update
        sudo apt-get install -y gfortran
    elif [ "$(uname)" == "Darwin" ]; then
        echo "Installing on macOS"
        brew install gcc
    else
        echo "ERROR: Unsupported operating system"
        echo "Please install gfortran manually"
        exit 1
    fi
    
    # Verify installation
    if ! command -v gfortran >/dev/null 2>&1; then
        echo "ERROR: Fortran compiler installation failed"
        exit 1
    fi
    
    echo "Successfully installed: $(gfortran --version | head -n1)"
}


# -----------------------------------------------------------------------------
# Function: Compile Embedded Fortran Program (Fixed Format)
# -----------------------------------------------------------------------------
compile_embedded_fortran() {
    local program=$1
    local source_code=$2
    local source_hash=$(echo "$source_code" | sha256sum | cut -d' ' -f1)
    
    # Check if binary exists and matches current code
    if [ -f "./$program" ] && [ -f "./${program}.hash" ]; then
        local stored_hash=$(cat "./${program}.hash")
        if [ "$stored_hash" == "$source_hash" ]; then
            echo "Using existing binary: $program (code hash matches)"
            return 0
        else
            echo "Source code changed. Recompiling $program..."
            rm -f "./$program"
        fi
    fi
    
    echo "===== Compiling $program ====="
    
    # Use .f extension for fixed-form Fortran
    local source_file="${program}.f"
    echo "$source_code" > "$source_file"
    
    # Compile with fixed-form option and show warnings
    gfortran -O3 -ffixed-form -Wall -Wextra -o "$program" "$source_file"
    
    # Check compilation result
    if [ $? -ne 0 ] || [ ! -f "./$program" ]; then
        echo "ERROR: Failed to compile $program"
        echo "Source file preserved for debugging: $source_file"
        echo "Please check the Fortran source code for errors"
        exit 1
    fi
    
    # Store source hash for future reference
    echo "$source_hash" > "./${program}.hash"
    echo "Successfully compiled $program"
    
    # Cleanup source file (optional)
    # rm -f "$source_file"
}

# -----------------------------------------------------------------------------
# Function: Run Residual Gridding with File Validation
# -----------------------------------------------------------------------------
run_residual_gridding() {
    echo "===== Residual Velocity Gridding ====="
    
    # Define default water bottom file (Seafloor)
    DEFAULT_WATER_FILE="horizonZ_seafloor.dat"
    echo "Default water bottom file: $DEFAULT_WATER_FILE"
    
    # User interaction
    read -p "Press Enter to use default or enter new filename: " user_file
    
    # Check if user provided a file name
    if [ -z "$user_file" ]; then
        # Press Enter without input, use default file
        WATER_FILE="$DEFAULT_WATER_FILE"
    else
        # User provided a file name
        WATER_FILE="$user_file"
    fi
    
    # Validate existence of water bottom file (seafloor)
    if [ ! -f "$WATER_FILE" ]; then
        echo "ERROR: Water bottom file '$WATER_FILE' does not exist"
        
        # Provide options to retry or exit
        read -p "Retry (R) or Exit (E)? " choice
        case "$choice" in
            [Rr]* )
                # Retry by calling the function again
                run_residual_gridding
                return $?
                ;;
            * )
                echo "Processing aborted"
                exit 1
                ;;
        esac
    fi
    
    echo "Using water bottom file: $WATER_FILE"
       
    # establish temporary input file for Fortran program
    echo "$WATER_FILE" > water_input.txt
    
    # Compile the Fortran program for residual gridding
    ./residual_gridding < water_input.txt
    
    # Check if the Fortran program ran successfully
    local exit_code=$?
    
    # Delete temporary input file
    rm -f water_input.txt
    
    if [ $exit_code -ne 0 ]; then
        echo "ERROR: Residual gridding failed"
        exit 1
    fi
    
    echo "Created gridded residual velocity: velres.dat"
}

# -----------------------------------------------------------------------------
# Function: Velocity Model Addition (Shell implementation)
# -----------------------------------------------------------------------------
add_velocity_models() {
    echo "===== Velocity Model Addition ====="
    
    # Validate input files
    if [ ! -f "velres.dat" ] || [ ! -f "vfile.a" ] || [ ! -f "v.par" ]; then
        echo "ERROR: Required files missing:"
        [ ! -f "velres.dat" ] && echo "  - velres.dat"
        [ ! -f "vfile.a" ] && echo "  - vfile.a"
        [ ! -f "v.par" ] && echo "  - v.par"
        return 1
    fi
    
    # Read grid parameters - support both single-line and multi-line formats
    params=($(cat v.par))
    
    # Check if we have enough parameters
    if [ ${#params[@]} -lt 9 ]; then
        echo "ERROR: v.par must contain at least 9 values (found ${#params[@]})"
        echo "File contents:"
        cat v.par
        return 1
    fi
    
    # Assign parameters
    nz=${params[0]}
    dz=${params[1]}
    fz=${params[2]}
    nx=${params[3]}
    dx=${params[4]}
    fx=${params[5]}
    ncdpmin=${params[6]}
    ncdpmax=${params[7]}
    ncdp=${params[8]}
    
    # Debug output (can be removed after testing)
    echo "DEBUG: Parameters from v.par:"
    echo "  nz=$nz, dz=$dz, fz=$fz"
    echo "  nx=$nx, dx=$dx, fx=$fx"
    echo "  ncdpmin=$ncdpmin, ncdpmax=$ncdpmax, ncdp=$ncdp"
    
    # Validate numerical parameters
    if ! [[ "$nz" =~ ^[0-9]+$ ]] || [ "$nz" -eq 0 ]; then
        echo "ERROR: Invalid nz value: $nz"
        return 1
    fi
    
    if ! [[ "$nx" =~ ^[0-9]+$ ]] || [ "$nx" -eq 0 ]; then
        echo "ERROR: Invalid nx value: $nx"
        return 1
    fi
    
    # Calculate expected number of points
    total_points=$((nx * nz))
    echo "Grid dimensions: ${nx}x${nz} = $total_points points"
    
    # Verify file sizes
    velres_lines=$(wc -l < velres.dat)
    vfile_lines=$(wc -l < vfile.a)
    
    if [ $velres_lines -ne $total_points ]; then
        echo "ERROR: velres.dat size mismatch"
        echo "  Expected: $total_points lines"
        echo "  Actual: $velres_lines lines"
        return 1
    fi
    
    if [ $vfile_lines -ne $total_points ]; then
        echo "ERROR: vfile.a size mismatch"
        echo "  Expected: $total_points lines"
        echo "  Actual: $vfile_lines lines"
        return 1
    fi
    
    # Perform addition with precision control
    echo "Adding velocity models..."
    start_time=$(date +%s.%N)
    
    paste vfile.a velres.dat | awk -v total=$total_points '
    BEGIN {
        count = 0
        step = int(total/20)
        if (step == 0) step = 1  # Avoid division by zero
        print "0% completed" > "/dev/stderr"
    }
    {
        count++
        if (count % step == 0) {
            progress = int(count/total*100)
            printf "\rProcessing: %d%% completed", progress > "/dev/stderr"
            system("") # Flush output buffer
        }
        printf "%.8f\n", $1 + $2
    }
    END {
        printf "\rProcessing: 100%% completed\n" > "/dev/stderr"
    }' > vfile.updated
    
    # Calculate processing time
    end_time=$(date +%s.%N)
    elapsed=$(echo "$end_time - $start_time" | bc -l)
    points_per_sec=$(echo "scale=2; $total_points / $elapsed" | bc)
    
    echo "Addition completed in ${elapsed}s (${points_per_sec} points/sec)"
    echo "Created updated velocity model: vfile.updated"
}

# -----------------------------------------------------------------------------
# Embedded Fortran Code: Residual Velocity Gridding
# -----------------------------------------------------------------------------
FORT_GRIDDING_CODE='
! =============================================================================
! Residual Velocity Gridding for Marine Seismic Data
!
! Purpose: Converts residual picks to regular grid with water bottom correction
! Inputs:
!   - residuotot.dat: Residual picks data
!   - v.par: Grid parameters
!   - Water bottom file: User-provided bathymetry
! Outputs:
!   - velres.dat: Gridded residual velocity
! Original Author: Umberta Tinivella, OGS, Udine, Italy
! https://github.com/Dai411/ISTRICI-OGS/blob/main/TRAD_V1/faivelres2marinedata.f
! Modified by: Lining YANG, CNR-ISMAR Bologna
! =============================================================================
! Revise interbedded Fortran code to fixed format
      program faivelres
      real, allocatable :: res(:,:,:), resint(:,:)
      character filewater*80
      integer :: nvalido = 0  ! Initialize nvalido New add

      print*, " Provide the name of the water bottom file:"
      read(*,"(a80)") filewater

      open(60,file=filewater)

      open(10,file="residuotot.dat")
      open(12,file="v.par")
      read(12,*) nz
      read(12,*) ndz
      read(12,*) nfz
      read(12,*) nx
      read(12,*) ndx
      read(12,*) nfx
      read(12,*) ncdpmin
      read(12,*) ncdpmax
      read(12,*) ndcdp
      close(12)

      allocate(res(nx,100,4))
      allocate(resint(nx,nz))

10    read(10,*,end=99) nc
      do i=1,nc
         read(10,*) cdp,z,r,xlam
         ncdp=int(cdp)
         ni=(ncdp-nfx)/ndx+1
         res(ni,i,1)=z
         res(ni,i,2)=r
         res(ni,i,3)=xlam
         res(ni,i,4)=nc 
      enddo
      goto 10
99    close(10)
       
      nmin=(ncdpmin-nfx)/ndx+1
      nmax=(ncdpmax-nfx)/ndx+1
      nstep=ndcdp/ndx 

      do i=nmin,nmax,nstep
         do j=1,nz
            z=nfz+ndz*(j-1)

c        Exclude a CIG
          if(abs(res(i,1,3)-999.0).lt.1e-5) then
             resint(i,j)=999
             goto 20
          endif

          do k=1,int(res(i,1,4))

             if(z.le.res(i,k,1).and.k.eq.1) then
                resint(i,j)=res(i,k,3)
                goto 20
             endif

             if(z.gt.res(i,k,1).and.k.ne.int(res(i,1,4)).and.
     $          z.le.res(i,k+1,1)) then
                xm=(res(i,k+1,3)-res(i,k,3))/(res(i,k+1,1)-res(i,k,1))
                xq=res(i,k,3)-xm*res(i,k,1)
                resint(i,j)=xm*z+xq
                goto 20
             endif

             if(k.eq.int(res(i,1,4))) then
                resint(i,j)=res(i,k,3)
                goto 20
             endif

          enddo
20        continue
         enddo
      enddo

c     End of vertical interpolation
c     Check excluded CIGs
c     Fix first and last
      if(resint(nmin,1).eq.999) then
         do k=nmin+nstep,nmax,nstep
            if(resint(k,1).ne.999) then
               do j=1,nz        
                  resint(nmin,j)=resint(k,j)
               enddo
               goto 88
            endif           
         enddo
      endif

88    if(resint(nmax,1).eq.999) then
         do k=nmax-nstep,nmin,-nstep       
            if(resint(k,1).ne.999) then
               do j=1,nz
                  resint(nmax,j)=resint(k,j)
               enddo
               goto 77 
            endif
         enddo
      endif

c     Fix other 999 values
77    do i=nmin,nmax,nstep
          x=nfx+(i-1)*ndx
         ! if(resint(i,1).eq.999) then ! Old version
         if(abs(resint(i,1) - 999.0) < 1e-5) then  ! New version 
            do k=i+nstep,nmax,nstep          
               ! if(resint(k,1).ne.999) then
               if(abs(resint(k,1) - 999.0) > 1e-5) then  ! New version
                  nvalido=k
                  goto 66
               endif
            enddo

66          do j=1,nz
               z=nfz+(j-1)*ndz
               xm=(resint(i-nstep,j)-resint(nvalido,j))/
     $             ((nvalido-i+nstep)*ndx)
               xq=resint(i-nstep,j)-xm*(nfx+(i-nstep)*ndx)
               resint(i,j)=xm*x+xq
            enddo
         endif
      enddo

      do j=1,nz
         z=nfz+(j-1)*ndz
         do i=1,nx
            x=nfx+(i-1)*ndx
         
            if(i.le.nmin) then
               resint(i,j)=resint(nmin,j)
               goto 30
            endif

            if(i.ge.nmax) then
               resint(i,j)=resint(nmax,j)
               goto 30
            endif

            nk=((i-nmin)/nstep)*nstep+nmin      

            xm=(resint(nk+nstep,j)-resint(nk,j))/(nstep*ndx)
            xq=resint(nk,j)-xm*(nfx+(nk-1)*ndx)
            resint(i,j)=xm*x+xq

30          continue
         enddo
      enddo

c     Finished interpolation of analyzed CIPs

      open(50,file="velres.dat")
      do i=1,nx
         read(60,*) xxx,zwater
         do j=1,nz
            if(z.le.zwater) resint(i,j)=0.0
            write(50,*) resint(i,j)
         enddo
      enddo
      close(50)
      close(60)

      stop
      end
'

# -----------------------------------------------------------------------------
# Main Processing Workflow
# -----------------------------------------------------------------------------

# Step 1: Verify and install dependencies
install_fortran_compiler

# Step 2: Compile complex gridding program
compile_embedded_fortran "residual_gridding" "$FORT_GRIDDING_CODE"

# Step 3: User parameter verification
echo "===== Parameter Verification ====="
echo "Verify parameters in v.par:"
echo "  - nz: Number of depth samples"
echo "  - dz: Depth sampling interval"
echo "  - fz: Starting depth"
echo "  - nx: Number of x-position samples"
echo "  - dx: X sampling interval"
echo "  - fx: Starting x-position"
echo "  - cdpmin: Starting CDP"
echo "  - cdpmax: Ending CDP"
echo "  - dcdp: CDP step"
echo
read -p "Review and update v.par if needed. Press Enter to continue..."

# Step 4: Residual velocity gridding with water bottom file validation
run_residual_gridding

# Step 5: Convert to binary format
echo "===== Binary Conversion ====="
a2b < velres.dat n1=1 > velres.bin
echo "Created binary residual velocity: velres.bin"

# Step 6: Visualization (optional)
echo "===== Residual Velocity Visualization ====="
echo "Displaying residual velocity model - Close window to continue..."
ximage < velres.bin par=par_velres legend=1 title="Residual Velocity Model" &

# Step 7: Update velocity model
echo "===== Velocity Model Update ====="
add_velocity_models
if [ $? -ne 0 ]; then
    echo "ERROR: Velocity model update failed"
    exit 1
fi

# Step 8: Create final binary model
echo "===== Final Velocity Model Creation ====="
a2b < vfile.updated n1=1 > vfile_updated.bin
cp vfile_updated.bin vfile
echo "Created final velocity model: vfile"

# Step 9: Cleanup temporary files
echo "===== Cleanup ====="
rm -f vfile.a *.tmp
echo "Removed temporary files"

# -----------------------------------------------------------------------------
# Final Report
# -----------------------------------------------------------------------------
echo "================================================================"
echo "MARINE VELOCITY UPDATE COMPLETED SUCCESSFULLY"
echo "================================================================"
echo "Processing Summary:"
echo "  - Complex gridding: Fortran (optimized performance)"
echo "  - Velocity addition: Shell (efficient processing)"
echo
echo "Output Files:"
echo "  vfile              : Final velocity model (binary)"
echo "  vfile_updated.bin  : Updated velocity model (binary)"
echo "  vfile.updated      : Updated velocity model (ASCII)"
echo "  velres.bin         : Residual velocity model (binary)"
echo "  velres.dat         : Residual velocity model (ASCII)"
echo
echo "Next Steps:"
echo "  1. Validate velocity model with seismic data"
echo "  2. Use updated model for depth migration"
echo "  3. Iterate process if needed"
echo "================================================================"

exit 0
