#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_velres.py - Interactive Velocity Residual Visualization Tool

Author: Lining Yang @ CNR-ISMAR Bologna
Created: 2025-07-15 18:30
Last Modified: 2025-07-16

Description:
    This script loads velocity residual data (ASCII text or Fortran-order binary float32),
    and displays it as an interactive plot. Users can:
      1. Switch between RGB/HSV colormaps using 'r' and 'h' keys
      2. Support both text and binary input files
      3. Customize plot dimensions interactively or via CLI

    Data is assumed to be Fortran-order (z-fastest, i.e., depth-major, then trace).
    That is, the file is written as: for ix in 1..n2: for iz in 1..n1: value

CLI Usage Example:
    python3 plot_velres.py -f velres.dat -n1 321 -n2 701
    python3 plot_velres.py -f velres.bin -n1 321 -n2 701 --binary
    python3 plot_velres.py -f myfile.dat -n1 321 -n2 701 --save myplot.png
    python3 plot_velres.py -f velres.dat -n1 321 -n2 701 --no-check --verbose

Interactive Usage:
    python3 plot_velres.py
    # Then follow the prompts for file name and dimensions

Colormap switching:
    - Press 'r' to cycle through RGB colormaps
    - Press 'h' to cycle through HSV colormaps

"""

import argparse
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Define available colormaps
rgb_cmaps = ['jet', 'viridis', 'seismic', 'coolwarm', 'hot']
hsv_cmaps = ['hsv', 'twilight', 'rainbow', 'twilight_shifted', 'prism']

def in_cli_mode():
    return len(sys.argv) > 1

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Velocity Residual Visualization Tool (Fortran-order, n1=depth, n2=traces)"
    )
    parser.add_argument("-f", "--file", default="velres.dat", help="Data file name")
    parser.add_argument("-n1", type=int, help="Number of depth samples (n1, vertical)")
    parser.add_argument("-n2", type=int, help="Number of traces (n2, horizontal)")
    parser.add_argument("--binary", action="store_true", help="Force binary file loading (float32, Fortran-order)")
    parser.add_argument("--no-check", action="store_true", help="Skip size check before reshaping")
    parser.add_argument("--auto-shape", action="store_true", help="Infer missing n1 or n2 from file size")
    parser.add_argument("--transpose", action="store_true", help="Transpose data after reshaping (default: True)")
    parser.add_argument("--verbose", action="store_true", help="Print detailed status information")
    parser.add_argument("--save", type=str, help="Save the plot to file (e.g. output.png)")
    return parser.parse_args()

def load_data(filename, use_binary=False):
    print("[STATUS] Loading data ...")
    try:
        if use_binary:
            print(f"[INFO] Forcing binary read (float32): {filename}")
            data = np.fromfile(filename, dtype=np.float32)
        else:
            try:
                data = np.loadtxt(filename)
                print(f"[STATUS] Loaded ASCII text file: {filename}")
            except Exception:
                print(f"[INFO] Fallback to binary read (float32): {filename}")
                data = np.fromfile(filename, dtype=np.float32)
    except Exception as e:
        print(f"[ERROR] Failed to load '{filename}': {e}")
        exit(1)
    return data

def input_with_default(prompt, default, type_cast):
    try:
        user_input = input(f"{prompt} (default: {default}): ").strip()
        return type_cast(user_input) if user_input else default
    except ValueError:
        print(f"[WARNING] Invalid input. Using default value: {default}")
        return default

# ========================= MAIN =========================
if in_cli_mode():
    args = parse_arguments()
    filename = args.file

    if not os.path.exists(filename):
        print(f"[ERROR] File '{filename}' not found.")
        exit(1)

    data = load_data(filename, use_binary=args.binary)
    total_size = data.size

    n1 = args.n1
    n2 = args.n2

    if args.auto_shape:
        if n1 and not n2:
            if total_size % n1 != 0:
                print(f"[ERROR] Cannot infer n2: file size {total_size} not divisible by n1={n1}")
                exit(1)
            n2 = total_size // n1
            print(f"[AUTO] Inferred n2 = {n2}")
        elif n2 and not n1:
            if total_size % n2 != 0:
                print(f"[ERROR] Cannot infer n1: file size {total_size} not divisible by n2={n2}")
                exit(1)
            n1 = total_size // n2
            print(f"[AUTO] Inferred n1 = {n1}")
        elif not n1 and not n2:
            print(f"[ERROR] At least one of n1 or n2 must be specified with --auto-shape")
            exit(1)
    else:
        if n1 is None or n2 is None:
            print(f"[ERROR] Please provide both -n1 and -n2, or use --auto-shape to infer one.")
            exit(1)

    expected_size = n1 * n2
    if not args.no_check and data.size != expected_size:
        print(f"[ERROR] Data size mismatch.")
        print(f"        Expected: n1 × n2 = {n1} × {n2} = {expected_size}")
        print(f"        Got: {data.size}")
        exit(1)

    if args.verbose:
        print(f"[VERBOSE] File: {filename}")
        print(f"[VERBOSE] Data size: {data.size}")
        print(f"[VERBOSE] Target shape: ({n1}, {n2}), Transpose: {args.transpose}")

    # Always Fortran-order: reshape (n2, n1), then transpose to (n1, n2)
    reshaped = data.reshape((n2, n1)).T
else:
    print("=" * 50)
    print("Velocity Residual Visualization Tool (Interactive Mode)")
    print("=" * 50 + "\n")

    filename = input_with_default("Enter data file name \n(ASCII or Binary)", "velres.dat", str)
    n1 = input_with_default("Enter number of depth samples (n1)", 321, int)
    n2 = input_with_default("Enter number of traces (n2)", 701, int)

    if not os.path.exists(filename):
        print(f"[ERROR] File '{filename}' not found.")
        exit(1)

    # print("[STATUS] Loading data ...")
    data = load_data(filename)
    reshaped = data.reshape((n2, n1)).T

    # Simulate args object for consistency
    class Args: pass
    args = Args()
    args.binary = False
    args.no_check = False
    args.verbose = False
    args.save = None
    args.transpose = True  # Default transpose in interactive

# ======================= Plotting =======================
print("[STATUS] Creating visualization...")
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(
    reshaped,
    cmap=rgb_cmaps[0],
    aspect='auto',
    origin='upper',
    extent=[1, reshaped.shape[1], 0, reshaped.shape[0]]
)
cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Velocity Residual (m/s)")

ax.set_title(f"Velocity Residual from '{filename}'\nPress 'r' (RGB) or 'h' (HSV) to change colormap")
ax.set_xlabel("Trace Index (n2)")
ax.set_ylabel("Depth Index (n1, increasing downward)")

# Keypress handler for colormap switching
def on_key(event):
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

plt.tight_layout()
if hasattr(args, "save") and args.save:
    plt.savefig(args.save, dpi=300)
    print(f"[INFO] Plot saved to '{args.save}'")
else:
    print("[STATUS] Visualization ready. Press 'r' or 'h' to change colormaps.")
    plt.show()

print("\n🔴 Thanks for using this tool. Glory Glory Man United! ⚽")
