#!/usr/bin/env python3
# =============================================================================
# Fortran-style Velocity Model Substitution Tool
# Version: 1.1 (Added PNG export option)
# Author: Lining YANG, CNR-ISMAR Bologna
# Date: 2025-07-10 20:30
# Latest modified: 2025-07-10
# License: BSD-3-Clause
#
# Description:
#   Interactive tool for substituting velocity values in 2D seismic models
#   using horizon files as boundaries. Maintains Fortran binary format integrity.
#
# Core Functionality:
#   - Reads Fortran-order binary velocity models (nz × nx float32)
#   - Processes horizon files (x,z pairs) to define replacement zones
#   - Supports two replacement modes:
#     1. Single-horizon: Replace above or below horizon
#     2. Dual-horizon: Replace between horizons
#   - Generates difference maps and replacement statistics
#   - Optional PNG image export
#
# Strict Data Requirements:
#   - Velocity file: Must exactly match specified dimensions (nz*nx)
#   - Horizon files: Must contain at least 2 columns (x, z)
#
# Input Files:
#   Required:
#   - vfile (velocity.bin) : Binary velocity model (Fortran float32)
#   - horizonZ_[name].dat  : Horizon depth files (space/tab delimited)
#
# Interactive parameters::
#   - Press enter to use default values of choice in [ ] brackets
#
# Output Files:
#   - velocity_new.bin  : Substituted velocity model
#   - substitution.png  : Comparison plot (optional)
#
# Usage:
#   python3 vel_sub_horizon.py
#
# Python Dependencies:
#   - numpy >= 1.20
#   - matplotlib >= 3.5
# =============================================================================

import numpy as np
import matplotlib.pyplot as plt
import os

def read_velocity_file(filename, nx, nz):
    """Read binary velocity file (Fortran-order)"""
    try:
        with open(filename, 'rb') as f:
            data = np.fromfile(f, dtype=np.float32, count=nx * nz)
        if data.size != nx * nz:
            print(f"❌ Data size mismatch! Expected {nx*nz}, got {data.size}")
            return None
        return data.reshape((nz, nx), order='F')  # Fortran-order reshape
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def read_horizon_file(filename):
    """Read horizon depth file (x,z pairs)"""
    try:
        with open(filename, 'r') as f:
            lines = [line.strip().split() for line in f if line.strip()]
        x = [float(parts[0]) for parts in lines if len(parts) >= 2]
        z = [float(parts[1]) for parts in lines if len(parts) >= 2]
        return np.array(x), np.array(z)
    except Exception as e:
        print(f"Error reading horizon file: {e}")
        return None, None

def interpolate_horizon(x_horizon, z_horizon, nx, dx):
    """Interpolate horizon to all x positions"""
    x_full = np.arange(nx) * dx
    return np.interp(x_full, x_horizon, z_horizon)

def plot_comparison(original, substituted, dx, dz):
    """Generate comparison plots (original, substituted, difference)"""
    diff = substituted - original
    x = np.arange(original.shape[1]) * dx
    z = np.arange(original.shape[0]) * dz
    
    fig = plt.figure(figsize=(18, 5))
    
    # Original data plot
    plt.subplot(1, 3, 1)
    plt.imshow(original, extent=[x[0], x[-1], z[-1], z[0]], 
               cmap='jet', aspect='auto')
    plt.colorbar(label='Velocity (m/s)')
    plt.title('Original')
    plt.xlabel('Distance (m)')
    plt.ylabel('Depth (m)')
    
    # Substituted data plot
    plt.subplot(1, 3, 2)
    plt.imshow(substituted, extent=[x[0], x[-1], z[-1], z[0]], 
               cmap='jet', aspect='auto')
    plt.colorbar(label='Velocity (m/s)')
    plt.title('Substituted')
    plt.xlabel('Distance (m)')
    
    # Difference plot
    plt.subplot(1, 3, 3)
    vmax = np.max(np.abs(diff))
    plt.imshow(diff, extent=[x[0], x[-1], z[-1], z[0]], 
               cmap='bwr', aspect='auto', vmin=-vmax, vmax=vmax)
    plt.colorbar(label='Velocity Change (m/s)')
    plt.title('Difference')
    plt.xlabel('Distance (m)')
    
    plt.tight_layout()
    plt.show()
    return fig  # Return figure object for potential saving

