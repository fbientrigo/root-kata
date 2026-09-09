// Gate G0 smoke test: a non-trivial, deterministic C++17 program used to validate
// that the pinned Emscripten toolchain compiles and runs identically under Node
// and headless Chromium. Deliberately has nothing to do with ROOT.
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

class Shape {
 public:
  virtual ~Shape() = default;
  virtual double area() const = 0;
  virtual std::string name() const = 0;
};

class Circle : public Shape {
 public:
  explicit Circle(double r) : radius_(r) {
    if (r < 0) throw std::invalid_argument("negative radius");
  }
  double area() const override { return M_PI * radius_ * radius_; }
  std::string name() const override { return "circle"; }

 private:
  double radius_;
};

class Square : public Shape {
 public:
  explicit Square(double s) : side_(s) {}
  double area() const override { return side_ * side_; }
  std::string name() const override { return "square"; }

 private:
  double side_;
};

int main() {
  std::vector<std::unique_ptr<Shape>> shapes;
  shapes.push_back(std::make_unique<Circle>(2.0));
  shapes.push_back(std::make_unique<Square>(3.0));

  double total = 0.0;
  for (const auto& s : shapes) {
    total += s->area();
    std::cout << s->name() << " area = " << std::fixed << std::setprecision(6)
              << s->area() << "\n";
  }
  std::cout << "total area = " << std::fixed << std::setprecision(6) << total
             << "\n";

  try {
    Circle bad(-1.0);
    (void)bad;
    std::cout << "unreachable\n";
  } catch (const std::invalid_argument& e) {
    std::cout << "caught: " << e.what() << "\n";
  }

  std::cout << "sqrt(2) = " << std::fixed << std::setprecision(6)
             << std::sqrt(2.0) << "\n";
  std::cout << "G0 SMOKE OK\n";
  return 0;
}
