#include "TH1D.h"

struct HistogramInspection {
    double entries;
    double bin_content;
    double mean;
    double stddev;
};

HistogramInspection inspect_histogram(const TH1D& hist, int bin) {
    // TODO: inspect hist without modifying it.
    return {0.0, 0.0, 0.0, 0.0};
}
