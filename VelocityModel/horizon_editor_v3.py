# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# horizon_editor_v3.py

"""
Introduction:
-------------
Horizon Editing Tool

Author: Lining YANG @ CNR-ISMAR, BOLOGNA, ITALY
Date: 2025-06-30 19:47
License: BSD 3-Clause License
Version: 3.0.0
SPDX-FileCopyrightText: 2025 Lining YANG <

This script provides an interactive tool to:
    1. Create a seismic canvas with specified dimensions.
    2. Load and visualize multiple horizon files (.txt or .dat).
    3. Allow vertical editing (dragging) of horizon points.
    4. Apply influence functions (linear, Gaussian, sigmoid) to nearby points.
    5. Visualize changes live with interpolation-aware weighting.
    6. Support saving of edited results.

Some tips:
    -- After you select a point on a line, the title will show the 'idx' of the point, ...
       you can use the ← → to switch to the neighbour points and use ↑ ↓ to adjust the ...
       value of the points. The operation through hot keys only change the value of ...
       selected points and the neighnouring points keep unchanged.
    -- The x value cannot be changed. Remember the x value is int from the interpolation.  

"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

class HorizonEditor:
    def __init__(self, root, nx=701, nz=321, dx=100, dz=25):
        self.root = root
        self.root.title("Horizon Editor")

        # Default parameters
        self.nx = nx
        self.nz = nz
        self.dx = dx
        self.dz = dz
        self.x = np.arange(nx) * dx
        self.z = np.arange(nz) * dz
        self.horizons = {}       # {name: z-values}
        self.original_z = {}
        self.lines = {}
        self.selected_line = None
        self.selected_idx = None
        self.dragging = False
        self.max_influence_ratio = 0.1
        self.weight_type = "linear"
        self.adjust_step = dz / 10
        self.history = {}
        self.show_original = False

        # Parameter window variables
        self.influence_var = tk.DoubleVar(value=self.max_influence_ratio)
        self.weight_var = tk.StringVar(value=self.weight_type)
        self.step_var = tk.DoubleVar(value=self.adjust_step)
        self.param_win = None

        # UI layout
        frame = tk.Frame(root)
        frame.pack(side='top', fill='x')
        btn_load = tk.Button(frame, text="Load Horizon File", command=self.load_horizon_dialog)
        btn_param = tk.Button(frame, text="Parameters", command=self.open_param_window)
        btn_save = tk.Button(frame, text="Save", command=self.save_horizons_dialog)
        btn_undo = tk.Button(frame, text="Undo", command=self.undo)
        btn_show = tk.Button(frame, text="Show Original", command=self.toggle_original)
        btn_load.pack(side='left', padx=5, pady=5)
        btn_param.pack(side='left', padx=5, pady=5)
        btn_save.pack(side='left', padx=5, pady=5)
        btn_undo.pack(side='left', padx=5, pady=5)
        btn_show.pack(side='left', padx=5, pady=5)

        # Label for selected horizon
        self.selected_label = tk.Label(root, text="Selected: None", fg="blue", font=("Arial", 12, "bold"))
        self.selected_label.pack(pady=(0, 5))

        # Shortcuts info
        shortcut_info = (
            "Shortcuts:\n"
            "F1: Load Horizon File    F2: Parameters    F3: Save    F4: Undo    F5: Show Original    q: Quit"
        )
        tk.Label(root, text=shortcut_info, fg="gray", font=("Arial", 10)).pack(pady=(0, 5))

        # Matplotlib embedding
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("motion_notify_event", self.on_drag)
        self.canvas.mpl_connect("button_release_event", self.on_release)

        self.color_map = plt.cm.tab10

        # Keyboard shortcuts
        root.bind("<F1>", lambda e: self.load_horizon_dialog())
        root.bind("<F2>", lambda e: self.open_param_window())
        root.bind("<F3>", lambda e: self.save_horizons_dialog())
        root.bind("<F4>", lambda e: self.undo())
        root.bind("<F5>", lambda e: self.toggle_original())
        root.bind("<Up>", lambda e: self.move_selected_point(1, axis='y'))
        root.bind("<Down>", lambda e: self.move_selected_point(-1, axis='y'))
        root.bind("<Left>", lambda e: self.move_selected_point(-1, axis='x'))
        root.bind("<Right>", lambda e: self.move_selected_point(1, axis='x'))
        root.bind("q", lambda e: root.quit())

        # For crosshair
        self.crosshair_v = None
        self.crosshair_h = None
        self.crosshair_big = tk.BooleanVar(value=False)
        btn_cross = tk.Checkbutton(frame, text="Big Crosshair", variable=self.crosshair_big, command=self._update_crosshair)
        btn_cross.pack(side='left', padx=5, pady=5)

    def load_horizon_dialog(self):
        paths = filedialog.askopenfilenames(title="Select Horizon File(s)", filetypes=[("DAT/TXT", "*.dat *.txt")])
        for path in paths:
            self.add_horizon(path)
        self.draw_horizons()

    def add_horizon(self, filepath):
        try:
            data = np.loadtxt(filepath)
            if data.shape[1] != 2:
                messagebox.showerror("Format Error", f"{filepath} does not have 2 columns")
                return
            z_vals = data[:, 1]
            if len(z_vals) != self.nx:
                messagebox.showerror("Length Mismatch", f"{filepath} length {len(z_vals)} does not match nx={self.nx}")
                return
            name = os.path.splitext(os.path.basename(filepath))[0]
            self.horizons[name] = z_vals.copy()
            self.original_z[name] = z_vals.copy()
            self.history[name] = [z_vals.copy()]
            print(f"✅ Loaded horizon '{name}' from {filepath}")
        except Exception as e:
            messagebox.showerror("Load Failed", f"Failed to load {filepath}: {e}")

    def draw_horizons(self):
        self.ax.clear()
        for i, (name, z_vals) in enumerate(self.horizons.items()):
            line, = self.ax.plot(self.x, z_vals, label=name, color=self.color_map(i % 10))
            self.lines[name] = line
            if self.show_original:
                original = self.original_z[name]
                self.ax.plot(self.x, original, linestyle='--', color=self.color_map(i % 10), alpha=0.4)
        self.ax.set_title("Click and drag horizon | Parameters | Save | Undo")
        self.ax.set_xlabel("Distance (m)")
        self.ax.set_ylabel("Depth (m)")
        self.ax.grid(True)
        self.ax.invert_yaxis()
        self.ax.legend()
        self.canvas.draw()

    def on_click(self, event):
        if not event.inaxes:
            return
        min_dist = float("inf")
        selected_line = None
        selected_idx = None
        for name, line in self.lines.items():
            z_vals = self.horizons[name]
            idx = np.argmin(np.abs(self.x - event.xdata))
            dist = abs(z_vals[idx] - event.ydata)
            if np.isscalar(dist) and dist < min_dist and dist < 50:
                selected_line = name
                selected_idx = idx
                min_dist = dist
        self.selected_line = selected_line
        self.selected_idx = selected_idx
        # Update label
        if self.selected_line is not None:
            self.selected_label.config(text=f"Selected: {self.selected_line} (idx={self.selected_idx})")
            print(f"\nSelected point in '{self.selected_line}': x = {self.x[self.selected_idx]:.1f}, depth = {self.horizons[self.selected_line][self.selected_idx]:.1f}")
            self.dragging = True
            self._update_crosshair()
            # Print drag params only once at drag start
            total_x_range = self.x[-1] - self.x[0]
            influence_range = self.max_influence_ratio * total_x_range
            print(f"Dragging params: ratio={self.max_influence_ratio:.4f}, range={influence_range:.2f}m, type={self.weight_type}")
        else:
            self.selected_label.config(text="Selected: None")
            self.dragging = False
            self._remove_crosshair()

    def on_drag(self, event):
        if not self.dragging or not self.selected_line or event.inaxes != self.ax:
            return
        new_z = event.ydata
        if new_z is None:
            return
        horizon = self.horizons[self.selected_line]
        idx = self.selected_idx
        current_z = horizon[idx]
        dz = new_z - current_z
        total_x_range = self.x[-1] - self.x[0]
        influence_range = self.max_influence_ratio * total_x_range
        is_endpoint = (idx == 0) or (idx == len(self.x) - 1)
        for i, xval in enumerate(self.x):
            dx_abs = abs(xval - self.x[idx])
            if dx_abs <= influence_range:
                norm_dist = dx_abs / influence_range
                w = self.get_weight(norm_dist)
                if is_endpoint and i == idx:
                    w = 1.0
                horizon[i] += dz * w
        self.lines[self.selected_line].set_ydata(horizon)
        self._update_crosshair()
        self.canvas.draw_idle()

    def on_release(self, event):
        if self.selected_line is not None and self.selected_idx is not None:
            self.history[self.selected_line].append(self.horizons[self.selected_line].copy())
        self.dragging = False
        # Print drag params at drag end
        if self.selected_line is not None:
            total_x_range = self.x[-1] - self.x[0]
            influence_range = self.max_influence_ratio * total_x_range
            print(f"Drag finished: ratio={self.max_influence_ratio:.4f}, range={influence_range:.2f}m, type={self.weight_type}")

    def get_weight(self, norm_dist):
        if norm_dist > 1.0:
            return 0.0
        if self.weight_type == "linear":
            return max(0, 1 - norm_dist)
        elif self.weight_type == "gauss":
            return np.exp(-(norm_dist**2) / (2 * (0.3)**2))
        elif self.weight_type == "sigmoid":
            return 1 / (1 + np.exp(12 * (norm_dist - 0.5)))
        else:
            return max(0, 1 - norm_dist)

    def open_param_window(self):
        if self.param_win is not None and self.param_win.winfo_exists():
            self.influence_var.set(self.max_influence_ratio)
            self.weight_var.set(self.weight_type)
            self.step_var.set(self.adjust_step)
            self.param_win.lift()
            return
        self.param_win = tk.Toplevel(self.root)
        self.param_win.title("Parameter Settings")
        tk.Label(self.param_win, text="Influence Ratio (0.01-0.5):").pack()
        tk.Scale(self.param_win, from_=0.01, to=0.5, resolution=0.01,
                 variable=self.influence_var, orient='horizontal').pack()
        tk.Label(self.param_win, text="Weight Function:").pack()
        ttk.Combobox(self.param_win, values=["linear", "gauss", "sigmoid"],
                     textvariable=self.weight_var, state="readonly").pack()
        tk.Label(self.param_win, text="Adjustment Step (dz):").pack()
        tk.Entry(self.param_win, textvariable=self.step_var).pack()
        tk.Button(self.param_win, text="Apply", command=self.apply_settings).pack(pady=5)

    def apply_settings(self):
        old_ratio = self.max_influence_ratio
        old_type = self.weight_type
        old_step = self.adjust_step
        self.max_influence_ratio = self.influence_var.get()
        self.weight_type = self.weight_var.get()
        self.adjust_step = self.step_var.get()
        print("\n✅ Parameters updated:")
        print(f"   Influence Ratio: {old_ratio:.4f} → {self.max_influence_ratio:.4f}")
        print(f"   Weight Function: {old_type} → {self.weight_type}")
        print(f"   Adjustment Step (dz): {old_step:.2f} → {self.adjust_step:.2f}")

    def save_horizons_dialog(self):
        dir_path = filedialog.askdirectory(title="Select Save Directory")
        if not dir_path:
            return
        try:
            for name, z_vals in self.horizons.items():
                save_name = f"{name}_edited.dat"
                save_path = os.path.join(dir_path, save_name)
                data_to_save = np.column_stack((self.x, z_vals))
                np.savetxt(save_path, data_to_save, fmt='%.6f %.6f')
            messagebox.showinfo("Save Successful", f"All horizons saved to:\n{dir_path}")
            print(f"All horizons saved to {dir_path}")
        except Exception as e:
            messagebox.showerror("Save Failed", f"Save failed: {e}")

    def undo(self):
        if self.selected_line is None:
            messagebox.showwarning("Warning", "No horizon selected, cannot undo.")
            return
        if len(self.history[self.selected_line]) <= 1:
            messagebox.showwarning("Warning", "No more actions to undo.")
            return
        self.history[self.selected_line].pop()
        prev_state = self.history[self.selected_line][-1]
        self.horizons[self.selected_line] = prev_state.copy()
        self.draw_horizons()
        print(f"Undo performed on '{self.selected_line}'.")

    def toggle_original(self):
        self.show_original = not self.show_original
        self.draw_horizons()
        print(f"Original horizon display toggled {'ON' if self.show_original else 'OFF'}")

    def _update_crosshair(self):
        """Update crosshair visibility based on toggle and selection."""
        if self.selected_line is not None and self.selected_idx is not None:
            self._draw_crosshair(self.x[self.selected_idx], self.horizons[self.selected_line][self.selected_idx])
        else:
            self._remove_crosshair()

    def _draw_crosshair(self, x, y):
        self._remove_crosshair()
        if self.crosshair_big.get():
            try:
                self.crosshair_v = self.ax.axvline(x, color='red', linestyle='--', linewidth=2.0, zorder=10)
                self.crosshair_h = self.ax.axhline(y, color='red', linestyle='--', linewidth=2.0, zorder=10)
            except Exception:
                self.crosshair_v = None
                self.crosshair_h = None
        else:
            try:
                self.crosshair_h = self.ax.axhline(y, color='red', linestyle='--', linewidth=1.2, zorder=10)
                self.crosshair_v = None
            except Exception:
                self.crosshair_h = None
                self.crosshair_v = None
        self.canvas.draw_idle()

    def _remove_crosshair(self):
        try:
            if self.crosshair_v is not None:
                self.crosshair_v.remove()
        except Exception:
            if self.crosshair_v is not None:
                self.crosshair_v.set_visible(False)
        self.crosshair_v = None
        try:
            if self.crosshair_h is not None:
                self.crosshair_h.remove()
        except Exception:
            if self.crosshair_h is not None:
                self.crosshair_h.set_visible(False)
        self.crosshair_h = None
        self.canvas.draw_idle()

    def move_selected_point(self, direction, axis='y'):
        if self.selected_line is None or self.selected_idx is None:
            return
        horizon = self.horizons[self.selected_line]
        if axis == 'y':
            horizon[self.selected_idx] -= direction * self.adjust_step
            self.lines[self.selected_line].set_ydata(horizon)
            print(f"Moved point idx={self.selected_idx} on '{self.selected_line}' (y) by {self.adjust_step * direction:+.2f}")
        elif axis == 'x':
            new_idx = self.selected_idx + direction
            if 0 <= new_idx < len(self.x):
                self.selected_idx = new_idx
                print(f"Selected idx={self.selected_idx}, x={self.x[self.selected_idx]:.1f}, depth={horizon[self.selected_idx]:.1f}")
                self.selected_label.config(text=f"Selected: {self.selected_line} (idx={self.selected_idx})")
        self._update_crosshair()
        self.canvas.draw_idle()

def ask_grid_params(root):
    """Show a dialog to input nx, nz, dx, dz in a single window."""
    def on_ok():
        try:
            nx = int(nx_var.get())
            nz = int(nz_var.get())
            dx = float(dx_var.get())
            dz = float(dz_var.get())
            if nx <= 0 or nz <= 0 or dx <= 0 or dz <= 0:
                raise ValueError
            result.extend([nx, nz, dx, dz])
            param_win.destroy()
        except Exception:
            messagebox.showerror("Input Error", "Please enter valid positive numbers for all fields.", parent=param_win)

    param_win = tk.Toplevel(root)
    param_win.title("Grid Parameters")
    param_win.geometry("300x230+800+400")
    result = []

    nx_var = tk.StringVar(value="701")
    nz_var = tk.StringVar(value="321")
    dx_var = tk.StringVar(value="100")
    dz_var = tk.StringVar(value="25")

    tk.Label(param_win, text="Number of horizontal samples (nx):").pack(pady=(10,0))
    tk.Entry(param_win, textvariable=nx_var).pack()
    tk.Label(param_win, text="Number of vertical samples (nz):").pack()
    tk.Entry(param_win, textvariable=nz_var).pack()
    tk.Label(param_win, text="Horizontal spacing (dx):").pack()
    tk.Entry(param_win, textvariable=dx_var).pack()
    tk.Label(param_win, text="Vertical spacing (dz):").pack()
    tk.Entry(param_win, textvariable=dz_var).pack()
    tk.Button(param_win, text="OK", command=on_ok).pack(pady=10)

    param_win.grab_set()
    root.wait_window(param_win)
    if not result:
        import sys
        sys.exit("No parameters entered. Exiting.")
    return result

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    nx, nz, dx, dz = ask_grid_params(root)
    root.deiconify()
    app = HorizonEditor(root, nx=nx, nz=nz, dx=dx, dz=dz)
    root.mainloop()
