#include <vector>

int count_above(const std::vector<double>& values, double threshold) {
    int count = 0;
    for (double value : values)
        if (value > threshold) ++count;
    return count;
}
