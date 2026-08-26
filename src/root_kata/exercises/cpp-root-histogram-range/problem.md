# Keep calibration values visible

A detector calibration scan contains measurements from `0` through `100`, inclusive. You want 10-unit-wide bins and every intended calibration value visible.

The starter histogram uses 10 bins from 0 to 100. It looks reasonable, but one measurement is not represented by a visible bin.

## Observe before coding

Run the starter once and inspect `underflow`, `overflow`, and the visible integral.

Predict: where does the value exactly equal to the upper edge (`100`) go?

## Your task

Repair `build_calibration_histogram` without changing the 10-unit bin width and without dropping measurements.

A correct solution should make the data representation, not just the drawing, match the intended calibration domain.
