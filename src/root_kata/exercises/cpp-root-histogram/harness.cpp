#include "rk.h"
#include "solution.cpp"
#include "TROOT.h"
#include "TCanvas.h"

int main() {
    gROOT->SetBatch(kTRUE);

    TH1D* h = build_histogram({});
    rk::emit("returned object", h != nullptr);
    if (h) { rk::emit("name", h->GetName()); rk::emit("nbins", h->GetNbinsX()); rk::emit("xmin", h->GetXaxis()->GetXmin()); rk::emit("xmax", h->GetXaxis()->GetXmax()); }
    TH1D* f = build_histogram({10.0, 20.0, 30.0});
    if (f) { rk::emit("entries", f->GetEntries()); rk::emit("integral", f->Integral()); rk::emit("mean", f->GetMean()); }
    TH1D* o = build_histogram({-5.0, 50.0, 150.0});
    if (o) { rk::emit("ovf entries", o->GetEntries()); rk::emit("ovf integral", o->Integral()); }

    // Deliberately spans underflow, several visible bins, and overflow so wrong binning is visible.
    TH1D* preview = build_histogram({-5, 5, 15, 35, 55, 75, 99, 150});
    if (preview) {
        TCanvas c("c", "", 640, 480);
        preview->Draw("HIST");
        c.SaveAs("preview.png");
    }
    return rk::done();
}
