#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Velocity Model Binary Preview Tool

Author: Lining YANG
Created: 2025-06-17 01:04
Last Modified: 2025-06-17 01:04
Version: 1.0.0
License: BSD 3-Clause License

Description:
    You may be confused about the storage order of your seismic velocity models.
    This tool helps you preview and visualize the data, detect the storage order,
    and understand the structure of your velocity models.
    Interactive tool for previewing velocity model binary files with specialized
    storage order detection for seismic velocity models.
"""

import numpy as np
import matplotlib.pyplot as plt # type: ignore
import argparse
import random

def preview_1d(data, max_elements=500):
    """Preview data as a 1D array"""
    preview_data = data[:max_elements]
    
    plt.figure(figsize=(12, 6))
    
    # Data Preview
    plt.subplot(1, 2, 1)
    plt.plot(preview_data, 'b-', linewidth=0.5)
    plt.title(f"First {len(preview_data)} Elements")
    plt.xlabel("Index")
    plt.ylabel("Velocity Value")
    plt.grid(True)
    
    # Value Distribution - Histogram
    plt.subplot(1, 2, 2)
    plt.hist(preview_data, bins=50, alpha=0.7)
    plt.title("Value Distribution")
    plt.xlabel("Velocity Value")
    plt.ylabel("Frequency")
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()

def plot_velocity_model(matrix, title):
    """Specialized visualization for velocity models"""
    plt.figure(figsize=(12, 6))
    
    # Main Heatmap
    plt.subplot(1, 2, 1)
    im = plt.imshow(matrix, aspect='auto', cmap='viridis',
                  extent=[0, matrix.shape[1], matrix.shape[0], 0])
    plt.colorbar(im, label='Velocity (m/s)')
    plt.xlabel('Trace Position (x)')
    plt.ylabel('Depth (z)')
    plt.title(title)
    
    # Variance Analysis
    plt.subplot(1, 2, 2)
    plt.plot(np.var(matrix, axis=0), 'r-', label='Horizontal variance')
    plt.plot(np.var(matrix, axis=1), 'b-', label='Vertical variance')
    plt.legend()
    plt.xlabel('Index')
    plt.ylabel('Variance')
    plt.title('Variance Analysis')
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()

def auto_detect_velocity_model(data, nz, nx):
    """Optimized auto-detection for velocity models"""
    try:
        # Try to reshape the data into both C and Fortran order
        matrix_c = data[:nz*nx].reshape((nz, nx), order='C')  # Rows First
        # C order: rows represent depth/z-direction, columns represent horizontal/x-direction
        matrix_f = data[:nz*nx].reshape((nz, nx), order='F')  # Columns First
        # Fortran order: columns represent depth/z-direction, rows represent horizontal/x-direction
        
        # Claculate variance ratios for both orders
        def calculate_variance_ratio(mat):
            vertical_var = np.mean(np.var(mat, axis=1))  # Variance in vertical direction (depth)
            horizontal_var = np.mean(np.var(mat, axis=0))  # Variance in horizontal direction (trace positions)
            return vertical_var / (horizontal_var + 1e-8)  # Avoid division by zero
        
        c_ratio = calculate_variance_ratio(matrix_c)
        f_ratio = calculate_variance_ratio(matrix_f)
        
        print(f"[Debug] C order - Vertical/Horizontal variance ratio: {c_ratio:.2f}")
        print(f"[Debug] F order - Vertical/Horizontal variance ratio: {f_ratio:.2f}")
        
        # Determine the order based on variance ratios
        # If C order has higher vertical variance, it's likely depth/z-direction
        # If F order has higher vertical variance, it's likely depth/z-direction
        # We use a threshold to avoid noise in variance calculations
        if c_ratio > f_ratio:
            return 'F', min(c_ratio / (c_ratio + f_ratio + 1e-8), 0.99)  # Fortran Order
        else:
            return 'C', min(f_ratio / (c_ratio + f_ratio + 1e-8), 0.99)  # C Order
            
    except Exception as e:
        print(f"❌ Auto-detection error: {str(e)}")
        return 'Error', 0.0

def interactive_mode():
    """Interactive mode for velocity model preview"""
    print("\n" + "="*60)
    print("📊 Velocity Model Binary Preview Tool")
    print("="*60)
    
    # Obtain user input for file path and dimensions
    file_path = input("Binary file path: ")
    nz = int(input("Number of depth samples (nz): "))
    nx = int(input("Number of trace positions (nx): "))
    
    # Load the binary file
    try:
        data = np.fromfile(file_path, dtype=np.float32)
        print(f"✅ Loaded {len(data)} elements from {file_path}")
        
        if len(data) < nz * nx:
            print(f"⚠️ Warning: File contains only {len(data)} elements, "
                  f"but {nz}x{nx} = {nz*nx} required")
            if input("Continue with partial data? [y/N]: ").lower() != 'y':
                return
    except Exception as e:
        print(f"❌ Error loading file: {str(e)}")
        return
    
    # Main interactive loop
    while True:
        print("\nOptions:")
        print("1. Preview in C order (row-major)")
        print("2. Preview in Fortran order (column-major)")
        print("3. Compare both orders")
        print("4. Auto-detect order (velocity model optimized)")
        print("5. Change dimensions")
        print("6. Exit")
        
        choice = input("Select an option (1-6): ").strip()
        
        if choice == '1':
            print("\n🔍 Previewing in C order...")
            matrix = data[:nz*nx].reshape((nz, nx), order='C')
            plot_velocity_model(matrix, "Velocity Model (C Order)")
        elif choice == '2':
            print("\n🔍 Previewing in Fortran order...")
            matrix = data[:nz*nx].reshape((nz, nx), order='F')
            plot_velocity_model(matrix, "Velocity Model (Fortran Order)")
        elif choice == '3':
            print("\n🔍 Comparing both orders...")
            plt.figure(figsize=(12, 6))
            
            # C Order
            plt.subplot(1, 2, 1)
            matrix_c = data[:nz*nx].reshape((nz, nx), order='C')
            plt.imshow(matrix_c, aspect='auto', cmap='viridis',
                      extent=[0, nx, nz, 0])
            plt.colorbar(label='Velocity (m/s)')
            plt.title("C Order (Row-major)")
            plt.xlabel("Trace (x)")
            plt.ylabel("Depth (z)")
            
            # Fortran Order
            plt.subplot(1, 2, 2)
            matrix_f = data[:nz*nx].reshape((nz, nx), order='F')
            plt.imshow(matrix_f, aspect='auto', cmap='viridis',
                      extent=[0, nx, nz, 0])
            plt.colorbar(label='Velocity (m/s)')
            plt.title("Fortran Order (Column-major)")
            plt.xlabel("Trace (x)")
            plt.ylabel("Depth (z)")
            
            plt.tight_layout()
            plt.show()
        elif choice == '4':
            print("\n🔍 Auto-detecting order for velocity model...")
            order, confidence = auto_detect_velocity_model(data, nz, nx)
            
            print(f"\nResult: Suggested order = {order} (confidence: {confidence:.1%})")
            if order == 'F':
                print("   - This suggests Fortran (column-major) order")
                print("   - Columns represent depth/z-direction")
                print("   - Rows represent horizontal/x-direction")
            elif order == 'C':
                print("   - This suggests C (row-major) order")
                print("   - Rows represent depth/z-direction")
                print("   - Columns represent horizontal/x-direction")
            else:
                print("   - Unable to determine order with confidence")
                print("   - Please check dimensions or use visual comparison")
        elif choice == '5':
            print("\n🔄 Changing dimensions...")
            nz = int(input("New number of depth samples (nz): "))
            nx = int(input("New number of trace positions (nx): "))
            print(f"Dimensions updated to {nz}x{nx}")
        elif choice == '6':
            print("\n🔴 Thanks for using. Remember: The sky over Manchester is always red! 🔴")
            print("   - Glory Glory MAN United! ⚽")  
            break
        else:
            print("Invalid choice, please enter a number between 1-6")
        
        # Display current data status
        print(f"\nCurrent data: {len(data)} elements, dimensions {nz}x{nx}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Velocity model binary preview tool")
    parser.add_argument("--non-interactive", action='store_true',
                        help="Run in non-interactive mode (coming soon)")
    
    args = parser.parse_args()
    
    if args.non_interactive:
        print("Non-interactive mode coming soon!")
    else:
        interactive_mode()

