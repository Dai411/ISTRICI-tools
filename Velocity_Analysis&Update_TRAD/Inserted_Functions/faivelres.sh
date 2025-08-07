# -----------------------------------------------------------------------------
# Compile Embedded Fortran Program (faivelres)
# -----------------------------------------------------------------------------
# =============================================================================
# Embedded Fortran Program: faivelres
#
# Purpose:
#   Interpolates residual velocity picks (from residuotot.dat) onto a regular
#   grid defined by v.par_v, producing a gridded residual velocity field
#   (velres.dat) for subsequent model updating.
#
# Inputs:
#   - residuotot.dat : Residual picks for all CDPs (ASCII)
#   - v.par_v        : Grid parameters (ASCII, 9 lines: nz, dz, fz, nx, dx, fx, cdpmin, cdpmax, dcdp)
#
# Outputs:
#   - velres.dat     : Gridded residual velocity (ASCII, nz*nx lines)
#
# Notes:
#   - No water bottom (seafloor) constraint is applied.
#   - The Fortran code is embedded and auto-compiled by the script.
#   - Original Author: Umberta Tinivella, OGS, Udine, Italy
# https://github.com/Dai411/ISTRICI-OGS/blob/main/TRAD_V1/faivelres_dettaglio.f
#   - Modified by: Lining YANG, CNR-ISMAR Bologna
# =============================================================================
FORT_FAIVELRES_CODE=$(cat <<'EOF'
    program faivelres
    integer, parameter :: maxpicks = 100  ! Maximum picks per CDP
    real, allocatable :: res(:,:,:), resint(:,:)
    integer :: nz, dz, fz, nx, dx, fx, cdpmin, cdpmax, dcdp
    integer :: i, j, k, ni, ncdp, nmin, nmax, nstep, nvalido, nc
    real :: cdp, z, r, xlam, x, xm, xq

    ! Read grid parameters
    open(12, file='v.par_v')
    read(12, *) nz
    read(12, *) dz
    read(12, *) fz
    read(12, *) nx
    read(12, *) dx
    read(12, *) fx
    read(12, *) cdpmin
    read(12, *) cdpmax
    read(12, *) dcdp
    close(12)

    ! Allocate arrays
    allocate(res(nx, maxpicks, 4))
    allocate(resint(nx, nz))
    res = 0.0
    resint = 0.0

    ! Read residual picks
    open(10, file='residuotot.dat')
10  read(10, *, end=99) nc
    do i = 1, nc
        read(10, *) cdp, z, r, xlam
        ncdp = int(cdp)
        ni = (ncdp - fx) / dx + 1
        if (ni >= 1 .and. ni <= nx .and. i <= maxpicks) then
            res(ni, i, 1) = z
            res(ni, i, 2) = r
            res(ni, i, 3) = xlam
            res(ni, i, 4) = real(nc)
        else
            print *, "Warning: Index out of bounds - ni:", ni, "i:", i
        endif
    enddo
    goto 10
99  close(10)

    ! Calculate index ranges
    nmin = (cdpmin - fx) / dx + 1
    nmax = (cdpmax - fx) / dx + 1
    nstep = dcdp / dx

    ! Vertical interpolation
    do i = nmin, nmax, nstep
        do j = 1, nz
            z = fz + dz * (j - 1)  ! Check the name of vaiables
            
            ! Skip if no picks for this CDP (marked by 999)
            if (res(i, 1, 3) == 999) then
                resint(i, j) = 999
                cycle
            endif
            
            do k = 1, int(res(i, 1, 4))
                if (z <= res(i, k, 1) .and. k == 1) then
                    resint(i, j) = res(i, k, 3)
                    exit
                endif
                
                if (z > res(i, k, 1) .and. k /= int(res(i, 1, 4)) .and. &
                    z <= res(i, k+1, 1)) then
                    xm = (res(i, k+1, 3) - res(i, k, 3)) / &
                         (res(i, k+1, 1) - res(i, k, 1))
                    xq = res(i, k, 3) - xm * res(i, k, 1)
                    resint(i, j) = xm * z + xq
                    exit
                endif
                
                if (k == int(res(i, 1, 4))) then
                    resint(i, j) = res(i, k, 3)
                    exit
                endif
            enddo
        enddo
    enddo

    ! Handle missing data (999) - part 1: fix first and last CDPs
    if (resint(nmin, 1) == 999) then
        do k = nmin + nstep, nmax, nstep
            if (resint(k, 1) /= 999) then
                do j = 1, nz
                    resint(nmin, j) = resint(k, j)
                enddo
                exit
            endif
        enddo
    endif

    if (resint(nmax, 1) == 999) then
        do k = nmax - nstep, nmin, -nstep
            if (resint(k, 1) /= 999) then
                do j = 1, nz
                    resint(nmax, j) = resint(k, j)
                enddo
                exit
            endif
        enddo
    endif

    ! Handle missing data (999) - part 2: fix intermediate CDPs
    do i = nmin, nmax, nstep
        if (resint(i, 1) == 999) then
            ! Find next valid CDP to the right
            do k = i + nstep, nmax, nstep
                if (resint(k, 1) /= 999) then
                    nvalido = k
                    exit
                endif
            enddo
            
            ! Linear interpolation in x-direction
            do j = 1, nz
                x = fx + (i - 1) * dx
                xm = (resint(i - nstep, j) - resint(nvalido, j)) / &
                     ((nvalido - i + nstep) * dx)
                xq = resint(i - nstep, j) - xm * (fx + (i - nstep - 1) * dx)
                resint(i, j) = xm * x + xq
            enddo
        endif
    enddo

    ! Horizontal interpolation for all CDP indices
    do j = 1, nz
        do i = 1, nx
            x = fx + (i - 1) * dx
            
            ! Extrapolate for i <= nmin
            if (i <= nmin) then
                resint(i, j) = 0.0  ! Original code used 0.0
                cycle
            endif
            
            ! Extrapolate for i >= nmax
            if (i >= nmax) then
                resint(i, j) = 0.0  ! Original code used 0.0
                cycle
            endif
            
            ! Find the step index for current i
            nk = nmin + ((i - nmin) / nstep) * nstep
            if (nk < nmin) nk = nmin
            if (nk >= nmax) nk = nmax - nstep
            
            ! Linear interpolation between nk and nk + nstep
            xm = (resint(nk + nstep, j) - resint(nk, j)) / (nstep * dx)
            xq = resint(nk, j) - xm * (fx + (nk - 1) * dx)
            resint(i, j) = xm * x + xq
        enddo
    enddo

    ! Write results
    open(50, file='velres.dat')
    do i = 1, nx
        do j = 1, nz
            write(50, *) resint(i, j)
        enddo
    enddo
    close(50)
    
    deallocate(res, resint)
    print *, "Successfully generated velres.dat"
end program
EOF
)

