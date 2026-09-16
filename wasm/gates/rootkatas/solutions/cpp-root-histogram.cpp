#include <vector>
#include "TH1D.h"

TH1D* build_histogram(const std::vector<double>& values) {
    TH1D* hist = new TH1D("h_pt", "h_pt", 10, 0, 100);
    for (double value : values) hist->Fill(value);
    return hist;
}
