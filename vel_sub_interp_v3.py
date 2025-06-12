# Written by Lining YANG @ CNR-ISMAR, BOLOGNA, ITALY
# Date: 2025-06-06 16:24
# v3 version has more interporlation functions and better visualization
# This script is used to replace constant velocity values in a velocity model with interpolated values
# It allows users to select different interpolation functions and visualize the results

import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
import os
import matplotlib.font_manager as fm # type: ignore
import warnings

# If no need Chinese charcters in the preview part, ignore loading Chinese fonts part
# === 忽略字体警告（中文字符缺失）=== Ignore font warnings (Chinese characters missing) ===
warnings.filterwarnings("ignore", category=UserWarning) 

# === 加载中文字体 === Load Chinese fonts ===
font_path = "/home/rock411/fonts/NotoSansCJKsc-Black.otf"
my_font = fm.FontProperties(fname=font_path)

# === Input parameters === 用户输入参数 ===
nx = int(input("Please input horizontal sampling numbers nx:\n"))
nz = int(input("Please input vertical sampling numbers nz:\n"))
dx = int(input("Please input horizontal sampling resolution dx:\n"))
dz = int(input("Please input vertical sampling resolution dz:\n"))
filename = input("Please input vfile (Float32) e.g. vfile4l_15_16_20_50:\n").strip()
target_value = float(input("The constant velocity you want to substitute (e.g. 3500):\n"))
interp_start = float(input("The start value for interpolation (e.g. 3000):\n"))
interp_end = float(input("The end value for interpolation (e.g. 4000):\n"))

# === Can set default value like this ===
#nx = 701  # 
#nz = 321  # 
#dx = 100  # 
#dz = 25   # 

suffix = input("Please type the suffix of the new file:\n")
output_filename = filename + '_interp' + suffix

if not os.path.exists(filename):
    print(f"❌ No file '{filename}' found!")
    exit()

with open(filename, 'rb') as f:
    data = np.fromfile(f, dtype=np.float32, count=nx * nz)
vel_original = np.reshape(data, (nz, nx), order='F')
vel_modified = vel_original.copy()

# === Define interpolation parameters === 插值函数定义 === 
def get_function(name, start, end, expr=None):
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

# === Interpolation function select === 插值函数选择与图像对比 ===
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

    # === Function plot preview === 多函数绘图预览 ===
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
        print("❌ Invalid choice. Please re-select.")
        continue
    final_expr = custom_exprs.get(final_choice, None)
    break

# === Get the final interpolation value sequence (0-1) === 获取最终插值值序列（0-1） ===
interp_func = get_function(final_choice, interp_start, interp_end, final_expr)[1]

# === Interpolation replacement logic === 插值替换逻辑 ===
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

# === Rewrite new file ===
with open(output_filename, 'wb') as f:
    vel_modified.T.astype(np.float32).tofile(f)

print(f"\n✅ Interpolation finished, new vfile saved as: {output_filename}")

# === Visualization ===
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
