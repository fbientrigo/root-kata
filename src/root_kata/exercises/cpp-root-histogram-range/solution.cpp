#include "TH1D.h"
#include <vector>

TH1D* build_calibration_histogram(const std::vector<double>& values) {
    // This range looks plausible, but run the kata and inspect the boundary.
    auto* hist = new TH1D("h_calibration", "", 10, 0.0, 100.0);
    for (double value : values) hist->Fill(value);
    return hist;
}
