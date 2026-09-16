#include <cstdio>
#include <dlfcn.h>
#include "TNamed.h"
#include "TString.h"
#include "TClassTable.h"
#include "TH1D.h"
#include "TMath.h"
int main() {
  printf("smoke.start\n");
  TString s("root"); s += "-wasm"; printf("tstring=%s len=%d\n", s.Data(), s.Length());
  TNamed n("n", "title"); printf("tnamed=%s/%s\n", n.GetName(), n.GetTitle());
  printf("tmath.gaus=%.17g\n", TMath::Gaus(0.5, 0, 1, true));
  printf("classtable.TH1D=%d\n", TClassTable::GetDict("TH1D") != nullptr);
  printf("staticroot=%d\n", dlsym(RTLD_DEFAULT, "usedToIdentifyStaticRoot") != nullptr);
  fflush(stdout);
  TH1D h("h", "h", 10, 0, 10);
  h.Fill(3.3); h.Fill(-1); h.Fill(11);
  printf("th1d.entries=%.17g integral=%.17g mean=%.17g\n", h.GetEntries(), h.Integral(), h.GetMean());
  return 0;
}
