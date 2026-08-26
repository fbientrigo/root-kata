#include "rk.h"
#include "solution.cpp"

#include "TH1D.h"

int main() {
    TH1D hist("h_inspect", "", 5, 0.0, 5.0);
    for (double value : {0.2, 1.2, 1.7, 3.3, 3.8}) {
        hist.Fill(value);
    }

    const auto bin2 = inspect_histogram(hist, 2);
    rk::emit("entries", bin2.entries);
    rk::emit("bin2 content", bin2.bin_content);
    rk::emit("mean", bin2.mean);
    rk::emit("stddev", bin2.stddev);

    const auto bin3 = inspect_histogram(hist, 3);
    rk::emit("bin3 content", bin3.bin_content);

    return rk::done();
}
