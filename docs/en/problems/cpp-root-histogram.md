# Fill a ROOT histogram

**Difficulty:** Easy  
**Track:** ROOT basics  
**Estimated time:** 10 minutes  
**Topics:** `TH1D`, `Fill`, binning, underflow/overflow

## Problem

Implement:

```cpp
TH1D* build_histogram(const std::vector<double>& values);
```

Create a one-dimensional ROOT histogram named `h_pt` with **10 bins from 0 to 100**, fill every input value exactly once, and return the histogram pointer.

### Example

```text
Input:  {10, 20, 30}
Output: TH1D with 3 entries and mean 20
```

## Requirements

- Use exactly 10 bins covering `[0, 100]`.
- Name the histogram `h_pt`.
- Call `Fill` once per input value.
- Return a pointer created with `new TH1D(...)`.

## What this practices

The first ROOT object used constantly in analysis: explicit binning, filling measurements, and recognizing that underflow/overflow still contribute to the entry count.

## References

- [TH1 — ROOT reference](https://root.cern.ch/doc/master/classTH1.html)
- [std::vector — cppreference](https://en.cppreference.com/w/cpp/container/vector)

## Start in Jupyter

```python
import root_kata as rk
rk.start("cpp-root-histogram")
```
