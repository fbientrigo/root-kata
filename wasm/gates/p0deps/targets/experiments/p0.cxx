#include "TH1D.h"
#include <cstdio>
int main(int argc, char**) {
  if (argc > 1) TH1::AddDirectory(false);
  fprintf(stderr, "MARK before-ctor\n");
  TH1D h("h", "h", 10, 0., 10.);
  fprintf(stderr, "MARK after-ctor\n");
  for (int i = 0; i < 10; ++i) h.Fill(i + 0.5, i);
  printf("entries=%g bin3=%g mean=%.6f std=%.6f integral=%g nbins=%d\n",
         h.GetEntries(), h.GetBinContent(3), h.GetMean(), h.GetStdDev(), h.Integral(), h.GetNbinsX());
}
