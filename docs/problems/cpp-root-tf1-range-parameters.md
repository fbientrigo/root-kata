# Diagnose a plausible but wrong TF1

The starter code contains a mathematically valid exponential formula. It still represents the requested model incorrectly.

The intended model is `A*exp(-x/tau)` for an analysis domain from 0 to 10.

## Observe before coding

Run the starter and inspect parameter 0, parameter 1, the configured range, and `f(0)`.

Which failures come from the formula, and which come from configuration?

Repair the smallest causes. A correct formula is not enough if its parameters carry the wrong physical meaning.
