#!/usr/bin/env python3
# Written by Lining YANG @ CNR-ISMAR, BOLOGNA, ITALY
# Date: 2025-06-27 17:40
# Licensed under the BSD 3-Clause License

"""
vel_sub_const.py - Velocity Model Value Substitution Tool

This script allows users to substitute values in a 2D velocity model (float32 Fortran-style binary)
by exact value, by float tolerance, or by value range. It supports:
  - Exact value replacement
  - Float tolerance replacement (for floating-point precision issues)
  - Range replacement (replace all values within a specified interval)
The script provides data size checking, summary of replaced points, and optional visualization
of the original, substituted, and difference maps.

Usage:
  - Run the script and follow the prompts to input file parameters and substitution options.
  - The script is compatible with Python 3.x and requires numpy and matplotlib.
"""

import numpy as np
import matplotlib.pyplot as plt

def main():
    while True:
        # 1. User input for parameters
        nx = int(input("Enter nx (number of horizontal samples): "))
        nz = int(input("Enter nz (number of vertical samples): "))
        filename = input("Enter input binary filename: ").strip()
        output_filename = input("Enter output filename: ").strip()

        # 2. Read binary data
        try:
            with open(filename, 'rb') as f:
                data = np.fromfile(f, dtype=np.float32, count=nx * nz)
        except FileNotFoundError:
            print(f"File '{filename}' not found.")
            continue

        # 3. Check data size
        if data.size != nx * nz:
            print(f"❌ Data size mismatch! Expected {nx * nz}, got {data.size}.")
            choice = input("Type 'r' to re-enter parameters, 'f' to change file, or 'q' to quit: ").strip().lower()
            if choice == 'q':
                return
            else:
                continue
        else:
            break

    # 4. Ask user for substitution mode
    while True:
        print("Choose substitution mode:")
        print("1. Exact match (==)")
        print("2. Float tolerance (abs diff < tol)")
        print("3. Range replace (min <= value <= max)")
        print("h. Help: What is float tolerance mode?")
        mode = input("Enter 1, 2, 3, or h: ").strip().lower()
        if mode == 'h':
            print("\n--- Float Tolerance Mode Help ---")
            print("In float tolerance mode, all values within a specified tolerance of the target value will be replaced.")
            print("For example, if target=1500.0, tol=0.002, then values between 1499.998 and 1500.002 will be replaced.")
            print("Example:")
            print("  data = [1500.0, 1500.001, 1499.999, 1520.0]")
            print("  target = 1500.0, tol = 0.002, new_value = 1600.0")
            print("  Result: [1600.0, 1600.0, 1600.0, 1520.0]\n")
            continue
        elif mode in ('1', '2', '3'):
            break
        else:
            print("Invalid input. Please enter 1, 2, 3, or h.")

    if mode == '2':
        target = float(input("Enter value to replace: "))
        new_value = float(input("Enter new value: "))
        tol = float(input("Enter tolerance (e.g., 1e-3): "))
        mask = np.abs(data - target) < tol
        data_sub = data.copy()
        data_sub[mask] = new_value
    elif mode == '3':
        min_val = float(input("Enter minimum value of range: "))
        max_val = float(input("Enter maximum value of range: "))
        new_value = float(input("Enter new value: "))
        mask = (data >= min_val) & (data <= max_val)
        data_sub = data.copy()
        data_sub[mask] = new_value
    else:
        target = float(input("Enter value to replace: "))
        new_value = float(input("Enter new value: "))
        data_sub = data.copy()
        data_sub[data_sub == target] = new_value

    # 5. Write to new file
    with open(output_filename, 'wb') as f:
        data_sub.astype(np.float32).tofile(f)
    print(f"Substitution done and saved to '{output_filename}'.")

    # Count replaced points
    num_replaced = np.sum(data != data_sub)
    percent_replaced = num_replaced / data.size * 100
    print(f"Replaced {num_replaced} points ({percent_replaced:.2f}% of total).")

    # 6. Ask user if they want to show comparison plot
    show_plot = input("Show comparison plot? (y/n): ").strip().lower()
    if show_plot == 'y':
        data_2d = data.reshape((nz, nx), order='F')
        data_sub_2d = data_sub.reshape((nz, nx), order='F')
        diff = data_sub_2d - data_2d

        vmax = np.max(np.abs(diff))
        plt.figure(figsize=(15, 5))
        plt.subplot(1, 3, 1)
        plt.imshow(data_2d, cmap='jet', aspect='auto')
        plt.title('Original')
        plt.colorbar()
        plt.subplot(1, 3, 2)
        plt.imshow(data_sub_2d, cmap='jet', aspect='auto')
        plt.title('Substituted')
        plt.colorbar()
        plt.subplot(1, 3, 3)
        plt.imshow(diff, cmap='bwr', aspect='auto', vmin=-vmax, vmax=vmax)
        plt.title('Difference = Substituted - Original \n'
                 "Red: Substituted > Original\n"
                 "Blue: Substituted < Original")
        plt.colorbar()
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    main()
