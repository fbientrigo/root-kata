#include "rk.h"
#include <iostream>
#include <sstream>
#include "solution.cpp"

int main() {
    std::ostringstream captured;
    auto* previous = std::cout.rdbuf(captured.rdbuf());
    print_values();
    std::cout.rdbuf(previous);

    std::istringstream input(captured.str());
    int value = 0;
    int count = 0;
    int first = 0, second = 0, third = 0;
    while (input >> value) {
        if (count == 0) first = value;
        if (count == 1) second = value;
        if (count == 2) third = value;
        ++count;
    }

    rk::emit("value count", count);
    rk::emit("first value", first);
    rk::emit("second value", second);
    rk::emit("third value", third);
    return rk::done();
}
