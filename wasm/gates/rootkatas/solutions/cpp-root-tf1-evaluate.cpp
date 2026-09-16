#include "TF1.h"

TF1* build_linear_model(double intercept, double slope) {
    auto* model = new TF1("calibration_model", "[0]+[1]*x", 0.0, 10.0);
    model->SetParameters(intercept, slope);
    return model;
}
