// P0 TH1D/TAxis probe. Link: -lHist (+ whatever ld demands). No interpreter calls.
#include "TH1.h"
#include "TH1D.h"
#include "TAxis.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <set>
#include <string>

static void dump_maps() {
  const char *out = getenv("P0_MAPS");
  if (!out) return;
  std::ifstream in("/proc/self/maps");
  std::set<std::string> libs;
  for (std::string l; std::getline(in, l);) {
    auto p = l.find('/');
    if (p != std::string::npos && l.find(".so", p) != std::string::npos) libs.insert(l.substr(p));
  }
  FILE *f = fopen(out, "w");
  for (auto &s : libs) fprintf(f, "%s\n", s.c_str());
  fclose(f);
}

#define P(label, v) printf("%s = %.17g\n", label, (double)(v))

int main() {
#ifdef P0_NO_ADD_DIRECTORY
  TH1::AddDirectory(false);
  printf("variant = AddDirectory(false)\n");
#endif
  {
    TH1D h("h", "h", 10, 0, 10);
    printf("name = %s\n", h.GetName());
    printf("directory_is_null = %d\n", h.GetDirectory() == nullptr);
    for (double x : {0.5, 1.5, 1.5, 2.25, 3.75, 4.0, 5.5, 9.99}) h.Fill(x);
    h.Fill(-1.0);          // underflow
    h.Fill(11.0);          // overflow
    h.Fill(6.5, 2.5);      // weighted
    P("entries", h.GetEntries());
    for (int b = 0; b <= 11; ++b) { char k[32]; snprintf(k, sizeof k, "bin[%d]", b); P(k, h.GetBinContent(b)); }
    P("integral", h.Integral());
    P("mean", h.GetMean());
    P("stddev", h.GetStdDev());
    TAxis *ax = h.GetXaxis();
    P("axis.nbins", ax->GetNbins());
    P("axis.xmin", ax->GetXmin());
    P("axis.xmax", ax->GetXmax());
    P("axis.FindBin(3.3)", ax->FindBin(3.3));
    P("axis.FindBin(-1)", ax->FindBin(-1.0));
    P("axis.FindBin(11)", ax->FindBin(11.0));
    P("axis.GetBinCenter(3)", ax->GetBinCenter(3));
    P("axis.GetBinLowEdge(3)", ax->GetBinLowEdge(3));
    P("axis.GetBinWidth(3)", ax->GetBinWidth(3));
    P("nbinsx", h.GetNbinsX());
    h.SetBinContent(4, 7.25);
    h.SetBinError(4, 1.5);
    P("after_set.bin[4]", h.GetBinContent(4));
    P("after_set.err[4]", h.GetBinError(4));
    P("after_set.integral", h.Integral());
    P("after_set.entries", h.GetEntries());
    P("after_set.mean", h.GetMean());
    P("after_set.stddev", h.GetStdDev());
  }
  // harness pattern: heap-allocated TH1D returned by pointer
  TH1D *hp = new TH1D("h_heap", "", 5, 0.0, 5.0);
  for (double v : {0.2, 1.2, 1.7, 3.3, 3.8}) hp->Fill(v);
  printf("heap.name = %s\n", hp->GetName());
  P("heap.bin[2]", hp->GetBinContent(2));
  P("heap.mean", hp->GetMean());
  P("heap.stddev", hp->GetStdDev());
  delete hp;
  printf("destroyed = 1\n");
  dump_maps();
  return 0;
}
