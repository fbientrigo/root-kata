#include "TF1.h"

TF1* build_decay_model(double amplitude, double tau) {
    // The formula is fine. Two configuration choices below are not.
    auto* model = new TF1("decay_model", "[0]*exp(-x/[1])", 0.0, 1.0);
    model->SetParameters(tau, amplitude);
    return model;
}
