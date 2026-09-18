# Recover a peak with a Gaussian fit

A histogram contains a deterministic peak. Your task is not to draw a curve that looks convincing; it is to extract and inspect a numerical fit result.

Implement `fit_peak(TH1D& hist)` using a Gaussian `TF1` on `[2,8]`.

Return three pieces of evidence:

- the fit status;
- the fitted mean;
- the fitted sigma as a positive width.

## Predict before coding

The supplied sample was constructed with a peak near `5` and a width near `0.8`. What values should a successful fit recover?

The visible tests allow small numerical tolerances but require the fit itself to converge.
