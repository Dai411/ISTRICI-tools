#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Written by Lining YANG @ CNR-ISMAR, BOLOGNA, ITALY
# Date: 2025-06-27 18:45
# License: BSD 3-Clause License

"""
vel_data_analysis.py - Velocity Model Data Analysis Tool
version: 1.0.0
This script provides an interactive tool for analyzing seismic velocity model binary files.


It allows users to:

- Auto-detect possible dimensions (nx, nz) for a binary float32 file.
- Visualize the data using both C-order and Fortran-order.
- Let user choose the correct order.
- Show data distribution: histogram, most frequent values.
- Optionally plot sampled profiles (every N rows/columns) using various visualization methods.
"""

import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

def suggest_dimensions(data_len):
    # Suggest common square-like dimensions
    suggestions = []
    for n in range(50, 2001):
        if data_len % n == 0:
            m = data_len // n
            if 50 <= m <= 2000:
                suggestions.append((n, m))
    return suggestions

def plot_orders(data, nx, nz):
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.imshow(data.reshape((nz, nx), order='C'), aspect='auto', cmap='viridis')
    plt.title('C-order (row-major)')
    plt.colorbar()
    plt.subplot(1, 2, 2)
    plt.imshow(data.reshape((nz, nx), order='F'), aspect='auto', cmap='viridis')
    plt.title('F-order (column-major)')
    plt.colorbar()
    plt.tight_layout()
    plt.show()

def plot_histogram(data):
    plt.figure(figsize=(8, 4))
    plt.hist(data, bins=100, color='steelblue', alpha=0.7)
    plt.title('Velocity Value Distribution')
    plt.xlabel('Velocity')
    plt.ylabel('Frequency')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def print_top_values(data, topn=5):
    vals, counts = np.unique(data, return_counts=True)
    top_idx = np.argsort(counts)[-topn:][::-1]
    print("Top {} most frequent values:".format(topn))
    for i in top_idx:
        print(f"  Value: {vals[i]:.3f}, Count: {counts[i]}")

def plot_sample_profiles(matrix, axis=0, step=10):
    plt.figure(figsize=(10, 6))
    if axis == 0:
        for i in range(0, matrix.shape[0], step):
            plt.plot(matrix[i, :], alpha=0.2, color='blue')
        plt.title(f'Row profiles (every {step} rows, alpha blend)')
        plt.xlabel('Trace')
        plt.ylabel('Velocity')
    else:
        for i in range(0, matrix.shape[1], step):
            plt.plot(matrix[:, i], alpha=0.2, color='red')
        plt.title(f'Column profiles (every {step} columns, alpha blend)')
        plt.xlabel('Depth')
        plt.ylabel('Velocity')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_sample_heatmap(matrix, axis=0, step=10):
    if axis == 0:
        sampled = matrix[::step, :]
        ylabel = f'Row (every {step})'
        xlabel = 'Trace'
    else:
        sampled = matrix[:, ::step]
        ylabel = 'Depth'
        xlabel = f'Column (every {step})'
    plt.figure(figsize=(10, 6))
    plt.imshow(sampled, aspect='auto', cmap='jet')
    plt.colorbar(label='Velocity')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title('Sampled Velocity Heatmap')
    plt.tight_layout()
    plt.show()

def plot_sample_stat(matrix, axis=0, step=10):
    plt.figure(figsize=(8, 5))
    if axis == 0:
        sampled = matrix[::step, :]
        mean_profile = sampled.mean(axis=0)
        plt.plot(mean_profile, color='green')
        plt.title(f'Mean profile (rows every {step})')
        plt.xlabel('Trace')
        plt.ylabel('Mean Velocity')
    else:
        sampled = matrix[:, ::step]
        mean_profile = sampled.mean(axis=1)
        plt.plot(mean_profile, color='purple')
        plt.title(f'Mean profile (columns every {step})')
        plt.xlabel('Depth')
        plt.ylabel('Mean Velocity')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_thumbnail(matrix, axis=0, step=50):
    # Downsampled heatmap as thumbnail
    if axis == 0:
        sampled = matrix[::step, :]
        ylabel = f'Row (every {step})'
        xlabel = 'Trace'
    else:
        sampled = matrix[:, ::step]
        ylabel = 'Depth'
        xlabel = f'Column (every {step})'
    plt.figure(figsize=(6, 4))
    plt.imshow(sampled, aspect='auto', cmap='jet')
    plt.colorbar(label='Velocity')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title('Thumbnail (Coarse Heatmap)')
    plt.tight_layout()
    plt.show()

def main():
    filename = input("Enter binary velocity file: ").strip()
    data = np.fromfile(filename, dtype=np.float32)
    print(f"Loaded {len(data)} float32 values.")

    # 1. Auto-suggest possible dimensions
    suggestions = suggest_dimensions(len(data))
    print("Possible (nz, nx) dimension suggestions (showing up to 10):")
    for idx, (nz, nx) in enumerate(suggestions[:10]):
        print(f"  {idx+1}: nz={nz}, nx={nx}")
    print("  0: Enter custom dimensions manually")
    if suggestions:
        sel = int(input("Select a suggestion (number, 0 for manual): "))
        if sel == 0:
            nz = int(input("Enter nz (depth): "))
            nx = int(input("Enter nx (trace): "))
        else:
            nz, nx = suggestions[sel-1]
    else:
        nz = int(input("Enter nz (depth): "))
        nx = int(input("Enter nx (trace): "))

    # Check if dimensions match data length
    if nz * nx != len(data):
        print(f"❌ Dimension mismatch: {nz} x {nx} = {nz*nx}, but file has {len(data)} values.")
        exit(1)

    # 2. Visualize both C-order and F-order
    plot_orders(data, nx, nz)
    order = input("Which order looks correct? (c/f): ").strip().lower()
    if order == 'f':
        matrix = data.reshape((nz, nx), order='F')
    else:
        matrix = data.reshape((nz, nx), order='C')

    # 3. Data distribution histogram and top values
    plot_histogram(data)
    print_top_values(data, topn=5)

    # 4. Sampled profile visualization
    do_sample = input("Plot sampled profiles? (y/n): ").strip().lower()
    if do_sample == 'y':
        step = int(input("Sampling step (e.g., 10 or 50): "))
        axis = int(input("Sample along rows [0] or columns [1]? "))
        while True:
            print("Choose visualization method (you can enter multiple, e.g. 1 2 3):")
            print("  1: Overlayed profiles (alpha blend)")
            print("  2: Heatmap")
            print("  3: Mean profile curve")
            print("  4: Thumbnail (coarse heatmap)")
            print("  0: Exit sampled profile visualization")
            method = input("Enter 1, 2, 3, any combination (e.g. 1 2), or 0 to exit: ").strip()
            if method == '0':
                print("Exit sampled profile visualization.")
                break
            methods = method.split()
            valid = {'1', '2', '3', '4'}
            for m in methods:
                if m == '1':
                    plot_sample_profiles(matrix, axis=axis, step=step)
                elif m == '2':
                    plot_sample_heatmap(matrix, axis=axis, step=step)
                elif m == '3':
                    plot_sample_stat(matrix, axis=axis, step=step)
                elif m == '4':
                    plot_thumbnail(matrix, axis=axis, step=50)
                else:
                    if m not in valid:
                        print(f"Invalid input '{m}', please enter 1, 2, 3, 4, or 0.")

if __name__ == "__main__":
    main()
    print("\n🔴 Thanks for using. Remember: The sky over Manchester is always red! 🔴")
    print("   - Glory Glory MAN United! ⚽")
