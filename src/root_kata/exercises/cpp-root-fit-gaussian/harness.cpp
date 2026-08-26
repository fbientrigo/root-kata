#include "rk.h"
#include "solution.cpp"
#include "TH1D.h"
#include <algorithm>
#include <cmath>

int main() {
    TH1D hist("h_peak", "", 80, 0.0, 10.0);
    for (int bin = 1; bin <= hist.GetNbinsX(); ++bin) {
        const double x = hist.GetXaxis()->GetBinCenter(bin);
        const double z = (x - 5.0) / 0.8;
        const double y = 120.0 * std::exp(-0.5 * z * z);
        hist.SetBinContent(bin, y);
        hist.SetBinError(bin, std::sqrt(std::max(y, 1.0)));
    }
    const PeakFit fit = fit_peak(hist);
    rk::emit("status", fit.status);
    rk::emit("mean", fit.mean);
    rk::emit("sigma", fit.sigma);
    return rk::done();
}
