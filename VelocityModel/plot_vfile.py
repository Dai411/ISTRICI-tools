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

# Define available colormaps
rgb_cmaps = ['viridis', 'plasma', 'inferno', 'magma', 'cividis']
hsv_cmaps = ['hsv', 'rainbow', 'jet', 'nipy_spectral', 'gist_rainbow']

def parse_arguments():
    """Parse command line arguments for velocity field visualization
    
    Returns:
        argparse.Namespace: Parsed arguments with the following attributes:
            - nx: Horizontal sampling points (default: 701)
            - nz: Vertical sampling points (default: 321)
            - dx: Horizontal sampling interval in meters (default: 100)
            - dz: Vertical sampling interval in meters (default: 25)
            - vfile: Velocity field filename (default: 'vfile')
            - horizons: List of horizon files to plot (default: [])
            - horizon_names: Optional display names for horizons (default: [])
            - xflip: Flag to flip x-axis direction (default: False)
            - no_interactive: Flag to disable interactive prompts (default: False)
            - cmap: Initial colormap (default: 'hsv')
    """
    parser = argparse.ArgumentParser(description='Visualize velocity field with optional horizons')
    
    # Matrix parameters
    parser.add_argument('--nx', type=int, default=701, 
                       help='Horizontal sampling numbers (default: 701)')
    parser.add_argument('--nz', type=int, default=321,
                       help='Vertical sampling numbers (default: 321)')
    
    # Sampling intervals
    parser.add_argument('--dx', type=int, default=100,
                       help='Horizontal sampling interval in meters (default: 100)')
    parser.add_argument('--dz', type=int, default=25,
                       help='Vertical sampling interval in meters (default: 25)')
    
    # File parameters
    parser.add_argument('--vfile', type=str, default='vfile',
                       help='Velocity file name (default: vfile)')
    parser.add_argument('--horizons', nargs='*', default=[],
                       help='List of horizon files to plot')
    parser.add_argument('--horizon-names', nargs='*', default=[],
                       help='Optional display names for horizons')
    
    # Display options
    parser.add_argument('--xflip', action='store_true',
                       help='Flip x-axis direction')
    parser.add_argument('--no-interactive', action='store_true',
                       help='Disable interactive prompts')
    parser.add_argument('--cmap', type=str, default='hsv',
                       help='Initial colormap (default: hsv)')
    
    return parser.parse_args()

def load_horizon_data(horizon_files, horizon_names, no_interactive):
    """Load and process horizon data with interactive capabilities
    
    Args:
        horizon_files (list): Pre-loaded horizon filenames from CLI
        horizon_names (list): Corresponding display names
        no_interactive (bool): Flag to disable interactive prompts
    
    Returns:
        tuple: (list of horizon files, list of display names)
    """
    if not horizon_files:
        if no_interactive:
            return [], []
        plot_horizon = input("Do you want to plot horizon data? (y/n) [n]: ").strip().lower() or 'n'
        if plot_horizon != 'y':
            return [], []
        
        while True:
            horizon_file = input("📥 Please type horizon file name (no path, or 'done' to finish): ").strip()
            if horizon_file.lower() == 'done':
                if not horizon_files:
                    print("No horizon files added. Continuing without horizon data.")
                break
                
            try:
                horizon_data = np.loadtxt(horizon_file)
                if horizon_data.shape[1] != 2:
                    print(f"File '{horizon_file}' should have exactly 2 columns. Skipping this file.")
                    continue
                    
                horizon_files.append(horizon_file)
                if len(horizon_names) < len(horizon_files):
                    if no_interactive:
                        name = os.path.splitext(horizon_file)[0]
                        horizon_names.append(name)
                    else:
                        name = input(f"Enter display name for '{horizon_file}' (or press Enter to use file name): ").strip()
                        horizon_names.append(name if name else os.path.splitext(horizon_file)[0])
                
                if not no_interactive:
                    add_more = input("Add another horizon? (y/n): ").strip().lower()
                    if add_more != 'y':
                        break
                        
            except FileNotFoundError:
                print(f"Horizon file '{horizon_file}' not found! Please try again.")
            except Exception as e:
                print(f"Error reading horizon file: {e}. Please try again.")
    
    return horizon_files, horizon_names

