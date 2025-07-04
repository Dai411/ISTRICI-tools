#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2D Smoothing Tool (similar to Seismic Unix smooth2)
#
# Author: Lining YANG CNR-ISMAR Bologna
# Version: 1.0 Date: 2025-06-16 21:29
# License: BSD 3-Clause License
# SPDX-FileCopyrightText: 2025 Lining YANG <
#   
# This script performs 2D smoothing similar to Seismic Unix's smooth2
# This script allows users to smooth 2D data using a regularization approach
# that applies a first-order difference operator in both dimensions.
#
# It can be run in two modes:
#   1. Command Line Interface (CLI) mode: where parameters are passed as command line arguments.
#      Command Line Example:
#      python smooth2.py input.bin output.bin --n1 500 --n2 300 --r1 1.0 --r2 0.5 --win 100 400 50 200 --efile error.txt --plot --save-plot comparison.png
#   2. Interactive mode: where the user is prompted to enter parameters interactively.        
#
# Usage:
#   python smooth2.py <input_file> <output_file> --n1 <n1> --n2 <n2> 
#          [--r1 <r1>] [--r2 <r2>] [--win i1s i1e i2s i2e] 
#          [--efile error_file] [--plot] [--save-plot save_file]
#
# Arguments:
#   input_file   : Path to input binary file (float32 format)
#   output_file  : Path to output smoothed data (float32 binary)
#   --n1         : Size of first dimension (depth or samples)
#   --n2         : Size of second dimension (traces)
#   --r1         : Smoothing strength along first dimension (depth)
#                  Higher values = stronger smoothing
#   --r2         : Smoothing strength along second dimension (traces)
#                  Higher values = stronger smoothing
#   --win        : Smoothing window specified as four integers: 
#                  i1_start i1_end i2_start i2_end
#                  Defines processing window: data[i1_start:i1_end, i2_start:i2_end]
#                  Example: --win 100 400 50 200 processes data[100:400, 50:200]
#   --efile      : Optional path to save relative error report
#   --plot       : Display comparison plots (original, smoothed, error)
#   --save-plot  : Save comparison plot to specified file (png/jpg/etc)

import numpy as np
from scipy.sparse import diags, eye, kron, csr_matrix
from scipy.sparse.linalg import spsolve
import argparse
import matplotlib.pyplot as plt

# ========= Smoothing Core Logic =========

def build_diff_matrix(n):
    """Construct first-order difference matrix (keep sparse format)"""
    return diags([-1, 1], [0, 1], shape=(n - 1, n), format='csr')

def build_regularization(n1, n2, r1, r2):
    """Build regularization matrix (keep sparse format)"""
    I1 = eye(n1, format='csr')
    I2 = eye(n2, format='csr')

    D1 = build_diff_matrix(n1)
    R1 = kron(I2, D1.T @ D1, format='csr')

    D2 = build_diff_matrix(n2)
    R2 = kron(D2.T @ D2, I1, format='csr')

    return r1 * R1 + r2 * R2

def smooth2(data, r1=0.0, r2=0.0, win=None):
    """
    2D smoothing similar to Seismic Unix smooth2
    
    Parameters:
    data : 2D numpy array
        Input data to be smoothed
    r1 : float
        Smoothing parameter along first dimension (depth/samples)
    r2 : float
        Smoothing parameter along second dimension (traces)
    win : list of int
        Smoothing window [i1_start, i1_end, i2_start, i2_end]
    
    Returns:
    Smoothed 2D array with same shape as input
    """
    n1, n2 = data.shape
    if win is None:
        win = [0, n1, 0, n2]
    i1s, i1e, i2s, i2e = win

    sub_data = data[i1s:i1e, i2s:i2e]
    n1_win, n2_win = sub_data.shape
    N = n1_win * n2_win
    f = sub_data.flatten()
    
    # Maintain sparse matrix format
    A = eye(N, format='csr')
    R = build_regularization(n1_win, n2_win, r1, r2)
    lhs = (A + R).tocsr()  # Ensure CSR format for efficient solving
    
    s = spsolve(lhs, f)
    smoothed_sub = s.reshape(n1_win, n2_win)

    result = np.copy(data)
    result[i1s:i1e, i2s:i2e] = smoothed_sub
    return result

def compute_error(original, smoothed):
    """Calculate relative error between original and smoothed data"""
    return np.linalg.norm(original - smoothed) / np.linalg.norm(original)

# ========= Visualization =========

