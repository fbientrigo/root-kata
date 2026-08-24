#include "rk.h"
#include "solution.cpp"

int main() {
    rk::emit("mixed values", count_above({20.0, 35.0, 50.0, 35.0}, 35.0));
    rk::emit("strict boundary", count_above({5.0, 5.0, 5.1}, 5.0));
    rk::emit("empty input", count_above({}, 10.0));
    rk::emit("negative threshold", count_above({-3.0, -1.0, 0.0, 2.0}, -1.0));
    return rk::done();
}