# -----------------------------------------------------------------------------
# Compile Embedded Fortran Program (faivelres)
# Compared to the original, this is a more modern Fortran style
# .f90 is the preferred extension for modern Fortran code
# .f90 files are free-form, allowing for better readability and maintainability 
# -----------------------------------------------------------------------------
compile_embedded_faivelres() {
    local program="faivelres"
    local source_code="$FORT_FAIVELRES_CODE"
    local source_hash=$(echo "$source_code" | sha256sum | cut -d' ' -f1)
    if [ -f "./$program" ] && [ -f "./${program}.hash" ]; then
        local stored_hash=$(cat "./${program}.hash")
        if [ "$stored_hash" == "$source_hash" ]; then
            log info "Using existing binary: $program (code hash matches)"
            return 0
        else
            log info "Source code changed. Recompiling $program..."
            rm -f "./$program"
        fi
    fi
    log info "Compiling $program (embedded Fortran)..."
    local source_file="${program}.f90" 
    echo "$source_code" > "$source_file"
    #gfortran -O3 -ffixed-form -o "$program" "$source_file" #Old style
    gfortran -O3 -free -o "$program" "$source_file"

    if [ $? -ne 0 ] || [ ! -f "./$program" ]; then
        log error "Failed to compile $program"
        log error "Source file preserved for debugging: $source_file"
        exit 1
    fi
    echo "$source_hash" > "./${program}.hash"
    log info "Successfully compiled $program"
}
