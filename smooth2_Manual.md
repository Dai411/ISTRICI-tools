
# smooth2: 2D Smoothing Tool

`smooth2` is a Python-based tool for smoothing 2D float32 arrays, designed to emulate and extend the `smooth2` command in Seismic Unix (SU), with added visualization and sweep capabilities.

---

## 📌 Usage

```bash
python smooth2_sweep.py <input_file> --n1 <n1> --n2 <n2> [optional arguments]
```
## 📬 Example

```bash
python smooth2.py input.bin output.bin --n1 500 --n2 300 --r1 1.0 --r2 0.5 --win 100 400 50 200 --efile error.txt --plot --save-plot comparison.png
```

### Required Arguments

- `input_file`: Binary float32 input file
- `--n1`: Number of samples in the first (fast) dimension (e.g., depth)
- `--n2`: Number of samples in the second (slow) dimension (e.g., traces)

### Optional Arguments

| Argument | Description |
|----------|-------------|
| `--r1-range` | Range of smoothing parameters in the 1st dimension |
| `--r2-range` | Range of smoothing parameters in the 2nd dimension |
| `--win`      | Smoothing window: `[i1_start, i1_end, i2_start, i2_end]` |
| `--save-dir` | Directory to save smoothed results |
| `--plot-top` | Number of top results (lowest error) to plot (default `12`) |

---

## 🔍 Recommended r1/r2 Values

- Suggested range for both `r1` and `r2`: **1 to 20**
- Higher values yield smoother output, but can increase smoothing error
- Typically, values around 5–15 give good results. Acceptable relative error: `0.01 ~ 0.1`

---

## 🔬 Comparison with Seismic Unix

| Feature | Seismic Unix `smooth2` | This Script |
|--------|--------------------------|-------------|
| Windowed smoothing | ✅ | ✅ |
| `rw` (window edge smoothing) | ✅ (`rw=0` by default) | ❌ Not implemented |
| Error file output | ✅ (`efile`) | ✅ (command-line output) |
| Visualization | ❌ | ✅ (`matplotlib` subplots) |
| Parameter sweeping | ❌ | ✅ (evaluates all `r1/r2` combinations) |

> Note: The `rw` parameter in SU is used to soften the window edges. This implementation uses hard window boundaries only.

---

## 📐 Mathematical Principle

The smoothing is formulated as a damped least squares problem:

$$
\min_s \|s - d\|^2 + r_1 \|D_1 s\|^2 + r_2 \|D_2 s\|^2
$$

Where:

- $d$ is the original data
- $s$ is the smoothed data
- $D_1$, $D_2$ are finite-difference operators
- $r_1$, $r_2$ are regularization weights

This is solved efficiently using sparse matrix techniques via `scipy.sparse.linalg.spsolve`.

---

## 🖼 Visualization

The tool automatically selects the top `N` best combinations (lowest error) and displays:

- Original data
- Smoothed result
- Error map

Each group contains 3 subplots and is arranged in rows for easy comparison.

---
