#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Lining YANG @ CNR-ISMAR, BOLOGNA, ITALY
Date: 2025-06-06 17:44
Last Modified: 2025-07-22
License: BSD-3-Clause

Description:
    This script provides an interactive tool for interpolating picked horizons (like SeafloorZ.dat
    into a uniform x-grid. It supports various interpolation methods and allows users to visualize
    the results before saving. The output is saved in a specified format, with options for column       
    order and interpolation method.

Features:
    1. Read picked horizon data from a file
    2. Choose column order (x, z) or (z, x)
    3. Interpolate into a uniform x-grid with user-defined parameters
    4. Select from multiple interpolation methods (linear, spline, cubic, etc.)
    5. Visualize the interpolation result before saving
    6. Save the interpolated data to a specified output file
    7. ASCII art for better visual appearance

Usage:
    python3 horizon_interpolation.py     

Origin:
    from the preparepick.f from ISTRICI from Umberta Tinivella, OGS
    https://github.com/Dai411/ISTRICI-OGS/blob/main/TRAD_V1/preparepicks.f

"""

import numpy as np
import matplotlib.pyplot as plt  # type: ignore
from scipy.interpolate import interp1d, UnivariateSpline, CubicSpline, Akima1DInterpolator, BSpline, make_interp_spline  # type: ignore
import os

# ASCII art for better visual appearance
BANNER = """
╔══════════════════════════════════════════════════╗
║          HORIZON INTERPOLATION TOOL              ║
╚══════════════════════════════════════════════════╝
"""

print(BANNER)
print("🔹 Interpolate picked horizon (like SeafloorZ.dat) into a uniform x-grid")
print("🔹 Output will be saved as horizonZ_seafloor.dat or custom name\n")

# === User Input ===
input_file = input("📂 Enter picked horizon file (e.g. SeafloorZ.dat): ").strip()
if not os.path.exists(input_file):
    print(f"\n❌ Error: File '{input_file}' not found.")
    exit()

# === Read picked data ===
data = np.loadtxt(input_file)
if data.shape[1] != 2:
    print("\n❌ Error: Input must have exactly two columns")
    exit()

# === Column order selection ===
print("\n📊 Data format selection:")
print("1. [Distance(x), Depth(z)] order")
print("2. [Depth(z), Distance(x)] order (Fortran style)")
col_choice = input("Choose column order (1 or 2): ").strip()

if col_choice == '1':
    x_picked = data[:, 0]
    z_picked = data[:, 1]
    print("\nℹ️ Selected column order: [x, z]")
elif col_choice == '2':
    x_picked = data[:, 1]
    z_picked = data[:, 0]
    print("\nℹ️ Selected column order: [z, x] (Fortran style)")
else:
    print("\n❌ Invalid choice. Using default [z, x] order.")
    x_picked = data[:, 1]
    z_picked = data[:, 0]

# === Sort by x (important) ===
sort_idx = np.argsort(x_picked)
x_picked = x_picked[sort_idx]
z_picked = z_picked[sort_idx]

# === Interpolation range ===
print("\n📏 Enter interpolation parameters (from your velocity model):")
cdp1 = float(input("   Start x (e.g. 0): "))
cdp2 = float(input("   End x (e.g. 70000): "))
dx = float(input("   Spacing dx (e.g. 100): "))
x_target = np.arange(cdp1, cdp2 + dx, dx)

while True:
    # === Interpolation method ===
    print("\n🔧 Available interpolation methods:")
    print("1. linear - Piecewise linear interpolation")
    print("2. spline - Smoothing spline")
    print("3. poly3 - 3rd order polynomial (not recommended)")
    print("4. cubic - Cubic spline")
    print("5. akima - Akima spline (good for unevenly spaced data)")
    print("6. quadratic - Piecewise quadratic interpolation")
    print("7. bspline - B-spline interpolation")
    print("8. nearest - Nearest neighbor interpolation")
    
    choice = input("\n💡 Choose interpolation method (number or name): ").strip().lower()
    
    # Method mapping
    method_map = {
        '1': 'linear',
        '2': 'spline',
        '3': 'poly3',
        '4': 'cubic',
        '5': 'akima',
        '6': 'quadratic',
        '7': 'bspline',
        '8': 'nearest'
    }

    # Get actual method name
    method = method_map.get(choice, choice)

    # === Interpolation function ===
    try:
        if method == "linear":
            interp_fn = interp1d(
                x_picked, z_picked, kind='linear',
                bounds_error=False,
                fill_value=(z_picked[0], z_picked[-1])
            )
            z_target = interp_fn(x_target)

        elif method == "spline":
            spline = UnivariateSpline(x_picked, z_picked, k=3, s=0)
            z_target = spline(x_target)

        elif method == "poly3":
            coeffs = np.polyfit(x_picked, z_picked, 3)
            poly = np.poly1d(coeffs)
            z_target = poly(x_target)

        elif method == "cubic":
            cubic_spline = CubicSpline(x_picked, z_picked)
            z_target = cubic_spline(x_target)
            
        elif method == "akima":
            akima = Akima1DInterpolator(x_picked, z_picked)
            z_target = akima(x_target)

        elif method == "quadratic":
            interp_fn = interp1d(
                x_picked, z_picked, kind='quadratic',
                bounds_error=False,
                fill_value=(z_picked[0], z_picked[-1])
            )
            z_target = interp_fn(x_target)

        elif method == "bspline":
            bspline = make_interp_spline(x_picked, z_picked, k=3)
            z_target = bspline(x_target)

        elif method == "nearest":
            interp_fn = interp1d(
                x_picked, z_picked, kind='nearest',
                bounds_error=False,
                fill_value=(z_picked[0], z_picked[-1])
            )
            z_target = interp_fn(x_target)

        else:
            print("\n❌ Unknown interpolation method. Please try again.")
            continue

        # === Visualization preview ===
        plt.figure(figsize=(10, 5))
        plt.plot(x_picked, z_picked, 'ko', label='Picked Points', markersize=5)
        plt.plot(x_target, z_target, 'r-', linewidth=1.5, label=f'Interpolated ({method})')
        plt.xlabel("Distance x (m)")
        plt.ylabel("Depth z (m)")
        plt.title(f"Interpolated Horizon Preview\nMethod: {method}")
        plt.gca().invert_yaxis()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        plt.show()

        # Ask if satisfied with current result
        satisfied = input("\n✅ Does this interpolation look good? (y/n): ").strip().lower()
        if satisfied == 'y':
            break
        plt.close()  # Close current figure

    except Exception as e:
        print(f"\n❌ Interpolation error: {str(e)}")
        print("Please try a different method.")
        continue

# === Save confirmation ===
save = input("\n💾 Do you want to save the interpolated file? (y/n): ").strip().lower()
if save == 'y':
    default_name = "horizon.dat"
    output_file = input(f"   Output file name (default: {default_name}): ").strip()
    if not output_file:
        output_file = default_name

    with open(output_file, 'w') as f:
        for x, z in zip(x_target, z_target):
            f.write(f"{x:12.6f} {z:12.6f}\n")

    print(f"\n🎉 Success! File saved as: {output_file}")
    print(f"   - Points interpolated: {len(x_target)}")
    print(f"   - X range: {x_target[0]:.1f} to {x_target[-1]:.1f}")
    print(f"   - Z range: {min(z_target):.1f} to {max(z_target):.1f}")
else:
    print("\n❎ Operation completed without saving.")
