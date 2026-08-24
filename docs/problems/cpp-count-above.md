# Count values above a cut

**Difficulty:** Easy  
**Track:** C++ selections  
**Estimated time:** 7 minutes  
**Topics:** `std::vector`, function arguments, strict comparison, selection

## Problem

Implement:

```cpp
int count_above(const std::vector<double>& values, double threshold);
```

Count how many values are **strictly greater than** `threshold`.

This is the smallest useful model of an analysis cut: each value is tested and either survives or is rejected.

### Example

```text
Input:  values = {20, 35, 50, 35}, threshold = 35
Output: 1
```

Only `50` survives. Values equal to `35` do not pass because the comparison is strict.

## Requirements

- Use the condition `value > threshold`.
- Return `0` for an empty vector.
- Do not hard-code the threshold.
- Do not modify the input vector.

## What this practices

Turning a written selection into an exact boolean condition — the mental step behind analysis cuts such as `pT > 35 GeV`.

## References

- [Range-based for loop — cppreference](https://en.cppreference.com/w/cpp/language/range-for)
- [std::vector — cppreference](https://en.cppreference.com/w/cpp/container/vector)

## Start in Jupyter

```python
import root_kata as rk
rk.start("cpp-count-above")
```
