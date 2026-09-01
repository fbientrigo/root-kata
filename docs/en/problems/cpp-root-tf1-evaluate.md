# Turn a formula into a ROOT model

A calibration model is more useful when its parameters can change without rewriting the formula.

Build the linear model `f(x) = intercept + slope*x` as a `TF1` on `[0,10]`.

## Observe before coding

For `intercept = 2` and `slope = 3`, predict `f(0)` and `f(2)`.

Then ask what should happen to `f(2)` if only the slope changes to `-1`.

The kata checks both the initial prediction and that changing the parameter actually changes the same model.
