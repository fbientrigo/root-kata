#include "TGraph.h"
#include <vector>

TGraph* build_graph(const std::vector<double>& x, const std::vector<double>& y) {
    return new TGraph(static_cast<int>(x.size()), x.data(), y.data());
}
