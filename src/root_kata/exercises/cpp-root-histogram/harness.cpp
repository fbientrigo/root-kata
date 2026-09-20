#include "rk.h"
#include "solution.cpp"
#include "TROOT.h"
#if !defined(__EMSCRIPTEN__) && !defined(ROOT_KATA_HEADLESS_WASM)
#include "TCanvas.h"
#endif

int main() {
    gROOT->SetBatch(kTRUE);
    TH1::AddDirectory(kFALSE);

    TH1D* h = build_histogram({});
    rk::emit("returned object", h != nullptr);
    if (h) {
        rk::emit("name", h->GetName());
        rk::emit("nbins", h->GetNbinsX());
        rk::emit("xmin", h->GetXaxis()->GetXmin());
        rk::emit("xmax", h->GetXaxis()->GetXmax());
        delete h;
    }
    TH1D* f = build_histogram({10.0, 20.0, 30.0});
    if (f) {
        rk::emit("entries", f->GetEntries());
        rk::emit("integral", f->Integral());
        rk::emit("mean", f->GetMean());
        delete f;
    }
    TH1D* o = build_histogram({-5.0, 50.0, 150.0});
    if (o) {
        rk::emit("ovf entries", o->GetEntries());
        rk::emit("ovf integral", o->Integral());
        delete o;
    }

    // Deliberately spans underflow, several visible bins, and overflow so wrong binning is visible.
#if !defined(__EMSCRIPTEN__) && !defined(ROOT_KATA_HEADLESS_WASM)
    TH1D* preview = build_histogram({-5, 5, 15, 35, 55, 75, 99, 150});
    if (preview) {
        TCanvas c("c", "", 640, 480);
        preview->Draw("HIST");
        c.SaveAs("preview.png");
        delete preview;
    }
#endif
    return rk::done();
}
