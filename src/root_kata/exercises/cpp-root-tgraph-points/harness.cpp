#include "rk.h"
#include "solution.cpp"
#include "TGraph.h"
#include <string>

int main() {
    TGraph* graph = build_graph({0.0, 1.5, 4.0}, {2.0, 3.5, 3.0});
    rk::emit("returned object", graph != nullptr);
    if (graph) {
        rk::emit("n", graph->GetN());
        for (int i = 0; i < graph->GetN(); ++i) {
            double x = 0.0, y = 0.0;
            graph->GetPoint(i, x, y);
            rk::emit("x" + std::to_string(i), x);
            rk::emit("y" + std::to_string(i), y);
        }
        delete graph;
    }
    return rk::done();
}
