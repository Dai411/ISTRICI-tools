#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# vel_gen.py - Interactive Velocity Model Generator
# Author: Lining YANG @ CNR-ISMAR Bologna
# Date: 2025-07-25
# License: BSD-3-Clause
# =====================================================================================
# Description:
#   This script interactively generates a 2D velocity model for seismic applications.
#   Users can define horizons (as picked or interpolated files), choose interpolation
#   methods for each layer, preview the model, and save the result as a Fortran-order
#   binary float32 file. Supports various interpolation functions and custom expressions.
#
# Usage:
#   python vel_gen.py
#   # Follow the prompts to define grid, horizons, and velocity layers.
#
# Input:
#   - Horizon files: Picked horizons (z,x) or interpolated horizons (x,z)
#   - Layer velocity parameters: Constant or interpolated between top/bottom
#
# Output:
#   - Binary velocity model file (float32, Fortran-order, shape nz*nx)
#
# Features:
#   - Supports multiple interpolation methods: linear, spline, cubic, akima, etc.
#   - Custom velocity-depth functions via Python expressions
#   - Interactive preview of horizons and velocity profiles
#   - Fortran-order output for compatibility with seismic processing tools
#   - Robust input validation and error handling
#
# Example workflow:
#   1. Define grid size and spacing
#   2. Specify number of horizons and provide horizon files
#   3. Choose interpolation method for each horizon
#   4. For each layer, choose constant or interpolated velocity
#   5. Preview the velocity model
#   6. Save to binary file if satisfied
# ====================================================================================

import numpy as np
import matplotlib.pyplot as plt  
import os
from scipy.interpolate import (interp1d, UnivariateSpline, CubicSpline, 
                             Akima1DInterpolator, BSpline, make_interp_spline)
import warnings

warnings.filterwarnings("ignore")

def load_picks(filename):
    """Load picked horizon file (z,x format). Returns x, z arrays."""
    data = np.loadtxt(filename)
    z, x = data[:, 0], data[:, 1]
    return x, z

def interpolate_horizon(x, z, fx, lx, dx, method='linear'):
    """
    Interpolate horizon using specified method.
    x, z: input points
    fx, lx, dx: grid start, end, spacing
    method: interpolation type (string or number)
    Returns interpolated x, z arrays.
    """
    xi = np.arange(fx, lx + dx, dx)
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
    method = method_map.get(method, method)
    if method == "linear":
        f = interp1d(x, z, kind='linear', bounds_error=False,
                    fill_value=(z[0], z[-1]))
    elif method == "spline":
        f = UnivariateSpline(x, z, k=3, s=0)
    elif method == "poly3":
        f = np.poly1d(np.polyfit(x, z, 3))
    elif method == "cubic":
        f = CubicSpline(x, z)
    elif method == "akima":
        f = Akima1DInterpolator(x, z)
    elif method == "quadratic":
        f = interp1d(x, z, kind='quadratic', bounds_error=False,
                    fill_value=(z[0], z[-1]))
    elif method == "bspline":
        f = make_interp_spline(x, z, k=3)
    elif method == "nearest":
        f = interp1d(x, z, kind='nearest', bounds_error=False,
                    fill_value=(z[0], z[-1]))
    else:
        raise ValueError("Unknown interpolation method. Valid methods: linear, spline, poly3, cubic, akima, quadratic, bspline, nearest")
    zi = f(xi)
    return xi, zi

