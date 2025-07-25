# residuo_extract.py
# Author: Lining YANG @ CNR-ISMAR Bologna
# Date: 2025-07-17
# Last Modified: 2025-07-25
# License: BSD-3-Clause
#
# =====================================================================================
# Description:
#   This script extracts trace and depth pairs from a 'residuotot.dat' file.
#   It searches for lines containing only '1', and then takes the next line's
#   first two columns as trace and depth. The results are saved to 'trace_depth.dat'.
#
# Example usage:
#   python residuo_extract.py
#
# Input file format (residuotot.dat):
#   1
#   15000 1000 30.5 -0.0123
#   1
#   15500 1200 28.7 -0.0110
#   ...
#
# Output file format (trace_depth.dat):
#   15000 1000
#   15500 1200
#   ...
# =====================================================================================

import os

input_file = 'residuotot.dat'
output_file = 'trace_depth.dat'

# Check if input file exists
if not os.path.exists(input_file):
    print(f"ERROR: File '{input_file}' not found! Current directory: {os.getcwd()}")
    exit()

trace_depth_pairs = []

# Read and process input file
with open(input_file, 'r') as f_in:
    lines = [line.strip() for line in f_in.readlines()]  # Remove leading/trailing whitespace
    print(f"DEBUG: Read {len(lines)} lines from input file")

    # Iterate through all lines, skip empty lines and single '1' lines
    for i in range(len(lines)):
        line = lines[i]
        if line == '1' and i + 1 < len(lines):  # Current line is '1' and next line exists
            data_line = lines[i + 1]
            parts = data_line.split()
            if len(parts) >= 2:
                trace_depth_pairs.append((parts[0], parts[1]))

# Write output file
with open(output_file, 'w') as f_out:
    for trace, depth in trace_depth_pairs:
        f_out.write(f"{trace} {depth}\n")

# Print top 10 results for quick check
print("\nTop 10 Trace-Depth Pairs:")
print("Trace\tDepth")
for trace, depth in trace_depth_pairs[:10]:
    print(f"{trace}\t{depth}")

print(f"\nExtraction complete: {len(trace_depth_pairs)} pairs saved to '{output_file}'")
