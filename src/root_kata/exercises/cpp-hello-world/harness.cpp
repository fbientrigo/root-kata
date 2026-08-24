#include "rk.h"
#include <iostream>
#include <sstream>
#include "solution.cpp"

int main() {
    std::ostringstream captured;
    auto* previous = std::cout.rdbuf(captured.rdbuf());
    say_hello();
    std::cout.rdbuf(previous);

    const std::string output = captured.str();
    rk::emit("prints something", !output.empty());
    rk::emit("exact output", output == "Hello, world!\n");
    return rk::done();
}
