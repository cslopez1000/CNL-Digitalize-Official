#include "Engine/Visualization/Charts/CstTrendModel.hpp"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>

namespace combination {
namespace {
std::string Upper(std::string text) {
    for (auto &c : text)
        c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    return text;
}
// Python round() uses ties-to-even, unlike std::round(). Inputs here are
// nonnegative indices; preserve CST's choice at exact half-way points.
std::size_t RoundIndex(double value) {
    const auto lower = static_cast<std::size_t>(std::floor(value));
    const auto fraction = value - static_cast<double>(lower);
    return lower + (fraction > 0.5 || (fraction == 0.5 && lower % 2));
}
} // namespace
bool CstTrendModel::IsTimeAxis() const {
    return Upper(xLabel).find("TIME") != std::string::npos;
}
void CstTrendModel::SetData(const std::vector<double> &x, const std::vector<double> &target,
                            const std::vector<double> &actual, const std::vector<double> *third) {
    rows.clear();
    hasThird = third != nullptr;
    auto n = std::min({x.size(), target.size(), actual.size()});
    if (third)
        n = std::min(n, third->size());
    rows.reserve(std::min(n, std::max(std::size_t{50}, maxPoints)));
    for (std::size_t i = 0; i < n; ++i) {
        if (!std::isfinite(x[i]) || (!allowMissingTarget && !std::isfinite(target[i])) ||
            !std::isfinite(actual[i]) || (third && !std::isfinite((*third)[i])))
            continue;
        rows.push_back({x[i], target[i], actual[i]});
        if (third)
            rows.back().push_back((*third)[i]);
    }
    if (!rows.empty() && IsTimeAxis() && rollingWindow > 0) {
        const auto newest = rows.back()[0];
        std::erase_if(rows, [&](const auto &row) { return row[0] < newest - rollingWindow; });
        if (relativeTime)
            for (auto &row : rows)
                row[0] -= newest;
    }
    const auto limit = std::max(std::size_t{50}, maxPoints);
    if (rows.size() > limit) {
        std::vector<std::vector<double>> selected;
        selected.reserve(limit);
        for (std::size_t i = 0; i < limit; ++i)
            selected.push_back(
                rows[RoundIndex(static_cast<double>(i) * (rows.size() - 1) / (limit - 1))]);
        rows.swap(selected);
    }
}
double CstTrendModel::NiceNumber(double value, bool roundValue) {
    value = std::abs(value);
    if (!std::isfinite(value) || value <= 0)
        return 1;
    const auto power = std::pow(10.0, std::floor(std::log10(value)));
    const auto f = value / power;
    const auto nice = roundValue ? (f < 1.5 ? 1
                                    : f < 3 ? 2
                                    : f < 7 ? 5
                                            : 10)
                                 : (f <= 1   ? 1
                                    : f <= 2 ? 2
                                    : f <= 5 ? 5
                                             : 10);
    return nice * power;
}
Axis CstTrendModel::NiceAxis(double lower, double upper, int requestedTicks) {
    if (!std::isfinite(lower) || !std::isfinite(upper))
        return {0, 1, 0.2};
    if (upper < lower)
        std::swap(lower, upper);
    if (std::abs(lower - upper) <= 1e-15) {
        const auto pad = std::max(1.0, std::abs(lower) * 0.1);
        lower -= pad;
        upper += pad;
    }
    const auto step =
        NiceNumber(NiceNumber(upper - lower, false) / std::max(2, requestedTicks - 1), true);
    Axis axis{std::floor(lower / step) * step, std::ceil(upper / step) * step, step};
    if (std::abs(axis.minimum - axis.maximum) <= 1e-15)
        axis.maximum = axis.minimum + step;
    return axis;
}
std::array<double, 4> CstTrendModel::RawBounds() const {
    if (rows.size() < 2)
        return {relativeTime && IsTimeAxis() ? -1.0 : 0.0, relativeTime && IsTimeAxis() ? 0.0 : 1.0,
                0, 1};
    double xMin = rows[0][0], xMax = xMin, yMin = std::numeric_limits<double>::infinity(),
           yMax = -yMin;
    for (const auto &row : rows) {
        xMin = std::min(xMin, row[0]);
        xMax = std::max(xMax, row[0]);
        for (std::size_t i = 1; i < row.size(); ++i)
            if (std::isfinite(row[i])) {
                yMin = std::min(yMin, row[i]);
                yMax = std::max(yMax, row[i]);
            }
    }
    if (!(relativeTime && IsTimeAxis()) && Upper(xLabel).find("EVALUATION") != std::string::npos)
        xMin = std::min(0.0, xMin);
    const auto pad = std::abs(yMax - yMin) <= 1e-15
                         ? std::max({0.01, std::abs(yMax) * 0.08, yMax == 0 ? 1.0 : 0.0})
                         : 0.08 * (yMax - yMin);
    yMin -= pad;
    yMax += pad;
    const auto label = Upper(yLabel);
    if (yMin >= 0 &&
        (label.find("ERROR") != std::string::npos || label.find("FITNESS") != std::string::npos ||
         yMin <= 0.2 * std::max(yMax, 1e-12)))
        yMin = 0;
    return {xMin, xMax, yMin, yMax};
}
Axis CstTrendModel::XAxis() const {
    const auto bounds = RawBounds();
    if (!(relativeTime && IsTimeAxis()))
        return NiceAxis(bounds[0], bounds[1], std::max(3, xTicks));
    const auto span = std::max(1.0, std::abs(bounds[0]));
    const auto step = NiceNumber(span / std::max(2, std::max(3, xTicks) - 1), true);
    return {-std::max(1.0, std::ceil(span / step)) * step, 0, step};
}
Axis CstTrendModel::YAxis() const {
    const auto b = RawBounds();
    return NiceAxis(b[2], b[3], std::max(3, yTicks));
}
std::vector<double> CstTrendModel::Ticks(Axis axis) {
    if (axis.step <= 0 || !std::isfinite(axis.minimum) || !std::isfinite(axis.maximum) ||
        !std::isfinite(axis.step))
        return {axis.minimum, axis.maximum};
    std::vector<double> values;
    auto value = axis.minimum;
    for (int i = 0; i < 30 && value <= axis.maximum + axis.step * 0.25; ++i, value += axis.step)
        values.push_back(std::abs(value) < axis.step * 1e-10 ? 0 : value);
    if (values.empty())
        return {axis.minimum, axis.maximum};
    return values;
}
std::string CstTrendModel::FormatTick(double value, double step) {
    if (std::abs(value) < std::max(1e-15, std::abs(step) * 1e-10))
        value = 0;
    const auto magnitude = std::abs(value);
    std::ostringstream out;
    if (magnitude >= 10000 || (magnitude > 0 && magnitude < .001))
        out << std::scientific << std::setprecision(2) << value;
    else {
        const int decimals = step >= 10     ? 0
                             : step >= 1    ? 1
                             : step >= .1   ? 2
                             : step >= .01  ? 3
                             : step >= .001 ? 4
                                            : 5;
        out << std::fixed << std::setprecision(decimals) << value;
    }
    return out.str();
}
} // namespace combination
