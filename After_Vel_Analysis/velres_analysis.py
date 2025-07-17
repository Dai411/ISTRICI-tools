#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
velres_analysis.py - Comprehensive Velocity Field Analysis Tool

Author: Lining Yang @ CNR-ISMAR, BOLOGNA, ITALY
Date: 2025-07-17
Last Modified: 2025-07-17
License: BSD-3-Clause

Description:
    This script performs comprehensive analysis of velocity field data (ASCII text or binary format),
    with the following capabilities:
      1. Robust file reading for both text and binary formats
      2. Statistical analysis with outlier detection
      3. Interactive heatmap visualization with colormap switching
      4. Vertical and horizontal profile plotting
      5. Automatic detection of high-variation regions
      6. Detailed reporting of data statistics and outliers

    Data is assumed to be Fortran-order (column-major) with dimensions (nz, nx).
    That is, the file is written as: for ix in 1..nx: for iz in 1..nz: value

CLI Usage Example:
    python3 velres_analysis.py
    # Follow interactive prompts for file path and parameters

    Alternative direct execution:
    python3 velres_analysis.py -f velres.dat -nx 701 -nz 321 -t 3 -s 50

Interactive Features:
    - Press 'r' to cycle through RGB colormaps (jet, viridis, plasma, inferno)
    - Press 'h' to cycle through HSV colormaps (hsv, twilight, twilight_shifted)
    - Interactive zoom regions automatically detected based on data variation

Analysis Features:
    - Global and clean data statistics
    - Outlier detection with configurable sigma threshold
    - Data quality metrics (non-uniform columns percentage)
    - Option to save outlier reports

Output:
    - Interactive matplotlib figures
    - Detailed console statistics report
    - Optional text report of outliers
