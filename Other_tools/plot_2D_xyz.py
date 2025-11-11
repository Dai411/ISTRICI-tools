# -*- coding: utf-8 -*-
"""
============================================================================
                XYZ Geophysical Transect Data Plotter
============================================================================
Author: Lining YANG @CNR-ISMAR, Bologna, Italy
Date: 2025-11-11
Version: 1.3

Description:
This script is designed to load and visualize 3-column XYZ data from a
text file (e.g., .xyz, .csv, .txt). It is particularly useful for plotting
geophysical survey lines, such as 2D seismic profiles, bathymetric transects,
or other topographic data collected along a track.

The data file should have three columns: X, Y, and Z (e.g., longitude,
latitude, and elevation/depth), separated by a consistent delimiter
such as a comma, space, or tab. The script will automatically try to
detect the correct delimiter.

The user will be prompted to:
1. Enter the data filename.
2. Choose from three different plotting modes in a continuous loop.
3. Decide whether to flip the plot horizontally for each view.
4. For 3D plots, choose whether to apply 1:1 axis scaling.

Available Plotting Modes:
1. 2D Profile: A side-on view showing elevation/depth (Z) vs. distance
   along the track. This is the classic seismic/topographic profile view.
2. 2D Track Map: A top-down map view (X vs. Y) where the color of the
   track represents the Z value.
3. 3D Track Line: A view of the track in a 3D space, with an option for
   geometrically scaled axes.
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

def load_data(file_path):
    """
    Loads XYZ data from a text file, automatically detecting
    common delimiters (comma, space, or tab).
    """
    print(f"--> Loading data from '{file_path}'...")
    try:
        # First, attempt to load with a comma delimiter.
        print("    Attempting to parse with comma delimiter...")
        x, y, z = np.loadtxt(file_path, delimiter=',', unpack=True)
        print(f"--> Success! Loaded {len(x)} data points using comma delimiter.")
        return x, y, z
    except ValueError:
        # If the comma delimiter fails, try again with the default whitespace delimiter.
        print("    Comma delimiter failed. Retrying with whitespace (space/tab) delimiter...")
        try:
            x, y, z = np.loadtxt(file_path, unpack=True) # No delimiter specified handles any whitespace
            print(f"--> Success! Loaded {len(x)} data points using whitespace delimiter.")
            return x, y, z
        except Exception as e:
            # If both methods fail, report a comprehensive error.
            print(f"\nERROR: Failed to load data with both comma and whitespace delimiters.")
            print(f"    The specific error was: {e}")
            print("    Please ensure your file contains three columns of numbers separated by a consistent delimiter.")
            return None, None, None
    except FileNotFoundError:
        print(f"\nERROR: File '{file_path}' not found.")
        print("    Please make sure the file is in the same directory as the script, or provide a full path.")
        return None, None, None
    except Exception as e:
        # Catch any other unexpected errors.
        print(f"\nERROR: An unexpected error occurred: {e}")
        return None, None, None

def plot_2d_profile(x, y, z, flip_xaxis=False):
    """Plots a 2D topographic/seismic profile."""
    fig, ax = plt.subplots(figsize=(15, 7))
    segment_distances = np.hypot(np.diff(x), np.diff(y))
    distance_along_track = np.insert(np.cumsum(segment_distances), 0, 0)
    ax.plot(distance_along_track, z, color='blue', linewidth=1.5)
    ax.fill_between(distance_along_track, z, np.min(z), color='lightblue', alpha=0.4)
    ax.set_title('Topographic Profile', fontsize=16)
    ax.set_xlabel('Distance Along Track', fontsize=12)
    ax.set_ylabel('Depth / Elevation (Z-value)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_xlim(0, np.max(distance_along_track))
    if flip_xaxis:
        print("--> Flipping plot horizontally (inverting X-axis)...")
        ax.invert_xaxis()
    plt.show()

def plot_2d_track_map(x, y, z, flip_xaxis=False):
    """Plots a 2D top-down track map with color representing depth/elevation."""
    fig, ax = plt.subplots(figsize=(12, 10))
    sc = ax.scatter(x, y, c=z, cmap='viridis', s=15, alpha=0.9)
    fig.colorbar(sc, ax=ax, label='Depth / Elevation (Z-value)')
    ax.set_title('Track Map (Color Represents Depth/Elevation)', fontsize=16)
    ax.set_xlabel('X Coordinate / Longitude', fontsize=12)
    ax.set_ylabel('Y Coordinate / Latitude', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_aspect('equal', adjustable='box')
    if flip_xaxis:
        print("--> Inverting X-axis direction...")
        ax.invert_xaxis()
    plt.show()

# --- CHANGE HIGHLIGHT ---
def plot_3d_track(x, y, z, flip_xaxis=False, scale_xy_axes=False):
    """Plots the survey track as a line in 3D space, with an option to scale the X and Y axes equally."""
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    ax.plot(x, y, z)
    ax.set_title('3D Track Line', fontsize=16)
    ax.set_xlabel('X Coordinate / Longitude', fontsize=12)
    ax.set_ylabel('Y Coordinate / Latitude', fontsize=12)
    ax.set_zlabel('Depth / Elevation (Z-value)', fontsize=12)

    if scale_xy_axes:
        print("--> Applying 1:1 scaling to X and Y axes...")
        # This method preserves the true shape of the track on the horizontal plane.
        # It finds the larger of the X and Y data ranges and sets both axes to that range.
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        max_xy_range = max(x_range, y_range)
        
        x_mid = (x.max() + x.min()) * 0.5
        y_mid = (y.max() + y.min()) * 0.5
        
        ax.set_xlim(x_mid - max_xy_range * 0.5, x_mid + max_xy_range * 0.5)
        ax.set_ylim(y_mid - max_xy_range * 0.5, y_mid + max_xy_range * 0.5)
        # The Z-axis is left to autoscale to show maximum vertical detail.

    if flip_xaxis:
        print("--> Inverting X-axis direction...")
        ax.invert_xaxis()

    plt.show()

# --- Main Program Execution ---
if __name__ == "__main__":
    print("==============================================")
    print(" Welcome to the Geophysical Transect Plotter!")
    print("==============================================\n")
    
    file_name = input("Please enter the name of your data file (e.g., survey_line.txt): ")
    x_data, y_data, z_data = load_data(file_name)

    if x_data is None:
        exit()

    # --- Main plotting loop ---
    while True:
        print("\nPlease choose a plotting mode:")
        print("  1: 2D Profile (Side view showing elevation changes along the track)")
        print("  2: 2D Track Map (Top-down view, color represents depth)")
        print("  3: 3D Track Line (View the track in 3D space)")

        mode_choice = ''
        while mode_choice not in ['1', '2', '3']:
            mode_choice = input("Enter the mode number (1, 2, or 3): ")
            if mode_choice not in ['1', '2', '3']:
                print("Invalid input. Please try again.")

        # --- Ask for XY scaling ONLY if mode 3 is chosen ---
        should_scale_xy = False
        if mode_choice == '3':
            scale_choice = ''
            while scale_choice.lower() not in ['y', 'n']:
                # --- CHANGE HIGHLIGHT ---
                scale_choice = input("Apply 1:1 scaling to the X and Y axes (to preserve map shape)? (y/N): ")
                if scale_choice == '':
                    scale_choice = 'n'
                if scale_choice.lower() not in ['y', 'n']:
                    print("Invalid input. Please enter 'y' for yes or 'n' for no.")
            should_scale_xy = (scale_choice.lower() == 'y')

        # --- Ask if the plot should be flipped ---
        while True:
            flip_choice = (input("Flip the plot horizontally (invert the X-axis)? (y/N): ") or 'n').lower()
            if flip_choice in ['y', 'n']:
                break
            else:
                print("Invalid input. Please enter 'y' for yes or 'n' for no.")
        should_flip = (flip_choice == 'y')
        
        #flip_choice = ''
        #while flip_choice.lower() not in ['y', 'n']:
        #    flip_choice = input("Flip the plot horizontally (invert the X-axis)? (y/n): ")
        #    if flip_choice.lower() not in ['y', 'n']:
        #        print("Invalid input. Please enter 'y' for yes or 'n' for no.")
        #should_flip = (flip_choice.lower() == 'y')

        # --- Call the appropriate plotting function ---
        print("\nGenerating plot... (Close the plot window to continue)")
        if mode_choice == '1':
            plot_2d_profile(x_data, y_data, z_data, flip_xaxis=should_flip)
        elif mode_choice == '2':
            plot_2d_track_map(x_data, y_data, z_data, flip_xaxis=should_flip)
        elif mode_choice == '3':
            # --- CHANGE HIGHLIGHT ---
            plot_3d_track(x_data, y_data, z_data, flip_xaxis=should_flip, scale_xy_axes=should_scale_xy)

        # --- Ask user if they want to continue or quit ---
        continue_choice = (input("\nWould you like to plot this data in another mode? (y/N): ") or 'n').lower()
        if continue_choice != 'y':
            break

    print("\nScript finished.")
    print("Thanks for using the Geophysical Transect Plotter!")
    print("Glory Glory Manchester United! ⚽🔴😈")
