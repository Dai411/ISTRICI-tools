
# 📘 Notes: C-style vs Fortran-style Data Layout

---

## 🧠 Key Differences in Memory Layout

| Feature                      | C-style (Row-major)                      | Fortran-style (Column-major)                      |
|-----------------------------|------------------------------------------|--------------------------------------------------|
| `reshape` default order     | `order='C'`                               | `order='F'`                                      |
| Storage pattern             | Row by row                               | Column by column                                |
| Common in seismic data      | ❌ Not recommended                        | ✅ Often used in velocity models (Fortran-style) |
| `imshow()` display control  | Requires `.T` for correct visual         | Direct display with `extent=[0,n2,n1,0]`         |
| Code example reshape        | `.reshape((n1, n2))`                     | `.reshape((n1, n2), order='F')`                  |

---

## 🔍 Example

Given a `3×2` matrix:

```
Original Matrix A:

[[ 1, 4 ],
 [ 2, 5 ],
 [ 3, 6 ]]
```

### ✅ Fortran-style storage (column-major):

Memory layout becomes:

```
[1, 2, 3, 4, 5, 6]  ← stored column by column
```

```python
A = np.reshape([1, 2, 3, 4, 5, 6], (3, 2), order='F')
```

- Column 1: `[1, 2, 3]`
- Column 2: `[4, 5, 6]`

Matrix:

```
[[1, 4],
 [2, 5],
 [3, 6]]
```

---

## 📊 Controlling `imshow()`

### ✅ Recommended approach:

```python
extent = [0, n2, n1, 0]  # Make y-axis increase downwards
plt.imshow(data, extent=extent, cmap='viridis', aspect='auto')
```

- `n1`: vertical dimension (depth/time)
- `n2`: horizontal dimension (trace index)
- `extent=[x_min, x_max, y_max, y_min]` ensures correct geological orientation

### ⚠️ Not recommended: `.T`

Although `imshow(data.T)` may look right visually, it:

- **Changes the meaning of dimensions**
- **Breaks consistency in saving/comparison**
- **Easily causes coordinate confusion**

---

## ✅ Recommended Processing Steps

1. **Read data in Fortran order:**
   ```python
   data = np.fromfile("file.bin", dtype=np.float32).reshape((n1, n2), order='F')
   ```

2. **Ensure plotting consistency via reshape:**
   ```python
   plot_data = np.reshape(data.flatten(), (n1, n2), order='F')
   ```

3. **Control direction with `extent`:**
   ```python
   extent = [0, n2, n1, 0]
   plt.imshow(plot_data, extent=extent, cmap='viridis')
   ```

---

## 📌 Seismic Image Dimension Reference

| Name         | Dimension  | Meaning                             |
|--------------|------------|-------------------------------------|
| `n1`         | Vertical   | Depth or time samples               |
| `n2`         | Horizontal | Trace number (line number)          |
| `data[n1,n2]`| Array      | `n1` rows (depth), `n2` columns     |

---

## ✅ Summary

| Stage               | Recommended Practice                        |
|--------------------|---------------------------------------------|
| Reshaping           | Use `order='F'` to keep column-major layout |
| Display direction   | Use `extent=[0,n2,n1,0]` to show top-down   |
| No `.T`             | Avoid confusion and mismatches              |

---
