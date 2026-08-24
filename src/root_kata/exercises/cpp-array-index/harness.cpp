#include "rk.h"
#include "solution.cpp"

int main() {
    rk::emit("second value", second_value());
    return rk::done();
}