def preview_horizons(horizons, dx):
    """Plot all horizons for visual inspection."""
    plt.figure(figsize=(10, 6))
    for i, (_, z) in enumerate(horizons):
        x = np.arange(len(z)) * dx
        plt.plot(x, z, label=f"Horizon {i+1}")
    plt.gca().invert_yaxis()
    plt.xlabel("Distance (m)")
    plt.ylabel("Depth (m)")
    plt.title("Preview of All Horizons")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def preview_interp_functions(v_start, v_end, selected_types=None):
    """
    Preview selected velocity-depth interpolation functions.
    v_start: velocity at top
    v_end: velocity at bottom
    selected_types: list of function names to preview
    """
    x = np.linspace(0, 1, 500)
    functions = {
        'linear': lambda x: v_start + (v_end - v_start) * x,
        'log': lambda x: v_start + (v_end - v_start) * np.log1p(9 * x) / np.log(10),
        'exp': lambda x: v_start + (v_end - v_start) * (np.exp(2 * x) - 1) / (np.exp(2) - 1),
        'sqrt': lambda x: v_start + (v_end - v_start) * np.sqrt(x),
        'square': lambda x: v_start + (v_end - v_start) * x**2,
        'sigmoid': lambda x: v_start + (v_end - v_start) * (1 / (1 + np.exp(-10 * (x - 0.5)))),
        'bell': lambda x: v_start + (v_end - v_start) * (1 - np.abs(2 * x - 1))
    }
    if selected_types:
        functions = {k: v for k, v in functions.items() if k in selected_types}
    plt.figure(figsize=(10, 6))
    for name, func in functions.items():
        plt.plot(func(x), x, label=name, linewidth=2)
    plt.title("Interpolation Function Preview")
    plt.xlabel("Velocity (m/s)")
    plt.ylabel("Normalized depth")
    plt.gca().invert_yaxis()
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

def get_velocity_profile(model_type, npts, v_start, v_end, expr=None):
    """
    Generate velocity profile for a layer using specified interpolation.
    model_type: interpolation type (string)
    npts: number of depth samples
    v_start, v_end: velocity at top/bottom
    expr: custom Python expression (if model_type == 'custom')
    Returns velocity array of length npts.
    """
    t = np.linspace(0, 1, npts)
    if model_type == "linear":
        return v_start + (v_end - v_start) * t
    elif model_type == "log":
        return v_start + (v_end - v_start) * np.log1p(9 * t) / np.log(10)
    elif model_type == "exp":
        return v_start + (v_end - v_start) * (np.exp(2 * t) - 1) / (np.exp(2) - 1)
    elif model_type == "sqrt":
        return v_start + (v_end - v_start) * np.sqrt(t)
    elif model_type == "square":
        return v_start + (v_end - v_start) * t**2
    elif model_type == "sigmoid":
        return v_start + (v_end - v_start) * (1 / (1 + np.exp(-10 * (t - 0.5))))
    elif model_type == "bell":
        return v_start + (v_end - v_start) * (1 - np.abs(2 * t - 1))
    elif model_type == "custom":
        try:
            x = t
            return eval(expr, {"x": x, "np": np})
        except Exception as e:
            print("❌ Error in custom expression:", e)
            return None
    else:
        raise ValueError("Unknown model type")

