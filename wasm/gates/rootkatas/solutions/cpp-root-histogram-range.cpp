#include "TH1D.h"
#include <vector>

TH1D* build_calibration_histogram(const std::vector<double>& values) {
    // 11 bins of width 10 keep 100 inside the visible range instead of in overflow.
    auto* hist = new TH1D("h_calibration", "", 11, 0.0, 110.0);
    for (double value : values) hist->Fill(value);
    return hist;
}