def main():
    """Main function for velocity field visualization"""
    args = parse_arguments()
    
    # Load velocity data
    try:
        with open(args.vfile, 'rb') as f:
            data = np.fromfile(f, dtype=np.float32, count=args.nx * args.nz)
    except FileNotFoundError:
        print(f"Velocity file '{args.vfile}' not found!")
        return

    if data.size != args.nx * args.nz:
        print(f"Data size mismatch! Expected {args.nx * args.nz} values, got {data.size}")
        return

    # Process data
    vel = np.reshape(data, (args.nz, args.nx), order='F')
    x = np.arange(args.nx) * args.dx
    z = np.arange(args.nz) * args.dz

    # Load horizon data
    horizon_files, horizon_names = load_horizon_data(args.horizons, args.horizon_names, args.no_interactive)

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='w')
    im = ax.imshow(vel, extent=[x[0], x[-1], z[-1], z[0]], cmap=args.cmap, aspect='auto')
    im.set_clim(1000, 10000)

    # Custom format for mouse hover coordinates
    def format_coord(x_val, y_val):
        """Format coordinates for mouse hover in the plot"""
        x_idx = int(np.clip((x_val - x[0]) / args.dx, 0, args.nx - 1))
        y_idx = int(np.clip((y_val - z[0]) / args.dz, 0, args.nz - 1))
        val = vel[y_idx, x_idx]
        return f"x={x_val:.1f} m, z={y_val:.1f} m, v={val:.2f} m/s"  # Show x, z, and velocity value

    ax.format_coord = format_coord  # Override default format_coord

    cbar = fig.colorbar(im, label='Velocity (m/s)')
    ax.set_xlabel('Distance (m)')
    ax.set_ylabel('Depth (m)')
    ax.set_title('Velocity Field (m/s)')
    ax.grid(True, which='both')

    # Plot horizons
    colors = ['black', 'red', 'blue', 'green', 'cyan', 'magenta', 'yellow']
    for i, (hfile, hname) in enumerate(zip(horizon_files, horizon_names)):
        try:
            hdata = np.loadtxt(hfile)
            color = colors[i % len(colors)]
            linestyle = '-' if i < len(colors) else '--'
            ax.plot(hdata[:, 0], hdata[:, 1], color=color, linestyle=linestyle,
                   linewidth=2, label=hname)
        except Exception as e:
            print(f"Error plotting horizon '{hname}': {e}")

    if horizon_files:
        ax.legend()

    # Handle x-flip
    if args.no_interactive:
        # if no_interactive is set, apply x-flip if specified
        if args.xflip:
            ax.invert_xaxis()
    else:
        # Interactive x-flip prompt
        reverse_x = input("Do you need a X_flip? (y/n) [n]: ").strip().lower() or 'n'
        if reverse_x == 'y':
            ax.invert_xaxis()
            print("[ACTION] X-axis flipped.")

    # Keyboard controls
    def on_key(event):
        """Handle keyboard events for colormap switching"""
        global im, cbar
        if event.key.lower() == 'r':
            current_cmap = im.get_cmap().name
            idx = (rgb_cmaps.index(current_cmap) + 1) % len(rgb_cmaps) if current_cmap in rgb_cmaps else 0
            new_cmap = rgb_cmaps[idx]
            print(f"[ACTION] Switched to RGB colormap: {new_cmap}")
        elif event.key.lower() == 'h':
            current_cmap = im.get_cmap().name
            idx = (hsv_cmaps.index(current_cmap) + 1) % len(hsv_cmaps) if current_cmap in hsv_cmaps else 0
            new_cmap = hsv_cmaps[idx]
            print(f"[ACTION] Switched to HSV colormap: {new_cmap}")
        else:
            return
        im.set_cmap(new_cmap)
        cbar.remove()
        cbar = fig.colorbar(im, ax=ax)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('key_press_event', on_key)
    print("\nKeyboard controls:")
    print("  Press 'r' to cycle through RGB colormaps")
    print("  Press 'h' to cycle through HSV colormaps")

    plt.show()

if __name__ == '__main__':
    main()