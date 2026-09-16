// Genuine CERN ROOT 6.40.04, compiled and run in your browser.
// Edit anything here and press Run.
#include "TH1D.h"
#include "TF1.h"
#include <cstdio>

int main() {
   TH1D h("h", "a histogram", 20, -5, 5);
   TF1 gaus("gaus", "gaus", -5, 5);
   gaus.SetParameters(1.0, 0.0, 1.0);
   for (int i = 1; i <= h.GetNbinsX(); ++i)
      h.SetBinContent(i, 100.0 * gaus.Eval(h.GetBinCenter(i)));

   printf("entries  = %g\n", h.GetEntries());
   printf("integral = %.6f\n", h.Integral());
   printf("mean     = %.6f\n", h.GetMean());
   printf("std dev  = %.6f\n", h.GetStdDev());
   printf("max bin  = %d at x = %.3f\n", h.GetMaximumBin(),
          h.GetXaxis()->GetBinCenter(h.GetMaximumBin()));

   for (int i = 1; i <= h.GetNbinsX(); ++i) {
      printf("%6.2f | ", h.GetXaxis()->GetBinCenter(i));
      for (int n = 0; n < (int)(h.GetBinContent(i) / 2.0); ++n) putchar('#');
      putchar('\n');
   }
   return 0;
}
