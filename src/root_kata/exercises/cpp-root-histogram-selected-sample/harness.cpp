#include "rk.h"
#include "solution.cpp"
#include "TH1D.h"

int main() {
    TH1D* a = build_selected_histogram({20.0, 50.0, 50.1, 80.0, 120.0}, 50.0);
    rk::emit("a returned", a != nullptr);
    if (a) {
        rk::emit("name", a->GetName());
        rk::emit("nbins", a->GetNbinsX());
        rk::emit("xmin", a->GetXaxis()->GetXmin());
        rk::emit("xmax", a->GetXaxis()->GetXmax());
        rk::emit("a entries", a->GetEntries());
        rk::emit("a integral", a->Integral());
        rk::emit("a first bin", a->GetBinContent(1));
        delete a;
    }
    TH1D* b = build_selected_histogram({-10.0, 10.0, 151.0}, 0.0);
    rk::emit("b returned", b != nullptr);
    if (b) {
        rk::emit("b entries", b->GetEntries());
        rk::emit("b integral", b->Integral());
        rk::emit("b overflow", b->GetBinContent(b->GetNbinsX() + 1));
        delete b;
    }
    return rk::done();
}
