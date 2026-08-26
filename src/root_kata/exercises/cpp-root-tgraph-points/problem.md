# Preserve paired measurements with TGraph

A calibration scan gives you measured `(x, y)` pairs. The x positions are real measurements, not implicit point numbers.

Implement:

```cpp
TGraph* build_graph(const std::vector<double>& x,
                    const std::vector<double>& y)
```

## Observe before coding

Compare the x values `0`, `1.5`, and `4`. They are not equally spaced.

Predict what information would be lost if you used point indices `0, 1, 2` as the x coordinates.

Return a graph that preserves every supplied pair and its order. The tests inspect coordinates, not drawing style.
