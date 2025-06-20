#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binary Data Comparison Tool

Author: Lining Yang
Created: 2025-06-16 23:41
Description:
    Interactive tool to compare two binary datasets (original vs processed)
    and visualize the differences with 2 dimensional plots.
"""

import numpy as np
import matplotlib.pyplot as plt # type: ignore
import argparse

def plot_comparison(original, smoothed, n1, n2):
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

    print(f"\n📊 Data Comparison Analysis:")
    print(f"   🔹 Average Absolute Error: {avg_error:.6f}")
    print(f"   🔺 Maximum Absolute Error: {max_error:.6f}")

    extent = [0, n2, n1, 0]  # [x_min, x_max, y_max, y_min]
    fig, axs = plt.subplots(1, 3, figsize=(18, 5))

    im0 = axs[0].imshow(original_plot, extent=extent, cmap='viridis', aspect='auto')
    axs[0].set_title("Original Data")
    axs[0].set_xlabel("Trace Index (n2)")
    axs[0].set_ylabel("Depth Index (n1)")
    fig.colorbar(im0, ax=axs[0])

    im1 = axs[1].imshow(smoothed_plot, extent=extent, cmap='viridis', aspect='auto')
    axs[1].set_title("Processed Data")
    axs[1].set_xlabel("Trace Index (n2)")
    axs[1].set_ylabel("Depth Index (n1)")
    fig.colorbar(im1, ax=axs[1])

    im2 = axs[2].imshow(error, extent=extent, cmap='seismic', aspect='auto',
                        vmin=-max_error, vmax=max_error)
    axs[2].set_title("Difference (Original - Processed)")
    axs[2].set_xlabel("Trace Index (n2)")
    axs[2].set_ylabel("Depth Index (n1)")
    fig.colorbar(im2, ax=axs[2])

    plt.tight_layout()
    plt.show()

def load_binary_file(file_path, n1, n2, fortran_order=False):
    """Load a binary file with error handling"""
    try:
        data = np.fromfile(file_path, dtype=np.float32)
        if data.size != n1 * n2:
            raise ValueError(f"Data size mismatch: Expected {n1}x{n2}={n1*n2} elements, got {data.size}")
        
        # reshape the data to (n1, n2) using Fortran order
        return data
    
    except Exception as e:
        print(f"❌ Error loading {file_path}: {str(e)}")
        return None

def interactive_mode():
    """Interactive mode for comparing two binary files"""
    print("\n" + "="*50)
    print("📊 Binary Data Comparison Tool")
    print("="*50)
    
    # Get input parameters
    print("\n[Original Data Parameters]")
    orig_file = input("Original data file path: ")
    
    print("\n[Processed (smoothed) Data Parameters]")
    proc_file = input("Processed (smoothed) data file path: ")
    
    # Get dimensions
    n1 = int(input("n1 (vertical dimension size): "))
    n2 = int(input("n2 (horizontal dimension size): "))
    
    # loading the data as Fortran order is the default behavior in numpy
    print("\n🔍 Loading data...")
    orig_data = load_binary_file(orig_file, n1, n2)
    if orig_data is None:
        return
    
    proc_data = load_binary_file(proc_file, n1, n2)
    if proc_data is None:
        return
    
    # test if the data sizes match
    if orig_data.size != n1 * n2 or proc_data.size != n1 * n2:
        print(f"❌ Size mismatch: Expected {n1}*{n2}={n1*n2} elements")
        print(f"    Original size: {orig_data.size}")
        print(f"    Processed size: {proc_data.size}")
        return
    
    # pass the data directly to the plotting function
    print("\n🖌️ Generating comparison plot...")
    plot_comparison(orig_data, proc_data, n1, n2)
    
    print("\n✅ Comparison complete!")

if __name__ == "__main__":
    # Command Line Example:
    # python3 smooth2_comp.py
    #
    # This script interactively compares two binary datasets
    #
    # Features:
    #   - Compares original vs processed data
    #   - Visualizes differences with seismic-style plots
    #   - Shows error metrics
    #   - Always uses Fortran order for visualization
    #
    # Usage:
    #   Simply run the script and follow the prompts
    
    parser = argparse.ArgumentParser(description="Interactive binary data comparison tool")
    parser.add_argument("--non-interactive", action="store_true", 
                        help="Run in non-interactive mode (coming soon)")
    
    args = parser.parse_args()
    
    if args.non_interactive:
        print("Non-interactive mode coming soon!")
    else:
        interactive_mode()
