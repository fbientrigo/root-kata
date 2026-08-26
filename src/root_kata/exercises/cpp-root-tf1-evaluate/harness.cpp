#include "rk.h"
#include "solution.cpp"
#include "TF1.h"

int main() {
    TF1* model = build_linear_model(2.0, 3.0);
    rk::emit("returned object", model != nullptr);
    if (model) {
        double xmin = 0.0, xmax = 0.0;
        model->GetRange(xmin, xmax);
        rk::emit("name", model->GetName());
        rk::emit("npar", model->GetNpar());
        rk::emit("xmin", xmin);
        rk::emit("xmax", xmax);
        rk::emit("p0", model->GetParameter(0));
        rk::emit("p1", model->GetParameter(1));
        rk::emit("eval0", model->Eval(0.0));
        rk::emit("eval2", model->Eval(2.0));
        model->SetParameter(1, -1.0);
        rk::emit("eval2 changed", model->Eval(2.0));
        delete model;
    }
    return rk::done();
}
