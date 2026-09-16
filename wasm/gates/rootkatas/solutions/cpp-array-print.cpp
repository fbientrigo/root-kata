#include <iostream>

void print_values() {
    int values[3] = {4, 8, 15};
    for (int value : values) std::cout << value << "\n";
}