"""

import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

def read_velocity_file(file_path, nx=701, nz=321):
    """Read velocity file with robust error handling"""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found!")

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in ('.txt', '.dat'):
            with open(file_path, 'r') as file:
                data = file.readlines()
            values = [float(line.strip()) for line in data if line.strip()]

        elif file_ext == '.bin':
            try:
                values = np.fromfile(file_path, dtype=np.float32)
                if len(values) != nx * nz:
                    values = np.fromfile(file_path, dtype=np.float64)
            except Exception as e:
                raise ValueError(f"Binary file read failed: {e}")

        else:
            raise ValueError("Only .txt, .dat, .bin files supported")

        if len(values) != nx * nz:
            raise ValueError(f"Data size mismatch! Expected {nx*nz} values, got {len(values)}")

        return np.array(values).reshape((nz, nx), order='F')

    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return None

def analyze_data(velocity, sigma_threshold=3):
    """Comprehensive data analysis with outlier detection"""
    if velocity is None:
        return None, [], []

    # Global statistics
    global_stats = {
        'mean': np.mean(velocity),
        'median': np.median(velocity),
        'std': np.std(velocity),
        'min': np.min(velocity),
        'max': np.max(velocity)
    }

    # Outlier detection
    outliers = []
    outlier_mask = np.zeros_like(velocity, dtype=bool)

    for col in range(velocity.shape[1]):
        col_data = velocity[:, col]
        col_mean = np.mean(col_data)
        col_std = np.std(col_data)

        threshold = sigma_threshold * col_std
        col_outliers = np.where(
            (col_data < col_mean - threshold) | 
            (col_data > col_mean + threshold)
        )[0]

        for row in col_outliers:
            outliers.append({
                'row': row, 'col': col,
                'value': velocity[row, col],
                'deviation': (velocity[row, col] - col_mean) / col_std
            })
            outlier_mask[row, col] = True

    clean_data = velocity[~outlier_mask]
    clean_stats = {
        'mean': np.mean(clean_data),
        'median': np.median(clean_data),
        'std': np.std(clean_data)
    } if len(clean_data) > 0 else None

    return global_stats, clean_stats, outliers

def plot_heatmaps_with_interactivity(velocity, highlight_cols=None):
    """Display heatmaps with interactive colormap switching"""
    if velocity is None:
        return

    fig = plt.figure(figsize=(12, 6), num="Velocity Field Heatmaps")
    gs = GridSpec(1, 2, width_ratios=[1, 1])

    handles = {
        'im0': None,
        'im1': None,
        'cbar0': None,
        'cbar1': None,
        'ax0': None,
        'ax1': None
    }

    ax0 = plt.subplot(gs[0])
    im0 = ax0.imshow(velocity, cmap='jet', aspect='auto',
                     extent=[0, velocity.shape[1], velocity.shape[0], 0])
    cbar0 = fig.colorbar(im0, ax=ax0, label='Velocity')
    ax0.set_title("Full Field")
    ax0.set_xlabel("Distance")
    ax0.set_ylabel("Depth")

    handles.update({'im0': im0, 'cbar0': cbar0, 'ax0': ax0})

    if highlight_cols:
        ax1 = plt.subplot(gs[1])
        zoom = velocity[:, highlight_cols[0]:highlight_cols[1] + 1]
        im1 = ax1.imshow(zoom, cmap='jet', aspect='auto',
                         extent=[highlight_cols[0], highlight_cols[1], velocity.shape[0], 0])
        cbar1 = fig.colorbar(im1, ax=ax1, label='Velocity')
        ax1.set_title(f"Zoom: Columns {highlight_cols[0]}-{highlight_cols[1]}")
        handles.update({'im1': im1, 'cbar1': cbar1, 'ax1': ax1})

    rgb_cmaps = ['jet', 'viridis', 'plasma', 'inferno']
    hsv_cmaps = ['hsv', 'twilight', 'twilight_shifted']

    def on_key(event):
        current_cmap = handles['im0'].get_cmap().name
        if event.key.lower() not in ['r', 'h']:
            return
        cmap_list = rgb_cmaps if event.key.lower() == 'r' else hsv_cmaps
        idx = (cmap_list.index(current_cmap) + 1) % len(cmap_list) if current_cmap in cmap_list else 0
        new_cmap = cmap_list[idx]
        print(f"[ACTION] Switched to colormap: {new_cmap}")
        handles['im0'].set_cmap(new_cmap)
        if handles['im1']:
            handles['im1'].set_cmap(new_cmap)
        handles['cbar0'].remove()
        handles['cbar0'] = fig.colorbar(handles['im0'], ax=handles['ax0'], label='Velocity')
        if handles['im1'] and handles['cbar1']:
            handles['cbar1'].remove()
            handles['cbar1'] = fig.colorbar(handles['im1'], ax=handles['ax1'], label='Velocity')
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('key_press_event', on_key)
    # Move interaction instructions to bottom-left corner
    fig.text(0.02, 0.01, "Press 'r' for RGB colormaps, 'h' for HSV colormaps", fontsize=9, color='gray')
    plt.tight_layout()
    plt.show(block=False)

def plot_profiles(velocity, sample_interval=50):
    """Display vertical and horizontal profiles"""
    if velocity is None:
        return
    fig = plt.figure(figsize=(12, 10), num="Velocity Profiles")
    gs = GridSpec(2, 1, height_ratios=[1, 1])
    ax0 = plt.subplot(gs[0])
    sample_cols = range(0, velocity.shape[1], sample_interval)
    for col in sample_cols:
        ax0.plot(velocity[:, col], -np.arange(velocity.shape[0]),
                 alpha=0.7, label=f'Col {col}' if col % (2*sample_interval) == 0 else "")
    ax0.set_title(f"Column Profiles (sample every {sample_interval} cols)")
    ax0.set_ylabel("Depth")
    ax0.legend(loc='upper right', fontsize=8)
    ax0.grid(True, alpha=0.3)

    ax1 = plt.subplot(gs[1])
    sample_rows = range(0, velocity.shape[0], sample_interval)
    for row in sample_rows:
        ax1.plot(np.arange(velocity.shape[1]), velocity[row, :],
                 alpha=0.7, label=f'Row {row}' if row % (2*sample_interval) == 0 else "")
    ax1.set_title(f"Row Profiles (sample every {sample_interval} rows)")
    ax1.set_xlabel("Distance")
    ax1.set_ylabel("Velocity")
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show(block=False)

def save_report(outliers, filename='report.txt'):
    """Save outlier report to file"""
    try:
        with open(filename, 'w') as f:
            f.write(f"Total outliers: {len(outliers)}\n")
            f.write("row,col,value,deviation(σ)\n")
            for o in outliers:
                f.write(f"{o['row']},{o['col']},{o['value']:.6f},{o['deviation']:.2f}\n")
        print(f"Report saved to {filename}")
    except Exception as e:
        print(f"Failed to save report: {str(e)}")

if __name__ == "__main__":
    # User inputs with error handling
    file_path = input("Enter file path (.txt/.dat/.bin): ").strip()
    try:
        nx = int(input("Enter nx (default 701): ") or 701)
    except Exception:
        nx = 701
    try:
        nz = int(input("Enter nz (default 321): ") or 321)
    except Exception:
        nz = 321
    try:
        sigma_threshold = float(input("Enter outlier threshold (default 3σ): ") or 3)
    except Exception:
        sigma_threshold = 3
    try:
        sample_interval = int(input("Enter sampling interval (default 50): ") or 50)
    except Exception:
        sample_interval = 50

    print("\n" + "=" * 50)
    velocity = read_velocity_file(file_path, nx, nz)

    if velocity is not None:
        print(f"File loaded successfully! Shape (nz, nx): {velocity.shape}")

        # Analyze full data
        global_stats, clean_stats, outliers = analyze_data(velocity, sigma_threshold)

        # Detect non-uniform columns (for info only)
        non_uniform_cols = len([
            col for col in range(velocity.shape[1])
            if len(np.unique(np.round(velocity[:, col], 6))) > 1
        ])

        # Automatically detect focus/zoom region based on column std
        col_std_devs = np.std(velocity, axis=0)
        threshold = np.percentile(col_std_devs, 85)  # top 15% variation
        candidate_cols = np.where(col_std_devs > threshold)[0]

        highlight_cols = None
        zoom_stats = None
        if len(candidate_cols) > 0:
            zoom_start = int(candidate_cols[0])
            zoom_end = int(candidate_cols[-1])
            highlight_cols = (zoom_start, zoom_end)
            zoom_data = velocity[:, zoom_start:zoom_end + 1]
            zoom_stats = {
                'mean': np.mean(zoom_data),
                'median': np.median(zoom_data),
                'std': np.std(zoom_data),
                'min': np.min(zoom_data),
                'max': np.max(zoom_data)
            }

        # Show interactive plots
        plot_heatmaps_with_interactivity(velocity, highlight_cols)
        plot_profiles(velocity, sample_interval)

        print("\n[INFO] Close all plot windows to continue...")
        plt.show()  # Block until user closes the figures

        # Display global statistics
        print("\n=============== Global Statistics ================")
        print(f"Mean velocity:       {global_stats['mean']:.4f}")
        print(f"Median velocity:     {global_stats['median']:.4f}")
        print(f"Standard deviation:  {global_stats['std']:.4f}")
        print(f"Data range:          [{global_stats['min']:.4f}, {global_stats['max']:.4f}]")

        if clean_stats:
            print("\n=== Clean Data Statistics (excluding outliers) ===")
            print(f"Mean velocity:       {clean_stats['mean']:.4f} (Δ={global_stats['mean'] - clean_stats['mean']:.4f})")
            print(f"Median velocity:     {clean_stats['median']:.4f} (Δ={global_stats['median'] - clean_stats['median']:.4f})")
            print(f"Standard deviation:  {clean_stats['std']:.4f} (Δ={global_stats['std'] - clean_stats['std']:.4f})")

        print("\n================== Data Quality ==================")
        print(f"Non-uniform columns: {non_uniform_cols}/{velocity.shape[1]} ({non_uniform_cols / velocity.shape[1]:.1%})")
        print(f"Potential outliers:  {len(outliers)} (>{sigma_threshold}σ from column means)")

        # Display zoom region statistics if available
        if highlight_cols and zoom_stats:
            print("\n============= Zoom Region Statistics =============")
            print(f"Columns:             {highlight_cols[0]}–{highlight_cols[1]}")
            print(f"Mean velocity:       {zoom_stats['mean']:.4f}")
            print(f"Median velocity:     {zoom_stats['median']:.4f}")
            print(f"Standard deviation:  {zoom_stats['std']:.4f}")
            print(f"Data range:          [{zoom_stats['min']:.4f}, {zoom_stats['max']:.4f}]")

        # Save report after visual inspection
        if outliers:
            print("\nTop 5 outliers:")
            for o in sorted(outliers, key=lambda x: abs(x['deviation']), reverse=True)[:5]:
                print(f"[Row {o['row']:3d}, Col {o['col']:3d}] = {o['value']:.4f} ({o['deviation']:+.1f}σ)")

            if input("\nSave outlier report? (y/n): ").lower() == 'y':
                report_name = input("Enter filename (default report.txt): ") or 'report.txt'
                save_report(outliers, report_name)

    print("=" * 50)
