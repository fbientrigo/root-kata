#include "TH1D.h"
#include <vector>

TH1D* build_selected_histogram(const std::vector<double>& values, double threshold) {
    auto* hist = new TH1D("h_selected", "", 5, 0.0, 150.0);
    for (double value : values) {
        // TODO: fill only values that satisfy the requested strict selection.
    }
    return hist;
}
