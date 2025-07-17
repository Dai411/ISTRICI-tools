#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binary Data Comparison Tool (Fortran-Order)

Author: Lining Yang
Created: 2025-06-16 23:41
Last Modified: 2025-07-14

Description:
    A Python tool to compare two binary datasets (original vs processed),
    visualize their differences with seismic-style 2D plots, and compute error metrics.
    Maintains Fortran-order (column-major) consistency throughout processing.

Usage:
    Interactive Mode:
        $ python3 comp_vfile.py

    CLI Mode Example:
        $ python3 comp_vfile.py --non-interactive \
            --orig original_data.bin \
            --proc processed_data.bin \
            --n1 512 --n2 128 \
            --save comparison_output.png \
            --save-error error_data.bin

Arguments:
    --non-interactive       Run the tool in CLI mode.
    --orig <file>           Path to the original binary file.
    --proc <file>           Path to the processed binary file.
    --n1 <int>             Vertical dimension size.
    --n2 <int>             Horizontal dimension size.
    --save <filename>       Save the comparison plot as PNG.
    --save-error <filename> Save error data as binary file (Fortran-order).
"""

import numpy as np
import matplotlib.pyplot as plt  # type: ignore
import argparse
import sys
import os

def save_error_data(error, filename, n1, n2):
    """
    Save error data to binary file in Fortran-order (column-major)
    
    Args:
        error: 2D error array
        filename: Output file path
        n1: Vertical dimension
        n2: Horizontal dimension
    """
    try:
        # Ensure Fortran-order consistency
        error_flat = np.reshape(error, (n1, n2), order='F').flatten(order='F')
        error_flat.astype(np.float32).tofile(filename)
        print(f"💾 Error data saved to: {filename} (Fortran-order, {n1}x{n2})")
    except Exception as e:
        print(f"❌ Failed to save error data: {str(e)}")

def plot_comparison(original, smoothed, n1, n2, orig_filename="", smoothed_filename="", save_path=None, save_error_path=None):
    """
    Compare and visualize two datasets with Fortran-order consistency
    
    Args:
        original: Original data array
        smoothed: Processed data array
        n1: Vertical dimension
        n2: Horizontal dimension
        orig_filename: Original filename for display
        smoothed_filename: Processed filename for display
        save_path: Path to save plot (optional)
        save_error_path: Path to save error data (optional)
    
    Returns:
        error: 2D error array in Fortran-order
    """
    # Reshape with Fortran-order
    original_plot = np.reshape(original.flatten(), (n1, n2), order='F')
    smoothed_plot = np.reshape(smoothed.flatten(), (n1, n2), order='F')
    # error = original_plot - smoothed_plot
    error = smoothed_plot - original_plot  # Revised：Processed - Original

    # Calculate error metrics
    abs_error = np.abs(error)
    avg_error = np.mean(abs_error)
    max_error = np.max(abs_error)

    print(f"\n📊 Data Comparison Analysis:")
    print(f"   🔹 Average Absolute Error: {avg_error:.6f}")
    print(f"   🔺 Maximum Absolute Error: {max_error:.6f}")

    # Save error data with dimension info
    if save_error_path:
        save_error_data(error, save_error_path, n1, n2)

    # Create visualization
    extent = [0, n2, n1, 0]
    fig, axs = plt.subplots(1, 3, figsize=(18, 5))

    # Plot original data
    im0 = axs[0].imshow(original_plot, extent=extent, cmap='viridis', aspect='auto')
    axs[0].set_title(f"Original Data\n{os.path.basename(orig_filename)}")
    axs[0].set_xlabel("Trace Index (n2)")
    axs[0].set_ylabel("Depth Index (n1)")
    fig.colorbar(im0, ax=axs[0])

    # Plot processed data
    im1 = axs[1].imshow(smoothed_plot, extent=extent, cmap='viridis', aspect='auto')
    axs[1].set_title(f"Processed Data\n{os.path.basename(smoothed_filename)}")
    axs[1].set_xlabel("Trace Index (n2)")
    axs[1].set_ylabel("Depth Index (n1)")
    fig.colorbar(im1, ax=axs[1])

    # Plot difference
    im2 = axs[2].imshow(error, extent=extent, cmap='seismic', aspect='auto',
                        vmin=-max_error, vmax=max_error)
    axs[2].set_title(("Difference (Processed - Original)\n"
                 "Red: Processed > Original\n"
                 "Blue: Processed < Original"))
    axs[2].set_ylabel("Depth Index (n1)")
    fig.colorbar(im2, ax=axs[2])

    plt.tight_layout()

    # Handle plot output
    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"\n💾 Plot saved to: {save_path}")
        plt.close()
    else:
        plt.show()

    return error

def load_binary_file(file_path, n1, n2):
    """
    Load binary file with dimension validation
    
    Args:
        file_path: Path to binary file
        n1: Expected vertical dimension
        n2: Expected horizontal dimension
    
    Returns:
        Loaded data array or None if error
    """
    try:
        data = np.fromfile(file_path, dtype=np.float32)
        if data.size != n1 * n2:
            raise ValueError(f"Expected {n1}x{n2}={n1*n2} elements, got {data.size}")
        return data
    except Exception as e:
        print(f"❌ Error loading {file_path}: {str(e)}")
        return None

def interactive_mode():
    """Run the tool in interactive user-input mode"""
    print("=" * 50)
    print("📊 Binary Data Comparison Tool (Interactive Mode)")
    print("=" * 50)

    # Get user input
    orig_file = input("Original data file path: ")
    proc_file = input("Processed data file path: ")
    n1 = int(input("n1 (vertical size): "))
    n2 = int(input("n2 (horizontal size): "))

    # Load data
    print("\n🔍 Loading data...")
    orig_data = load_binary_file(orig_file, n1, n2)
    if orig_data is None: return
    proc_data = load_binary_file(proc_file, n1, n2)
    if proc_data is None: return

    # Generate and show plot
    print("\n🖌️ Generating comparison plot...")
    error = plot_comparison(orig_data, proc_data, n1, n2,
                          orig_filename=orig_file, 
                          smoothed_filename=proc_file)
    
    # Prompt for error data saving
    save_error = input("\n💾 Save error data? [y/N]: ").strip().lower()
    if save_error == 'y':
        save_error_path = input("Enter filename to save error data (e.g., error.bin): ").strip()
        if save_error_path:
            save_error_data(error, save_error_path, n1, n2)
        else:
            print("⚠️ No filename provided, skipping error data save")

    print("\n✅ Comparison complete!")

def non_interactive_mode(args):
    """Run the tool in command-line mode"""
    # Validate required arguments
    if not (args.orig and args.proc and args.n1 and args.n2):
        print("❌ Missing required arguments in non-interactive mode.\n"
              "Use --help to see required options.")
        sys.exit(1)

    print("\n🔧 Running in non-interactive mode...")
    print(f"   📁 Original file: {args.orig}")
    print(f"   📁 Processed file: {args.proc}")
    print(f"   📐 Dimensions: n1={args.n1}, n2={args.n2}")
    if args.save: print(f"   💾 Save output to: {args.save}")
    if args.save_error: print(f"   💾 Save error data to: {args.save_error}")

    # Load data
    orig_data = load_binary_file(args.orig, args.n1, args.n2)
    if orig_data is None: sys.exit(1)
    proc_data = load_binary_file(args.proc, args.n1, args.n2)
    if proc_data is None: sys.exit(1)

    # Process and visualize
    plot_comparison(orig_data, proc_data, args.n1, args.n2,
                    orig_filename=args.orig,
                    smoothed_filename=args.proc,
                    save_path=args.save,
                    save_error_path=args.save_error)

if __name__ == "__main__":
    # Configure command-line arguments
    parser = argparse.ArgumentParser(description="Binary data comparison tool (Fortran-order)")
    parser.add_argument("--non-interactive", action="store_true", 
                       help="Run in non-interactive CLI mode")
    parser.add_argument("--orig", type=str, 
                       help="Original binary data file path")
    parser.add_argument("--proc", type=str, 
                       help="Processed binary data file path")
    parser.add_argument("--n1", type=int, 
                       help="Vertical dimension size")
    parser.add_argument("--n2", type=int, 
                       help="Horizontal dimension size")
    parser.add_argument("--save", type=str, 
                       help="Path to save the comparison plot")
    parser.add_argument("--save-error", type=str, 
                       help="Path to save the error data (Fortran-order)")

    args = parser.parse_args()

    # Execute appropriate mode
    if args.non_interactive:
        non_interactive_mode(args)
    else:
        interactive_mode()

    print("\n🔴 Thanks for using and please remember: \n   - The sky over Manchester is always red! 🔴")
    print("   - Glory Glory MAN United! ⚽")
