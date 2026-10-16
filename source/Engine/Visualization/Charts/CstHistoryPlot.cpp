#include "Engine/Visualization/Charts/ChartStroke.hpp"
#include "Engine/Visualization/Charts/CstTrendPlot.hpp"
#include <algorithm>
#include <cmath>
#include <glad/glad.h>
#include <iomanip>
#include <sstream>

namespace combination {
using namespace crocker::engine;
std::array<double, 4> CstTrendPlot::HistoryBounds() const {
    double xmin = INFINITY, xmax = -INFINITY, ymin = INFINITY, ymax = -INFINITY;
    for (const auto &series : monitorTraces)
        for (std::size_t i = 0; i < series.x.size(); ++i) {
            const double x = series.x[i], y = series.y[i];
            if (!std::isfinite(x) || !std::isfinite(y) || (historyLog && y <= 0))
                continue;
            xmin = std::min(xmin, x);
            xmax = std::max(xmax, x);
            ymin = std::min(ymin, y);
            ymax = std::max(ymax, y);
        }
    if (!std::isfinite(xmin)) {
        xmin = 0;
        xmax = 1;
        ymin = historyLog ? 1 : 0;
        ymax = historyLog ? 10 : 1;
    }
    if (xmin == xmax) {
        xmin -= .5;
        xmax += .5;
    }
    const double xp = (xmax - xmin) * .05;
    xmin -= xp;
    xmax += xp;
    double a = historyLog ? std::log10(ymin) : std::min(0., ymin),
           b = historyLog ? std::log10(ymax) : std::max(0., ymax);
    const double yp = std::max((b - a) * .05, a == b ? std::max(.05, std::abs(a) * .05) : 1e-12);
    a -= yp;
    b += yp;
    ymin = historyLog ? std::pow(10., a) : a;
    ymax = historyLog ? std::pow(10., b) : b;
    if (std::isfinite(historyX[0]) && std::isfinite(historyX[1]) && historyX[0] < historyX[1]) {
        xmin = historyX[0];
        xmax = historyX[1];
    }
    if (std::isfinite(historyY[0]) && std::isfinite(historyY[1]) && historyY[0] < historyY[1] &&
        (!historyLog || historyY[0] > 0)) {
        ymin = historyY[0];
        ymax = historyY[1];
    }
    return {xmin, xmax, ymin, ymax};
}
std::array<double, 2> CstTrendPlot::HistoryPoint(double x, double y, double width,
                                                 double height) const {
    if (width <= 86 || height <= 48 || x < 66 || x > width - 20 || y < 12 || y > height - 36)
        return {NAN, NAN};
    const auto b = HistoryBounds();
    const double xf = (x - 66) / (width - 86), yf = (height - 36 - y) / (height - 48);
    const double lo = historyLog ? std::log10(b[2]) : b[2],
                 hi = historyLog ? std::log10(b[3]) : b[3];
    return {b[0] + xf * (b[1] - b[0]),
            historyLog ? std::pow(10., lo + yf * (hi - lo)) : lo + yf * (hi - lo)};
}
void CstTrendPlot::ZoomHistory(double factor, double center) {
    if (!std::isfinite(factor) || factor <= 0)
        throw std::invalid_argument("Zoom factor must be positive");
    const auto b = HistoryBounds();
    double lo = historyLog ? std::log10(b[2]) : b[2], hi = historyLog ? std::log10(b[3]) : b[3];
    center = std::isfinite(center) && (!historyLog || center > 0)
                 ? (historyLog ? std::log10(center) : center)
                 : (lo + hi) / 2;
    lo = center + (lo - center) / factor;
    hi = center + (hi - center) / factor;
    if (hi - lo < 1e-10)
        return;
    historyY = {historyLog ? std::pow(10., lo) : lo, historyLog ? std::pow(10., hi) : hi};
}
void CstTrendPlot::RenderHistory(float width, float height, float pixelRatio) {
    if (width <= 86 || height <= 48)
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    const Color panel = historyPaper ? Color{1, 1, 1} : Color{24 / 255.f, 26 / 255.f, 30 / 255.f},
                grid =
                    historyPaper ? Color{.8f, .8f, .8f} : Color{48 / 255.f, 52 / 255.f, 59 / 255.f},
                ink = historyPaper ? Color{.1f, .1f, .1f}
                                   : Color{236 / 255.f, 239 / 255.f, 243 / 255.f};
    context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip, panel, 1, 1);
    const float left = 66, right = width - 20, bottom = 36, top = height - 12;
    const auto bounds = HistoryBounds();
    const double low = historyLog ? std::log10(bounds[2]) : bounds[2],
                 high = historyLog ? std::log10(bounds[3]) : bounds[3];
    const auto mx = [&](double x) {
        return left +
               static_cast<float>((x - bounds[0]) / (bounds[1] - bounds[0])) * (right - left);
    };
    const auto my = [&](double y) {
        return bottom +
               static_cast<float>(((historyLog ? std::log10(y) : y) - low) / (high - low)) *
                   (top - bottom);
    };
    const auto ndc = [&](Point p) { return Point{2 * p.x / width - 1, 2 * p.y / height - 1}; };
    const auto draw = [&](const std::vector<Point> &p, float size, Color color, float alpha = 1) {
        context_.Draw(detail::Stroke(p, size, width, height), Primitive::Triangles, color, 1,
                      alpha);
    };
    const auto text =
        [&](const std::string &value, Point p, Color color = Color{.925f, .937f, .953f},
            HorizontalAlignment align = HorizontalAlignment::Center, float rotation = 0) {
            TextStyle style;
            style.font = context_.Fonts().Load();
            style.size = 12;
            style.color = color;
            style.shadow = false;
            style.horizontalAlignment = align;
            style.rotationDegrees = rotation;
            canvas.DrawText(TextLayout(context_.Fonts()).Layout(value, style), p);
        };
    const auto ya = CstTrendModel::NiceAxis(low, high, 5);
    for (double tick : CstTrendModel::Ticks(ya)) {
        if (tick < low || tick > high)
            continue;
        const double value = historyLog ? std::pow(10., tick) : tick;
        const float y = my(value);
        draw({{left, y}, {right, y}}, .7f, grid, .8f);
        std::ostringstream label;
        if (historyScientific || historyLog)
            label << std::scientific << std::setprecision(1) << value;
        else
            label << CstTrendModel::FormatTick(tick, ya.step);
        text(label.str(), {left - 6, y}, ink, HorizontalAlignment::Right);
    }
    const auto xa = CstTrendModel::NiceAxis(bounds[0], bounds[1], 8);
    for (double tick : CstTrendModel::Ticks(xa)) {
        if (tick < bounds[0] || tick > bounds[1])
            continue;
        const float x = mx(tick);
        draw({{x, bottom}, {x, top}}, .7f, grid, .8f);
    }
    draw({{left, top}, {left, bottom}, {right, bottom}, {right, top}, {left, top}}, 1,
         {66 / 255.f, 72 / 255.f, 82 / 255.f});
    text("Sample", {(left + right) / 2, 10}, ink);
    text(historyLabel, {12, (bottom + top) / 2}, ink, HorizontalAlignment::Center, 90);
    // Preserve the host's scissor state while zoomed traces are clipped.
    GLint oldBox[4], viewport[4];
    glGetIntegerv(GL_SCISSOR_BOX, oldBox);
    glGetIntegerv(GL_VIEWPORT, viewport);
    const bool oldEnabled = glIsEnabled(GL_SCISSOR_TEST) != 0;
    glEnable(GL_SCISSOR_TEST);
    glScissor(viewport[0] + static_cast<int>(left * pixelRatio),
              viewport[1] + static_cast<int>(bottom * pixelRatio),
              static_cast<int>((right - left) * pixelRatio),
              static_cast<int>((top - bottom) * pixelRatio));
    for (const auto &series : monitorTraces) {
        std::vector<Point> points;
        const auto flush = [&]() {
            if (points.empty())
                return;
            std::vector<float> fill;
            for (auto p : points) {
                auto a = ndc({p.x, historyLog ? bottom : my(0)}), b = ndc(p);
                fill.insert(fill.end(), {a.x, a.y, b.x, b.y});
            }
            context_.Draw(fill, Primitive::TriangleStrip, series.color, 1, .035f);
            draw(points, 5, series.color, .12f);
            draw(points, 1.6f, series.color);
            if (points.size() == 1)
                draw(points, 5, series.color);
            points.clear();
        };
        for (std::size_t i = 0; i < series.x.size(); ++i) {
            const double x = series.x[i], y = series.y[i];
            if (!std::isfinite(x) || !std::isfinite(y) || (historyLog && y <= 0)) {
                flush();
                continue;
            }
            points.push_back({mx(x), my(y)});
        }
        flush();
    }
    if (std::isfinite(cursorX))
        draw({{mx(cursorX), bottom}, {mx(cursorX), top}}, 1.5f,
             {232 / 255.f, 59 / 255.f, 69 / 255.f}, .8f);
    if (std::isfinite(cursorY) && (!historyLog || cursorY > 0))
        draw({{left, my(cursorY)}, {right, my(cursorY)}}, 1.5f,
             {232 / 255.f, 59 / 255.f, 69 / 255.f}, .8f);
    for (const auto &marker : historyMarkers)
        draw({{mx(marker.x), bottom}, {mx(marker.x), top}}, 1.25f, marker.color, .9f);
    glScissor(oldBox[0], oldBox[1], oldBox[2], oldBox[3]);
    if (!oldEnabled)
        glDisable(GL_SCISSOR_TEST);
    float legendY = top - 10;
    for (const auto &series : monitorTraces) {
        text(series.name, {right - 8, legendY}, series.color, HorizontalAlignment::Right);
        legendY -= 17;
    }
    int i = 0;
    for (const auto &marker : historyMarkers) {
        text(marker.text, {left + 10 + (i % 3) * (right - left) / 3, top - 35 - (i / 3) * 65},
             marker.color, HorizontalAlignment::Left);
        ++i;
    }
    if (!cursorText.empty())
        text(cursorText, {left + 8, bottom + 18}, ink, HorizontalAlignment::Left);
    canvas.Flush();
}
} // namespace combination
