# Sum positive values

**Difficulty:** Easy  
**Track:** C++ warm-up  
**Estimated time:** 5 minutes  
**Topics:** `std::vector`, range-for, `if`, accumulator

## Problem

Implement:

```cpp
double sum_positive(const std::vector<double>& values);
```

Return the sum of every value that is **strictly greater than zero**. Zero and negative values do not contribute.

### Example

```text
Input:  {-2, 3, 0, 5}
Output: 8
```

Only `3` and `5` are positive, so the result is `3 + 5 = 8`.

## Requirements

- Return `0` for an empty vector.
- Ignore zero and negative values.
- Do not modify the input vector.

## What this practices

The loop → condition → accumulator pattern. The same shape appears later when selecting events and accumulating physics quantities.

## References

- [std::vector — cppreference](https://en.cppreference.com/w/cpp/container/vector)
- [Range-based for loop — cppreference](https://en.cppreference.com/w/cpp/language/range-for)

## Start in Jupyter

```python
import root_kata as rk
rk.start("cpp-sum-positive")
```
