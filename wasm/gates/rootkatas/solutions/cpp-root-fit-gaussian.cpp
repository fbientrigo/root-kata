#include "TH1D.h"
#include "TF1.h"

struct PeakFit {
    int status;
    double mean;
    double sigma;
};

PeakFit fit_peak(TH1D& hist) {
    TF1 model("peak_model", "gaus", 2.0, 8.0);
    model.SetParameters(hist.GetMaximum(), hist.GetMean(), hist.GetStdDev());
    const int status = hist.Fit(&model, "QNR");
    return {status, model.GetParameter(1), model.GetParameter(2)};
}
