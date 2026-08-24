#include "rk.h"
#include "solution.cpp"

int main() {
    rk::emit("mixed signs", sum_positive({-2, 3, 0, 5}));
    rk::emit("all non-positive", sum_positive({-5, -1, 0}));
    rk::emit("empty input", sum_positive({}));
    rk::emit("floats", sum_positive({1.5, -8.0, 2.25}));
    return rk::done();
}
