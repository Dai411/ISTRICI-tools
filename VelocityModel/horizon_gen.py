#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Horizon Data Processing Tool
# Version: 1.0
# Author: Lining Yang @ CNR-ISAMR, Italy
# Date: 2025-07-14
# License: BSD-3-Clause
#
# Description:
#   Interactive tool for processing seismic horizon data with overlap correction.
#   Maintains proper depth relationships between horizons and generates comparison plots.
#
# Core Functionality:
#   - Loads horizon files (x,z pairs) with strict dimension checking
#   - Corrects horizon overlaps by enforcing proper depth relationships
#   - Generates three-panel comparison plots:
#     1. Original horizons
#     2. Corrected horizons
#     3. Depth differences
#   - Saves modified horizon files when changes are made
#
# Strict Data Requirements:
#   - All horizon files must have identical x-coordinates
#   - Each file must contain exactly 2 columns (x, depth) with matching length
#
# Input Files:
#   - horizon_[name].dat : Horizon depth files (space/tab delimited)
#
# Interactive parameters:
#   - Press enter to use default values shown in quotes
#
# Output Files:
#   - [original_name]_chopped.dat : Modified horizon files (when changes occur)
#   - Interactive matplotlib plot : Three-panel comparison
#
# Usage:
#   python3 horizon_gen.py
#
# Python Dependencies:
#   - numpy >= 1.20
#   - matplotlib >= 3.5
# =============================================================================

import os
import numpy as np
import matplotlib.pyplot as plt


def load_horizon_file(filename, expected_length):
    try:
        data = np.loadtxt(filename)
        if data.shape[0] != expected_length or data.shape[1] != 2:
            print(f"[WARNING] {filename} has shape {data.shape}, expected ({expected_length}, 2).")
            return None, None
        return data[:, 0], data[:, 1]  # x, depth
    except Exception as e:
        print(f"[ERROR] Failed to read {filename}: {e}")
        return None, None


def get_sampling_parameters():
    while True:
        try:
            nx = int(input("Enter horizontal sampling points (nx): ") or "701")
            nz = int(input("Enter vertical sampling points (nz): ") or "321")
            dx = int(input("Enter horizontal sampling interval (dx): ") or "100")
            dz = int(input("Enter vertical sampling interval (dz): ") or "25")
            return nx, nz, dx, dz
        except ValueError:
            print("Invalid input. Please enter integers.\n")


def get_user_files():
    print("Enter horizon .dat filenames one by one (press Enter without input to finish):")
    files = []
    while True:
        fname = input(f"File {len(files) + 1}: ").strip()
        if fname == "":
            break
        if not os.path.isfile(fname):
            print(f"[WARNING] File '{fname}' does not exist. Please try again.")
        else:
            files.append(fname)
    return files


def save_modified_horizon(x, original_depth, modified_depth, original_filename):
    if not np.allclose(original_depth, modified_depth):
        base, ext = os.path.splitext(original_filename)
        new_filename = f"{base}_chopped{ext}"
        # Save x and modified depth as two columns
        data_to_save = np.column_stack((x, modified_depth))
        np.savetxt(new_filename, data_to_save, fmt='%.6f %.6f')
        print(f"✔ Modified file saved as {new_filename}")


def plot_all_subplots(original_horizons, updated_horizons, nx, nz, dx, dz):
    fig, axs = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

    # Use first file's x coordinates as reference
    x = original_horizons[0][0]
    z_max = (nz - 1) * dz

    # 1. Original horizon curves
    for x_vals, depth_vals in original_horizons:
        axs[0].plot(x_vals, depth_vals)
    axs[0].set_ylim(0, z_max)  # Set range first
    axs[0].invert_yaxis()       # Then invert
    axs[0].set_xlim(x[0], x[-1])
    axs[0].set_title("Original Horizons")
    axs[0].set_ylabel("Depth (m)")
    axs[0].grid(True)

    # 2. Updated horizon curves
    for x_vals, depth_vals in updated_horizons:
        axs[1].plot(x_vals, depth_vals)
    axs[1].set_ylim(0, z_max)  # Set range first
    axs[1].invert_yaxis()       # Then invert
    axs[1].set_xlim(x[0], x[-1])
    axs[1].set_title("Updated Horizons")
    axs[1].set_ylabel("Depth (m)")
    axs[1].grid(True)

    # 3. Difference curves (updated - original) for horizon2 onwards
    for i in range(1, len(original_horizons)):
        diff = updated_horizons[i][1] - original_horizons[i][1]
        axs[2].plot(x, diff, label=f"horizon{i + 1} - original")
    axs[2].set_xlim(x[0], x[-1])
    axs[2].set_title("Difference After Overlap Correction")
    axs[2].set_xlabel("Distance (m)")
    axs[2].set_ylabel("Depth Difference (m)")
    axs[2].legend()
    axs[2].grid(True)

    plt.tight_layout()
    plt.show()


def main():
    print("========== Horizon Data Processing ==========")
    nx, nz, dx, dz = get_sampling_parameters()

    horizon_files = get_user_files()
    if not horizon_files:
        print("[ERROR] No valid horizon files provided. Exiting.")
        return

    original_horizons = []
    for fname in horizon_files:
        x, depth = load_horizon_file(fname, nx)
        if x is None or depth is None:
            print("Please check the data file and rerun the program.")
            return
        # Verify x coordinates are uniform (optional, currently just checking length)
        original_horizons.append((x, depth))

    # Verify all x coordinates match (basic requirement)
    base_x = original_horizons[0][0]
    for i, (x_vals, _) in enumerate(original_horizons[1:], start=2):
        if not np.allclose(base_x, x_vals):
            print(f"[ERROR] x coordinates in file #{i} do not match first file's x coordinates.")
            return

    # Process horizon data (overlap correction)
    updated_horizons = [original_horizons[0]]
    for i in range(1, len(original_horizons)):
        prev_depth = updated_horizons[i - 1][1]
        curr_x, curr_depth = original_horizons[i]
        # Replacement logic: if curr_depth < prev_depth, use prev_depth (shallower covers deeper)
        corrected_depth = np.where(curr_depth < prev_depth, prev_depth, curr_depth)
        updated_horizons.append((curr_x, corrected_depth))

    # Generate plots
    plot_all_subplots(original_horizons, updated_horizons, nx, nz, dx, dz)

    # Save modified files (only if changes were made)
    for i in range(len(original_horizons)):
        x_vals = original_horizons[i][0]
        original_depth = original_horizons[i][1]
        updated_depth = updated_horizons[i][1]
        save_modified_horizon(x_vals, original_depth, updated_depth, horizon_files[i])

    print("✅ Processing completed!")


if __name__ == '__main__':
    main()
    print("\n🔴 Thanks for using and please remember: \n   - The sky over Manchester is always red! 🔴")
    print("   - Glory Glory MAN United! ⚽")
