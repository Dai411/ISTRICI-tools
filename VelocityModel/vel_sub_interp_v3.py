#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================================
# vel_sub_interp_v3.py
# Author: Lining YANG @ CNR-ISMAR, BOLOGNA, ITALY
# Date: 2025-06-06 16:24
# Last Modified: 2025-07-25
# License: BSD-3-Clause
# =====================================================================================
# v3 version: more interpolation functions and improved visualization
#
# Description:
#   This script replaces constant velocity values in a 2D velocity model (float32, Fortran-order)
#   with interpolated values using various interpolation functions.
#   Users can preview multiple interpolation functions, select one, and visualize the results.
#   The output is saved as a new binary velocity model file.
#
# Usage:
#   python vel_sub_interp_v3.py
#   # Follow the prompts for grid size, input file, target value, interpolation range, and output file suffix.
#
# Input:
#   - Velocity model file (float32 binary, Fortran-order, shape nz*nx)
#   - Target value to substitute (e.g. 3500)
#   - Interpolation range (start/end values)
#
# Output:
#   - New velocity model file with substituted/interpolated values
#   - Side-by-side visualization of original and modified models
#
# Features:
#   - Supports multiple interpolation functions: linear, log, exp, sqrt, square, sigmoid, bell, custom
#   - Interactive preview and selection of interpolation functions
#   - Robust input validation and error handling
#   - Visualization using matplotlib (supports Chinese font if available)
#
# =====================================================================================

import numpy as np  # Numerical operations
import matplotlib.pyplot as plt  # Visualization
import os
import matplotlib.font_manager as fm  # Font manager for custom fonts
import warnings

# Ignore font warnings (e.g. missing Chinese glyphs)
warnings.filterwarnings("ignore", category=UserWarning)

# === Load custom font (modify path as needed) ===
font_path = "/home/rock411/fonts/NotoSansCJKsc-Black.otf"
my_font = fm.FontProperties(fname=font_path)

# === User input parameters ===
""" We can set default values here, but they will be overridden by user input."""
#nx = 701  # Horizontal sampling points
#nz = 321  # Vertical sampling points
#dx = 100  # Horizontal sampling interval
#dz = 25   # Vertical sampling interval

# The default values can be set here, in [], press Enter to use them. 
print("[INFO] Press Enter to use default values, or input your own:")
nx = int(input("Please input horizontal sampling numbers nx [701]: ") or 701)
nz = int(input("Please input vertical sampling numbers nz [321]: ") or 321)
dx = int(input("Please input horizontal sampling resolution dx [100]: ") or 100)
dz = int(input("Please input vertical sampling resolution dz [25]: ") or 25)
filename = input("Please input velocity model file (Float32) e.g. vfile4l_15_16_20_50:\n").strip()
target_value = float(input("The constant velocity you want to substitute (e.g. 3500): "))
interp_start = float(input("The start value for interpolation (e.g. 3000): "))
interp_end = float(input("The end value for interpolation (e.g. 4000): "))

suffix = input("Please type the suffix of the new file:\n")
output_filename = filename + '_interp' + suffix

# Check if input file exists
if not os.path.exists(filename):
    print(f"❌ No file '{filename}' found!")
    exit()

# Load velocity model (float32, Fortran-order)
with open(filename, 'rb') as f:
    data = np.fromfile(f, dtype=np.float32, count=nx * nz)
vel_original = np.reshape(data, (nz, nx), order='F')
vel_modified = vel_original.copy()

# === Interpolation function definitions ===
def get_function(name, start, end, expr=None):
    """
    Returns interpolated velocity profile for normalized depth x in [0,1].
    name: interpolation type
    start, end: velocity at top/bottom
    expr: custom Python expression (if name == 'custom')
    """
    x = np.linspace(0, 1, 500)
    if name == "linear":
        y = start + (end - start) * x
    elif name == "log":
        y = start + (end - start) * np.log1p(9 * x) / np.log(10)
    elif name == "exp":
        y = start + (end - start) * (np.exp(2 * x) - 1) / (np.exp(2) - 1)
    elif name == "sqrt":
        y = start + (end - start) * np.sqrt(x)
    elif name == "square":
        y = start + (end - start) * x**2
    elif name == "sigmoid":
        y = start + (end - start) * (1 / (1 + np.exp(-10 * (x - 0.5))))
    elif name == "bell":
        y = start + (end - start) * (1 - np.abs(2 * x - 1))
    elif name == "custom":
        try:
            y = eval(expr, {"x": x, "np": np})
        except Exception as e:
            print("❌ Error in custom expression:", e)
            return None
    else:
        raise ValueError("Unknown function type")
    return x, y

