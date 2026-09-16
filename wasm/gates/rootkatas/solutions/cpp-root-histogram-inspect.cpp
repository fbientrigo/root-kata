#include "TH1D.h"

struct HistogramInspection {
    double entries;
    double bin_content;
    double mean;
    double stddev;
};

HistogramInspection inspect_histogram(const TH1D& hist, int bin) {
    return {hist.GetEntries(), hist.GetBinContent(bin), hist.GetMean(), hist.GetStdDev()};
}
