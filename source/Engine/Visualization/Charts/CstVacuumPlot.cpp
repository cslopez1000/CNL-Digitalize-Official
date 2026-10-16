#include "Engine/Visualization/Charts/ChartStroke.hpp"
#include "Engine/Visualization/Charts/CstTrendPlot.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>

namespace combination {
using namespace crocker::engine;
void CstTrendPlot::RenderVacuum(float width, float height, float pixelRatio, bool embedded,
                                double minimum, double maximum, int maxPoints, double pulse,
                                double seconds) {
    if (width <= 0 || height <= 0 || !std::isfinite(minimum) || !std::isfinite(maximum))
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    const auto ndc = [&](Point p) { return Point{2 * p.x / width - 1, 2 * p.y / height - 1}; };
    const auto draw = [&](const std::vector<Point> &points, float size, Color color,
                          float alpha = 1) {
        context_.Draw(detail::Stroke(points, size, width, height), Primitive::Triangles, color, 1,
                      alpha);
    };
    const auto text = [&](const std::string &value, Point p, float size = 11,
                          HorizontalAlignment align = HorizontalAlignment::Center) {
        TextStyle style;
        style.font = context_.Fonts().Load();
        style.size = size;
        style.color = {235 / 255.f, 238 / 255.f, 242 / 255.f};
        style.shadow = false;
        style.horizontalAlignment = align;
        canvas.DrawText(TextLayout(context_.Fonts()).Layout(value, style), p);
    };
    if (!embedded)
        context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip, {1, 1, 1}, 1, 1, -1,
                      1, 5);
    const float bottom = embedded ? 20.f : 0.f, top = height;
    if (embedded) {
        draw({{0, (bottom + top) / 2}, {width, (bottom + top) / 2}}, 1, {1, 1, 1}, 18 / 255.f);
        for (int i = 1; i <= 3; ++i)
            draw({{width * i / 4, bottom}, {width * i / 4, top}}, 1, {1, 1, 1}, 18 / 255.f);
    } else {
        for (int i = 1; i < 8; ++i)
            draw({{0, height * i / 8}, {width, height * i / 8}}, .7f, {1, 1, 1},
                 (i % 2 == 0 ? 20 : 11) / 255.f);
        for (int i = 1; i < 12; ++i)
            draw({{width * i / 12, 0}, {width * i / 12, height}}, .7f, {1, 1, 1},
                 (i % 2 == 0 ? 20 : 11) / 255.f);
        text(chartTitle, {width / 2, height - 18}, 14.6667f);
    }
    std::vector<double> values;
    for (double value : monitorY) {
        if (!embedded)
            values.push_back(value);
        else if (std::isfinite(value) && value > 0)
            values.push_back(std::log10(value));
    }
    if (embedded && values.size() < 2) {
        text("BUILDING HISTORY", {width / 2, (bottom + top) / 2}, 10);
        canvas.Flush();
        return;
    }
    if (embedded) {
        const auto bounds = std::minmax_element(values.begin(), values.end());
        minimum = *bounds.first;
        maximum = *bounds.second;
        const double span = maximum - minimum;
        if (span < .030) {
            const double center = (maximum + minimum) / 2;
            minimum = center - .015;
            maximum = center + .015;
        } else {
            minimum -= span * .16;
            maximum += span * .16;
        }
    }
    const double span = maximum != minimum ? maximum - minimum : 1;
    std::vector<Point> points;
    for (std::size_t i = 0; i < values.size(); ++i) {
        const double fraction =
            static_cast<double>(i) /
            std::max(1, embedded ? static_cast<int>(values.size()) - 1 : maxPoints - 1);
        // QPainter's source widget clips paths to its widget rectangle.
        const double norm = std::clamp((values[i] - minimum) / span, 0., 1.);
        points.push_back({static_cast<float>(width * fraction),
                          bottom + static_cast<float>(norm) * (top - bottom)});
    }
    if (points.size() >= 2) {
        if (!embedded) {
            std::vector<float> fill;
            for (auto p : points) {
                auto a = ndc({p.x, 0}), b = ndc(p);
                fill.insert(fill.end(), {a.x, a.y, b.x, b.y});
            }
            context_.Draw(fill, Primitive::TriangleStrip, actualColor, 1, 1, -1, 1, 6);
        }
        draw(points, embedded ? 5.f : 2.4f, actualColor, (embedded ? 55 : 26) / 255.f);
        draw(points, embedded ? 1.7f : 2.f, actualColor);
        draw({points.back()}, 8, actualColor);
        draw({points.back()}, embedded ? 5.f : 6.f,
             embedded ? Color{4 / 255.f, 8 / 255.f, 11 / 255.f} : Color{1, 1, 1},
             embedded ? 1.f : static_cast<float>(150 + 100 * std::sin(pulse)) / 255.f);
    }
    if (embedded) {
        std::ostringstream label;
        label << std::fixed << std::setprecision(0) << seconds << " s";
        text(label.str(), {0, 8}, 10, HorizontalAlignment::Left);
        text("0 s", {width, 8}, 10, HorizontalAlignment::Right);
    } else if (!values.empty()) {
        draw({{0, height}, {0, 1}, {width, 1}}, 2, {1, 1, 1}, 45 / 255.f);
        std::ostringstream value;
        value << std::fixed << std::setprecision(3) << values.back();
        const float textWidth = canvas.MeasureText(value.str(), 12);
        const Point boxMin{width - textWidth - 12, height - 28}, boxMax{width - 4, height - 8};
        const auto a = ndc(boxMin), b = ndc(boxMax);
        context_.Draw({a.x, a.y, b.x, a.y, a.x, b.y, b.x, b.y}, Primitive::TriangleStrip, {0, 0, 0},
                      1, 180 / 255.f);
        draw({boxMin, {boxMax.x, boxMin.y}, boxMax, {boxMin.x, boxMax.y}, boxMin}, 1, actualColor);
        text(value.str(), {width - 8, height - 18}, 12, HorizontalAlignment::Right);
    }
    canvas.Flush();
}
} // namespace combination
