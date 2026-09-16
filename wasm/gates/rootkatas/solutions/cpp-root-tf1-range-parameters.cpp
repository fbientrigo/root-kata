#include "TF1.h"

TF1* build_decay_model(double amplitude, double tau) {
    // The seeded bugs were the upper range and the argument order.
    auto* model = new TF1("decay_model", "[0]*exp(-x/[1])", 0.0, 10.0);
    model->SetParameters(amplitude, tau);
    return model;
}
