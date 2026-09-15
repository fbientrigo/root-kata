// Positive control: operations that genuinely need the interpreter / reflection.
#include "TInterpreter.h"
#include "TClass.h"
#include "TList.h"
#include "TF1.h"
#include <cstdio>

int main() {
  printf("control.start = 1\n"); fflush(stdout);
  long r = gInterpreter->ProcessLine("1+1;");
  printf("ProcessLine(1+1) = %ld\n", r); fflush(stdout);
  TClass *c = TClass::GetClass("TH1D");
  printf("TClass(TH1D).datamembers = %d\n", c && c->GetListOfDataMembers() ? c->GetListOfDataMembers()->GetSize() : -1); fflush(stdout);
  TF1 f("f", "gaus", -1, 1);
  f.SetParameters(1, 0, 1);
  printf("TF1(gaus).Eval(0.5) = %.17g\n", f.Eval(0.5));
  return 0;
}