def main():
    print("=== Horizon-based Velocity Substitution Tool ===")
    
    # 1. Read velocity file parameters
    nx = int(input("Enter nx (horizontal samples) [701]: ") or 701)
    nz = int(input("Enter nz (vertical samples) [321]: ") or 321)
    dx = float(input("Enter dx (horizontal spacing in m) [100.0]: ") or 100.0)
    dz = float(input("Enter dz (vertical spacing in m) [25.0]: ") or 25.0)
    
    # 2. Read velocity file
    while True:
        vfile = input("Enter velocity filename: ").strip()
        vel = read_velocity_file(vfile, nx, nz)
        if vel is not None:
            break
    
    # 3. Read horizon files
    num_horizons = int(input("Number of horizon files (1 or 2) [1]: ") or 1)
    horizons = []
    for i in range(num_horizons):
        while True:
            hfile = input(f"Horizon file {i+1}: ").strip()
            x, z = read_horizon_file(hfile)
            if x is not None:
                horizons.append((x, z))
                break
    
    # 4. Determine replacement area
    print("\nSelect replacement area:")
    if num_horizons == 1:
        choice = input("Replace (1) 0-horizon or (2) horizon-bottom? [1]: ") or "1"
        horizon_z = interpolate_horizon(horizons[0][0], horizons[0][1], nx, dx)
        
        mask = np.zeros_like(vel, dtype=bool)
        for ix in range(nx):
            z_idx = int(horizon_z[ix] / dz)
            if choice == "1":
                mask[:z_idx, ix] = True  # Fortran-order: z first
            else:
                mask[z_idx:, ix] = True
    else:
        # Area between two horizons
        h1_z = interpolate_horizon(horizons[0][0], horizons[0][1], nx, dx)
        h2_z = interpolate_horizon(horizons[1][0], horizons[1][1], nx, dx)
        
        mask = np.zeros_like(vel, dtype=bool)
        for ix in range(nx):
            z1 = int(min(h1_z[ix], h2_z[ix]) / dz)
            z2 = int(max(h1_z[ix], h2_z[ix]) / dz)
            mask[z1:z2, ix] = True
    
    # 5. Perform substitution
    new_vel = vel.copy()
    new_value = float(input("Enter new velocity value: "))
    new_vel[mask] = new_value
    
    # 6. Display results
    fig = plot_comparison(vel, new_vel, dx, dz)
    
    # 7. Save results
    save = input("Save velocity result? (Y/n) [y]: ").lower() or "y"
    if save == "y":
        default_out = os.path.splitext(vfile)[0] + "_new.bin"
        outfile = input(f"Output filename [{default_out}]: ").strip() or default_out
        
        #with open(outfile, 'wb') as f:
            # new_vel.astype(np.float32).tofile(f) # C-order
            # np.asfortranarray(new_vel).astype(np.float32).tofile(f) # C-order
        
        # Save in Fortran order
        with open(outfile, 'wb') as f:
            new_vel.T.astype(np.float32).tofile(f)  # Transpose to Fortran order
            # new_vel.ravel(order='F').astype(np.float32).tofile(f) # Should be equivalent
        print(f"Saved to {outfile} (Fortran-order preserved)")
    
    # 8. Optional PNG save
    save_png = input("Save plot as PNG? (y/N) [n]: ").strip().lower() or "n"
    if save_png == "y":
        default_png = os.path.splitext(vfile)[0] + "_comparison.png"
        png_file = input(f"PNG filename [{default_png}]: ").strip() or default_png
        fig.savefig(png_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {png_file}")

if __name__ == "__main__":
    main()
