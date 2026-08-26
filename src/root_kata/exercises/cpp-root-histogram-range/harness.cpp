#include "rk.h"
#include "solution.cpp"
#include "TH1D.h"

int main() {
    const std::vector<double> values{0,10,20,30,40,50,60,70,80,90,100};
    TH1D* h = build_calibration_histogram(values);
    rk::emit("returned object", h != nullptr);
    if (h) {
        rk::emit("name", h->GetName());
        rk::emit("nbins", h->GetNbinsX());
        rk::emit("xmin", h->GetXaxis()->GetXmin());
        rk::emit("xmax", h->GetXaxis()->GetXmax());
        rk::emit("bin width", h->GetXaxis()->GetBinWidth(1));
        rk::emit("entries", h->GetEntries());
        rk::emit("visible integral", h->Integral());
        rk::emit("underflow", h->GetBinContent(0));
        rk::emit("overflow", h->GetBinContent(h->GetNbinsX() + 1));
        delete h;
    }
    return rk::done();
}
