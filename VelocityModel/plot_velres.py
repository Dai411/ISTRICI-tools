#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_velres.py - Interactive Velocity Residual Visualization Tool

Author: Lining Yang @ CNR-ISAMR Bologna
Created: 2025-07-15 18:30
Last Modified: 2025-07-15

Description:
This script loads velocity residual data (either ASCII text or binary format), 
and displays it as an interactive plot. Users can:
1. Switch between RGB/HSV colormaps using 'r' and 'h' keys
2. Support both text and binary input files
3. Customize plot dimensions interactively

Usage:
1. Run the script: python plot_velres.py
2. Enter file name and dimensions when prompted
3. In the plot window:
   - Press 'r' to cycle through RGB colormaps
   - Press 'h' to cycle through HSV colormaps
"""

import numpy as np
import matplotlib.pyplot as plt

def input_with_default(prompt, default, type_cast):
    """Helper function for user input with default values."""
    try:
        user_input = input(f"{prompt} (default: {default}): ").strip()
        return type_cast(user_input) if user_input else default
    except ValueError:
        print(f"[WARNING] Invalid input. Using default value: {default}")
        return default

def load_data(filename, expected_size):
    """Load data from either text or binary file."""
    try:
        # First try loading as text file
        data = np.loadtxt(filename)
        print(f"[STATUS] Successfully loaded text file: {filename}")
    except:
        try:
            # Fall back to binary format (32-bit float)
            data = np.fromfile(filename, dtype=np.float32)
            print(f"[STATUS] Loaded binary file: {filename} (32-bit float)")
        except Exception as e:
            print(f"[ERROR] Failed to load file '{filename}': {str(e)}")
            exit(1)
    
    # Validate data size
    if data.size != expected_size:
        print(f"[ERROR] Data size mismatch. Expected: {expected_size}, Got: {data.size}")
        exit(1)
    return data

# ==================== MAIN SCRIPT ====================
print("="*50)
print("Velocity Residual Visualization Tool")
print("="*50 + "\n")

# 1. User input
filename = input_with_default("Enter data file name\nASCII or Binary", "velres.dat", str)
nz = input_with_default("Enter number of depth samples (n1)", 321, int)
nx = input_with_default("Enter number of CDPs (n2)", 701, int)

# 2. Load and validate data
print("\n[STATUS] Loading data...")
data = load_data(filename, nx * nz)
res_grid = data.reshape((nx, nz)).T  # Reshape and transpose

# 3. Define colormaps
rgb_cmaps = ['jet', 'viridis', 'seismic', 'coolwarm', 'hot']      # RGB colormaps
hsv_cmaps = ['hsv', 'twilight', 'rainbow', 'twilight_shifted', 'prism']  # HSV colormaps

# 4. Create plot
print("[STATUS] Creating visualization...")
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(
    res_grid,
    cmap=rgb_cmaps[0],
    aspect='auto',
    origin='upper',
    extent=[1, nx, 0, nz]
)
cbar = fig.colorbar(im, ax=ax)
cbar.set_label("Velocity Residual (m/s)")

ax.set_title(f"Velocity Residual from '{filename}'\nPress 'r' (RGB) or 'h' (HSV) to change colormap")
ax.set_xlabel("CDP Index (n2)")
ax.set_ylabel("Depth Index (n1, increasing downward)")

# 5. Keyboard interaction
def on_key(event):
    """Handle key press events for colormap switching."""
    global im, cbar
    if event.key.lower() == 'r':  # RGB colormaps
        current_cmap = im.get_cmap().name
        if current_cmap in rgb_cmaps:
            idx = (rgb_cmaps.index(current_cmap) + 1) % len(rgb_cmaps)
        else:
            idx = 0
        new_cmap = rgb_cmaps[idx]
        print(f"[ACTION] Switched to RGB colormap: {new_cmap}")
    elif event.key.lower() == 'h':  # HSV colormaps
        current_cmap = im.get_cmap().name
        if current_cmap in hsv_cmaps:
            idx = (hsv_cmaps.index(current_cmap) + 1) % len(hsv_cmaps)
        else:
            idx = 0
        new_cmap = hsv_cmaps[idx]
        print(f"[ACTION] Switched to HSV colormap: {new_cmap}")
    else:
        return
    
    im.set_cmap(new_cmap)
    cbar.remove()
    cbar = fig.colorbar(im, ax=ax)
    fig.canvas.draw_idle()

fig.canvas.mpl_connect('key_press_event', on_key)
print("[STATUS] Visualization ready. Press 'r' or 'h' to change colormaps.")
plt.tight_layout()
plt.show()
    
print("\n🔴 Thanks for using and please remember: \n   - The sky over Manchester is always red! ")
print("   - Glory Glory MAN United! ⚽")
