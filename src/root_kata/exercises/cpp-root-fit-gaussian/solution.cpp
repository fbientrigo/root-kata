#include "TH1D.h"

struct PeakFit {
    int status;
    double mean;
    double sigma;
};

PeakFit fit_peak(TH1D& hist) {
    // TODO: fit the supplied peak with a Gaussian model on [2, 8].
    return {-1, 0.0, 0.0};
}
