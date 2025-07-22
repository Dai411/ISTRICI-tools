#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_vfile.py - Velocity Field Visualization Tool with Horizon Plotting

Author: Lining YANG @ CNR-ISMAR, BOLOGNA, ITALY
Date: 2025-05-30
Last Modified: 2025-07-22
License: BSD-3-Clause

Description:
    This script visualizes velocity field data (binary float32 format) with optional horizon overlay,
    featuring the following capabilities:
      1. Binary velocity field visualization with configurable colormaps
      2. Interactive horizon plotting with customizable display names
      3. Multiple horizon support with automatic color differentiation
      4. Keyboard-controlled colormap switching
      5. Flexible coordinate system configuration
      6. Detailed data validation and error handling

    Velocity data is assumed to be Fortran-order (column-major) with dimensions (nz, nx).
    Horizon files should be ASCII text with two columns (x, depth).

CLI Usage Examples:
    # Interactive mode with prompts
    python3 plot_vfile.py
    
    # Direct execution with parameters
    python3 plot_vfile.py --nx 701 --nz 321 --dx 100 --dz 25 --vfile vfile
    python3 plot_vfile.py --horizons horizon1.dat horizon2.dat --horizon-names "Seafloor" "Basement"
    python3 plot_vfile.py --no-interactive --xflip --cmap viridis

Interactive Features:
    - Press 'r' to cycle through RGB colormaps (viridis, plasma, inferno, magma, cividis)
    - Press 'h' to cycle through HSV colormaps (hsv, rainbow, jet, nipy_spectral, gist_rainbow)
    - Interactive horizon addition during runtime
    - Optional x-axis flipping

Visualization Features:
    - Automatic velocity range scaling (1000-10000 m/s)
    - Multiple horizon plotting with distinct colors
    - Customizable horizon display names
    - Grid overlay for better spatial reference
"""

import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
import sys

# Colormap definitions
rgb_cmaps = ['viridis', 'plasma', 'inferno', 'magma', 'cividis']
hsv_cmaps = ['hsv', 'rainbow', 'jet', 'nipy_spectral', 'gist_rainbow']

def parse_arguments():
    """Parse command line arguments with proper interactive mode detection"""
    parser = argparse.ArgumentParser(description='Velocity field visualization')
    
    # Grid parameters with defaults matching interactive prompts
    parser.add_argument('--nx', type=int, default=None)
    parser.add_argument('--nz', type=int, default=None)
    parser.add_argument('--dx', type=int, default=None) 
    parser.add_argument('--dz', type=int, default=None)
    
    # File parameters
    parser.add_argument('--vfile', type=str, default=None)
    parser.add_argument('--horizons', nargs='*', default=None)
    parser.add_argument('--horizon-names', nargs='*', default=None)
    
    # Display options
    parser.add_argument('--xflip', action='store_true')
    parser.add_argument('--cmap', type=str, default='hsv')
    
    args = parser.parse_args()
    
    # Determine if we're in interactive mode (no CLI params provided)
    args.interactive = all(v is None or v == [] for v in [
        args.nx, args.nz, args.dx, args.dz,
        args.vfile, args.horizons, args.horizon_names
    ])
    
    return args

def prompt_for_parameters():
    """Interactive prompt for required parameters"""
    print("Velocity Field Visualization - Interactive Mode")
    print("--------------------------------------------")
    
    params = {
        'nx': int(input("Horizontal sampling (nx) [701]: ") or 701),
        'nz': int(input("Vertical sampling (nz) [321]: ") or 321),
        'dx': int(input("Horizontal interval (dx) [100]: ") or 100),
        'dz': int(input("Vertical interval (dz) [25]: ") or 25),
        'vfile': input("Velocity file [vfile]: ") or "vfile",
        'horizons': [],
        'horizon_names': []
    }
    
    if input("Plot horizons? (y/n) [n]: ").strip().lower() == 'y':
        while True:
            hfile = input("Horizon file (or 'done'): ").strip()
            if hfile.lower() == 'done':
                break
            params['horizons'].append(hfile)
            name = input(f"Display name for {hfile} [{os.path.splitext(hfile)[0]}]: ")
            params['horizon_names'].append(name or os.path.splitext(hfile)[0])
    
    params['xflip'] = input("Flip x-axis? (y/n) [n]: ").strip().lower() == 'y'
    
    return params

def main():
    args = parse_arguments()
    
    # Get parameters either from CLI or interactive prompts
    if args.interactive:
        params = prompt_for_parameters()
    else:
        params = {
            'nx': args.nx or 701,
            'nz': args.nz or 321,
            'dx': args.dx or 100,
            'dz': args.dz or 25,
            'vfile': args.vfile or 'vfile',
            'horizons': args.horizons or [],
            'horizon_names': args.horizon_names or [],
            'xflip': args.xflip
        }
    
    try:
        # Load and validate data
        with open(params['vfile'], 'rb') as f:
            data = np.fromfile(f, dtype=np.float32, count=params['nx']*params['nz'])
            if data.size != params['nx']*params['nz']:
                raise ValueError(f"Data size mismatch: expected {params['nx']*params['nz']}, got {data.size}")
            vel = np.reshape(data, (params['nz'], params['nx']), order='F')

        # Create plot
        x = np.arange(params['nx']) * params['dx']
        z = np.arange(params['nz']) * params['dz']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        im = ax.imshow(vel, extent=[x[0], x[-1], z[-1], z[0]], 
                      cmap=args.cmap, aspect='auto')
        im.set_clim(1000, 10000)

        def format_coord(x_val, y_val):
            x_idx = int(np.clip((x_val - x[0]) / args.dx, 0, args.nx - 1))
            y_idx = int(np.clip((y_val - z[0]) / args.dz, 0, args.nz - 1))
            val = vel[y_idx, x_idx]
            return f"x={x_val:.1f} m, z={y_val:.1f} m, v={val:.1f} m/s"  

        ax.format_coord = format_coord 
        fig.text(0.02, 0.01, "Press 'r' for RGB colormaps, 'h' for HSV colormaps", fontsize=9, color='gray')

        fig.colorbar(im, label='Velocity (m/s)')
        ax.set(xlabel='Distance (m)', ylabel='Depth (m)', 
              title='Velocity Field (m/s)')
        ax.grid(True)

        # Plot horizons if any
        if params['horizons']:
            colors = ['black', 'red', 'blue', 'green', 'cyan', 'magenta', 'yellow']
            for i, (hfile, hname) in enumerate(zip(params['horizons'], params['horizon_names'])):
                try:
                    hdata = np.loadtxt(hfile)
                    ax.plot(hdata[:,0], hdata[:,1], 
                           color=colors[i % len(colors)],
                           linewidth=2,
                           label=hname)
                except Exception as e:
                    print(f"Error plotting {hfile}: {e}")
            ax.legend()

        # Apply x-flip if requested
        if params['xflip']:
            ax.invert_xaxis()

        # Set up keyboard controls
        def on_key(event):
            if event.key.lower() == 'r':
                cmaps = rgb_cmaps
            elif event.key.lower() == 'h':
                cmaps = hsv_cmaps
            else:
                return
            
            current = im.get_cmap().name
            idx = (cmaps.index(current) + 1) % len(cmaps) if current in cmaps else 0
            im.set_cmap(cmaps[idx])
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect('key_press_event', on_key)
        
        # Show keyboard help in interactive mode
        if args.interactive:
            print("\nKeyboard controls:")
            print("  r: Cycle RGB colormaps")
            print("  h: Cycle HSV colormaps")

        plt.show()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
