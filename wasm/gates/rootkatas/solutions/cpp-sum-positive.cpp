#include <vector>

double sum_positive(const std::vector<double>& values) {
    double sum = 0;
    for (double value : values)
        if (value > 0) sum += value;
    return sum;
}
