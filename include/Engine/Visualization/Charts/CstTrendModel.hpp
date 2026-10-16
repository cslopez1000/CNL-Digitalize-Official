#pragma once
#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace combination {
struct Axis {
    double minimum, maximum, step;
};
// CST pid_ga_control_tab.TrendPlot is the active behavioral reference. Numeric processing
// stays in C++; Python supplies data and owns Qt widget/context lifetime only.
class CstTrendModel {
  public:
    std::string xLabel = "TIME (s)", yLabel = "CURRENT (A)";
    bool relativeTime = true;
    bool allowMissingTarget = false;
    double rollingWindow = 120;
    std::size_t maxPoints = 600;
    int xTicks = 6, yTicks = 5;
    std::vector<std::vector<double>> rows;
    bool hasThird = false;
    void SetData(const std::vector<double> &x, const std::vector<double> &target,
                 const std::vector<double> &actual, const std::vector<double> *third = nullptr);
    std::array<double, 4> RawBounds() const;
    Axis XAxis() const;
    Axis YAxis() const;
    static double NiceNumber(double value, bool roundValue);
    static Axis NiceAxis(double lower, double upper, int requestedTicks);
    static std::vector<double> Ticks(Axis axis);
    static std::string FormatTick(double value, double step);
    bool IsTimeAxis() const;
};
} // namespace combination