def main():
    print("📌 Velocity Model Generator (vel_gen.py)")
    nx = int(input("Enter horizontal samples (nx): "))
    nz = int(input("Enter vertical samples (nz): "))
    dx = float(input("Enter dx (m): "))
    dz = float(input("Enter dz (m): "))
    background = float(input("Enter background velocity (default above first horizon): "))

    # Initialize velocity model with background value
    vel_model = np.full((nz, nx), background, dtype=np.float32)

    # Input number of horizons
    while True:
        num_layers_input = input("How many horizons do you want to insert? ")
        if num_layers_input.isdigit():
            num_layers = int(num_layers_input)
            break
        else:
            print("❌ Please enter a valid integer for the number of horizons.")

    horizons = []

    # Input horizon files and interpolation
    for layer in range(num_layers):
        print(f"--- Horizon {layer+1} ---")
        fname = input("Enter horizon filename: ").strip()
        is_raw = input("Is this a picked (raw) horizon file [z,x]? \n y -- non-interpolated \n n -- interpolated (y/n): ").strip().lower() == 'y'

        if is_raw:
            fx = 0
            lx = (nx - 1) * dx
            x, z = load_picks(fname)
            while True:
                print("\nAvailable interpolation methods:")
                print("1. linear")
                print("2. spline")
                print("3. poly3 (not recommended due to underfitting)")
                print("4. cubic")
                print("5. akima")
                print("6. quadratic")
                print("7. bspline")
                print("8. nearest")
                method = input("Choose method (number or name): ").strip().lower()
                x_interp, z_interp = interpolate_horizon(x, z, fx, lx, dx, method)
                horizons.append((x_interp, z_interp))
                preview_horizons(horizons, dx)
                confirm = input("✅ Are horizons OK? (y to continue): ").strip().lower()
                if confirm == 'y':
                    break
                else:
                    horizons.pop()
        else:
            x_interp, z_interp = np.loadtxt(fname, unpack=True)
            horizons.append((x_interp, z_interp))
            preview_horizons(horizons, dx)
            confirm = input("✅ Are horizons OK? (y to continue): ").strip().lower()
            if confirm != 'y':
                print("❌ Aborting. Please fix horizon input.")
                return

    # Add bottom horizon at model base
    horizons.append((np.arange(nx) * dx, np.full(nx, nz * dz)))

    # Layer velocity assignment
    for i in range(num_layers):
        top = horizons[i][1]
        bot = horizons[i+1][1]
        mask = np.ones_like(vel_model, dtype=bool)
        for j in range(nx):
            ztop_idx = int(top[j] // dz)
            zbot_idx = int(bot[j] // dz)
            if ztop_idx >= zbot_idx:
                continue
            mask[ztop_idx:zbot_idx, j] = False

        use_const = input(f"Use constant velocity for layer {i+1}? (y/n): ").strip().lower() == 'y'
        if use_const:
            vval = float(input("Enter constant velocity: "))
            vel_model[~mask] = vval
        else:
            v_start = float(input("Enter velocity at top: "))
            v_end = float(input("Enter velocity at bottom: "))
            print("\nAvailable interpolation types:")
            print("1. linear")
            print("2. log")
            print("3. exp")
            print("4. sqrt")
            print("5. square")
            print("6. sigmoid")
            print("7. bell")
            print("8. custom (e.g. x**0.5 + 1550)")
            print("\nYou can enter multiple types to preview (e.g. '2 4' or 'log sqrt')")
            preview_choice = input("Enter one or more interpolation types: ").strip().lower()
            type_map = {'1': 'linear', '2': 'log', '3': 'exp', '4': 'sqrt',
                        '5': 'square', '6': 'sigmoid', '7': 'bell', '8': 'custom'}
            preview_types = []
            for choice in preview_choice.split():
                if choice in type_map:
                    preview_types.append(type_map[choice])
                else:
                    preview_types.append(choice)
            preview_interp_functions(v_start, v_end, preview_types)
            model_type = input("\nNow choose one type for interpolation: ").strip().lower()
            model_type = type_map.get(model_type, model_type)
            expr = None
            if model_type == 'custom':
                expr = input("Enter custom Python expression using 'x' or 't' (e.g. x**0.5 + 1550): ")
            for j in range(nx):
                ztop_idx = int(top[j] // dz)
                zbot_idx = int(bot[j] // dz)
                npts = zbot_idx - ztop_idx
                if npts <= 1:
                    continue
                profile = get_velocity_profile(model_type, npts, v_start, v_end, expr)
                vel_model[ztop_idx:zbot_idx, j] = profile

    # Preview velocity model
    preview = input("👀 Do you want to preview the current velocity model? (y/n): ").strip().lower()
    if preview == 'y':
        vel_model_plot = vel_model.reshape((nz, nx), order='F')
        x = np.arange(nx) * dx
        z = np.arange(nz) * dz
        plt.figure(figsize=(10, 6))
        plt.imshow(vel_model_plot, extent=[x[0], x[-1], z[-1], z[0]], cmap='jet', aspect='auto')
        plt.colorbar(label='Velocity (m/s)')
        plt.xlabel("Distance (m)")
        plt.ylabel("Depth (m)")
        plt.title("Velocity Model Preview")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    # Save velocity model to binary file
    save = input("💾 Save this velocity model to binary file? (y/n): ").strip().lower()
    if save == 'y':
        fname = input("Enter output filename (no extension): ").strip()
        with open(fname, 'wb') as f:
            vel_model.T.astype(np.float32).tofile(f)
        print(f"✅ Velocity model saved to '{fname}' (Float32 binary).")
    else:
        print("⚠️ Model not saved.")

if __name__ == '__main__':
    main()
