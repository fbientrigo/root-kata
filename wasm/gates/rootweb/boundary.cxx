// M2b browser boundary probe.
//
// The same genuine ROOT calls the Node M2 gate makes
// (wasm/gates/rootlight/smoke.cxx -- its first five lines are asserted against
// the very same expected.txt), plus direct evidence of exactly which symbol
// TROOT::InitInterpreter is still missing.
//
// Why the interpreter check is a dlsym and not a TH1D construction: with ROOT's
// own static-ROOT marker present, TROOT::InitInterpreter
// (core/base/src/TROOT.cxx:2227-2251) resolves CreateInterpreter through
// RTLD_DEFAULT instead of dlopen'ing libCling, so these two lookups are
// literally the decision it makes. Constructing a TH1D today reaches that code
// and calls exit(1), which traps inside Emscripten's atexit dispatch and
// discards the captured output -- see FINDINGS.md.
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
  printf("createinterpreter=%d\n", dlsym(RTLD_DEFAULT, "CreateInterpreter") != nullptr);
  fflush(stdout);
  return 0;
}
