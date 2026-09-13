#include <cstdio>

#include <TH1D.h>

int main() {
  TH1D histogram("sample", "", 3, 0.0, 3.0);
  for (double value : {0.5, 1.5, 1.5, 2.5}) {
    histogram.Fill(value);
  }

  std::printf("entries=%.0f bin2=%.0f integral=%.0f mean=%.6f\n",
              histogram.GetEntries(), histogram.GetBinContent(2),
              histogram.Integral(), histogram.GetMean());
}