def plot_comparison(original, smoothed, n1, n2, save_path=None):
    """
    Plot comparison of original vs smoothed data with error analysis
    
    Uses Fortran-style (column-major) reshaping to maintain compatibility
    with seismic data visualization conventions.
    """
    # Fortran-style (column-major) reshaping
    original_plot = np.reshape(original.flatten(), (n1, n2), order='F')
    smoothed_plot = np.reshape(smoothed.flatten(), (n1, n2), order='F')
    error = original_plot - smoothed_plot
    abs_error = np.abs(error)
    avg_error = np.mean(abs_error)
    max_error = np.max(abs_error)

    print(f"\n📊 Smoothing Error Analysis:")
    print(f"   🔹 Average Error: {avg_error:.6f}")
    print(f"   🔺 Maximum Error: {max_error:.6f}")

    extent = [0, n2, n1, 0]  # [x_min, x_max, y_max, y_min]
    fig, axs = plt.subplots(1, 3, figsize=(18, 5))

    im0 = axs[0].imshow(original_plot, extent=extent, cmap='viridis', aspect='auto')
    axs[0].set_title("Original")
    axs[0].set_xlabel("Trace Index (n2)")
    axs[0].set_ylabel("Depth Index (n1)")
    fig.colorbar(im0, ax=axs[0])

    im1 = axs[1].imshow(smoothed_plot, extent=extent, cmap='viridis', aspect='auto')
    axs[1].set_title("Smoothed")
    axs[1].set_xlabel("Trace Index (n2)")
    axs[1].set_ylabel("Depth Index (n1)")
    fig.colorbar(im1, ax=axs[1])

    im2 = axs[2].imshow(error, extent=extent, cmap='seismic', aspect='auto',
                        vmin=-max_error, vmax=max_error)
    axs[2].set_title("Error (Original - Smoothed)")
    axs[2].set_xlabel("Trace Index (n2)")
    axs[2].set_ylabel("Depth Index (n1)")
    fig.colorbar(im2, ax=axs[2])

    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"💾 Comparison plot saved to: {save_path}")
    
    plt.show()

# ========= CLI & Interaction =========

def ask_input(prompt, cast=str, default=None):
    """Prompt user for input with type casting and default handling"""
    while True:
        inp = input(f"{prompt} [{'Enter for default' if default is not None else 'Required'}]: ")
        if inp == "" and default is not None:
            return default
        try:
            return cast(inp)
        except Exception:
            print(f"⚠️ Unable to convert to {cast.__name__}, please try again.")

def interactive_mode():
    """Interactive mode for parameter input"""
    print("🟡 Entering interactive mode:")
    config = {
        "input": ask_input("Input file path (float32 binary)"),
        "n1": ask_input("n1 (first dimension size: Depth nz)", int),
        "n2": ask_input("n2 (second dimension size: Distance nx)", int),
        "output": ask_input("Output filename", str)
    }

    smooth_all = ask_input("Smooth entire section? (y/n)", str, "y").lower() == "y"
    config["win"] = [0, config["n1"], 0, config["n2"]] if smooth_all else [
        ask_input("Window start i1", int),
        ask_input("Window end i1", int),
        ask_input("Window start i2", int),
        ask_input("Window end i2", int)
    ]

    config["r1"] = ask_input("r1 parameter (vertical smoothing)", float, 0.0)
    config["r2"] = ask_input("r2 parameter (horizontal smoothing)", float, 0.0)

    save_error = ask_input("Save error file? (y/n)", str, "n").lower() == "y"
    config["efile"] = ask_input("Error filename", str) if save_error else None

    config["plot"] = ask_input("Display plots? (y/n)", str, "y").lower() == "y"
    config["save_plot"] = ask_input("Save plot path (leave empty to skip)", str, "") or None
    
    return config

# ========= Main Entry =========

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="2D Smoothing similar to Seismic Unix smooth2")
    parser.add_argument("input", nargs="?", help="Input float32 binary file")
    parser.add_argument("output", nargs="?", help="Output float32 binary file")
    parser.add_argument("--n1", type=int, help="Number of samples in 1st dimension (depth)")
    parser.add_argument("--n2", type=int, help="Number of samples in 2nd dimension (traces)")
    parser.add_argument("--r1", type=float, default=0.0, 
                        help="Smoothing strength in depth direction (default: 0.0)")
    parser.add_argument("--r2", type=float, default=0.0, 
                        help="Smoothing strength in trace direction (default: 0.0)")
    parser.add_argument("--win", type=int, nargs=4, 
                        help="Processing window: i1_start i1_end i2_start i2_end")
    parser.add_argument("--efile", type=str, 
                        help="Optional output file for relative error report")
    parser.add_argument("--plot", action='store_true', 
                        help="Display comparison plots")
    parser.add_argument("--save-plot", type=str, 
                        help="Save comparison plot to specified file")

    args = parser.parse_args()

    if not all([args.input, args.output, args.n1, args.n2]):
        config = interactive_mode()
    else:
        config = vars(args)

    # Load and process data
    data = np.fromfile(config["input"], dtype=np.float32).reshape(
        (config["n1"], config["n2"]))
    
    if data.size != config["n1"] * config["n2"]:
        raise ValueError(f"Data size mismatch: Expected {config['n1']}x{config['n2']}={config['n1']*config['n2']}, got {data.size}")

    result = smooth2(data, r1=config["r1"], r2=config["r2"], win=config.get("win"))
    result.astype(np.float32).tofile(config["output"])

    # Error reporting
    if config.get("efile"):
        rel_error = compute_error(data, result)
        with open(config["efile"], "w") as f:
            f.write(f"Relative error: {rel_error:.6f}\n")
        print(f"✅ Smoothing complete. Relative error saved to: {config['efile']} ({rel_error:.6f})")
    else:
        print("✅ Smoothing complete")

    # Visualization handling
    show_plot = config.get("plot", False)
    save_path = config.get("save_plot")
    
    if show_plot or save_path:
        plot_comparison(data, result, config["n1"], config["n2"], save_path=save_path)
    
    print("\n🔴 Thanks for using. Remember: The sky over Manchester is always red! 🔴")
    print("   - Smoothing completed with United spirit - GGMU! ⚽")  