# === Interpolation function selection and preview ===
function_map = {
    "1": "linear", "2": "log", "3": "exp", "4": "sqrt",
    "5": "square", "6": "sigmoid", "7": "bell", "8": "custom",
    "linear": "linear", "log": "log", "exp": "exp", "sqrt": "sqrt",
    "square": "square", "sigmoid": "sigmoid", "bell": "bell", "custom": "custom"
}

while True:
    print("\nAvailable interpolation types:")
    print("1. linear\n2. log\n3. exp\n4. sqrt\n5. square\n6. sigmoid\n7. bell\n8. custom (e.g. x**0.5 + 1550)")
    print("You can enter multiple types to preview (e.g. '2 4' or 'log sqrt')")

    user_inputs = input("Enter one or more interpolation types: ").strip().lower().split()
    selected_funcs = []
    custom_exprs = {}

    for user_input in user_inputs:
        func = function_map.get(user_input)
        if func is None:
            print(f"❌ Unknown type '{user_input}', skipping.")
            continue
        if func == "custom":
            expr = input("Enter custom expression in x (e.g. x**0.5 + 1550): ")
            custom_exprs[func] = expr
        selected_funcs.append(func)

    # === Function plot preview ===
    x_plot = np.linspace(0, 1, 500)
    plt.figure(figsize=(8, 4))
    for func in selected_funcs:
        expr = custom_exprs.get(func, None)
        try:
            _, y_plot = get_function(func, interp_start, interp_end, expr)
            plt.plot(x_plot, y_plot, label=func, linewidth=2)
        except:
            continue
    plt.title("Interpolation function comparison", fontproperties=my_font)
    plt.xlabel("Normalized depth (x)", fontproperties=my_font)
    plt.ylabel("Velocity (m/sec)", fontproperties=my_font)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # === Final choice ===
    choice_input = input("✅ Enter the interpolation type you want to use: ").strip().lower()
    final_choice = function_map.get(choice_input)
    if final_choice is None or final_choice not in selected_funcs:
        print("[INFO] ❌ Invalid choice. Please re-select.")
        continue
    final_expr = custom_exprs.get(final_choice, None)
    break

# === Get final interpolation profile (0-1 normalized) ===
interp_func = get_function(final_choice, interp_start, interp_end, final_expr)[1]

# === Interpolation substitution logic ===
for i in range(nx):
    column = vel_modified[:, i]
    indices = np.where(column == target_value)[0]
    if len(indices) < 2:
        continue
    di1 = indices[0]
    di2 = indices[-1]
    length = di2 - di1 + 1
    new_values = interp_func[:length]
    vel_modified[di1:di2 + 1, i] = new_values

# === Save new velocity model file ===
with open(output_filename, 'wb') as f:
    vel_modified.T.astype(np.float32).tofile(f)

print(f"\n[STATUS] ✅ Interpolation finished, new velocity model saved as: {output_filename}")

# === Visualization: original vs interpolated velocity model ===
x = np.arange(nx) * dx
z = np.arange(nz) * dz
fig, axs = plt.subplots(1, 2, figsize=(14, 6), facecolor='w')

im1 = axs[0].imshow(vel_original, extent=[x[0], x[-1], z[-1], z[0]],
                    cmap='jet', aspect='auto')
axs[0].set_title("Original velocity model", fontproperties=my_font)
axs[0].set_xlabel("Distance (m)", fontproperties=my_font)
axs[0].set_ylabel("Depth (m)", fontproperties=my_font)
axs[0].grid(True)
plt.colorbar(im1, ax=axs[0], label="Velocity (m/s)")

im2 = axs[1].imshow(vel_modified, extent=[x[0], x[-1], z[-1], z[0]],
                    cmap='jet', aspect='auto')
axs[1].set_title("Interpolated velocity model", fontproperties=my_font)
axs[1].set_xlabel("Distance (m)", fontproperties=my_font)
axs[1].set_ylabel("Depth (m)", fontproperties=my_font)
axs[1].grid(True)
plt.colorbar(im2, ax=axs[1], label="Velocity (m/s)")

plt.tight_layout()
plt.show()
