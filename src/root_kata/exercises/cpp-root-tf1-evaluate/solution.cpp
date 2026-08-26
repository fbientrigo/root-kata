#include "TF1.h"

TF1* build_linear_model(double intercept, double slope) {
    // TODO: encode f(x) = intercept + slope*x as a parameterized TF1.
    return new TF1("calibration_model", "0", 0.0, 10.0);
}
