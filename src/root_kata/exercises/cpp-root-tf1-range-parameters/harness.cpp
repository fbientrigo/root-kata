#include "rk.h"
#include "solution.cpp"
#include "TF1.h"

int main() {
    TF1* model = build_decay_model(12.0, 2.0);
    rk::emit("returned object", model != nullptr);
    if (model) {
        double xmin = 0.0, xmax = 0.0;
        model->GetRange(xmin, xmax);
        rk::emit("name", model->GetName());
        rk::emit("p0", model->GetParameter(0));
        rk::emit("p1", model->GetParameter(1));
        rk::emit("xmin", xmin);
        rk::emit("xmax", xmax);
        rk::emit("eval0", model->Eval(0.0));
        rk::emit("eval4", model->Eval(4.0));
        delete model;
    }
    return rk::done();
}
