#include "Engine/Visualization/Charts/CstTrendPlot.hpp"
#include "Engine/Visualization/Charts/ChartStroke.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>

namespace combination {
using namespace crocker::engine;
using detail::Stroke;
void CstTrendPlot::RenderMagnetic(float width, float height, float pixelRatio, int kind) {
    // Port CST's grouped coil histories (0), metric sparklines (1), and fixed
    // 0..620 A trim overview (2). No RI smoothing or palette is applied.
    if (width <= 0 || height <= 0 || kind < 0 || kind > 3)
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    const bool spark = kind == 1, bars = kind == 2, source = kind == 3;
    const double sourceMinimum = -std::max(1., monitorSeconds) * 1.01,
                 sourceMaximum = std::max(1., monitorSeconds) * .01;
    context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip,
                  source ? Color{8 / 255.f, 14 / 255.f, 19 / 255.f}
                         : Color{11 / 255.f, 17 / 255.f, 21 / 255.f},
                  1, 1);
    const float left = spark ? 2.f : 44.f, right = width - 8, bottom = spark ? 2.f : 35.f,
                top = spark ? height - 2 : height - 30;
    if (right <= left || top <= bottom)
        return;
    double xmin = 0, xmax = 1, ymin = 0, ymax = 0;
    bool any = false;
    for (const auto &series : monitorTraces) {
        for (std::size_t i = 0; i < series.x.size(); ++i) {
            if (!std::isfinite(series.x[i]) || !std::isfinite(series.y[i]))
                continue;
            if (source && (series.x[i] < sourceMinimum || series.x[i] > sourceMaximum))
                continue;
            if (!any) {
                xmin = xmax = series.x[i];
                if (spark || source)
                    ymin = ymax = series.y[i];
                any = true;
            }
            xmin = std::min(xmin, series.x[i]);
            xmax = std::max(xmax, series.x[i]);
            ymin = std::min(ymin, series.y[i]);
            ymax = std::max(ymax, series.y[i]);
        }
    }
    if (xmax <= xmin) {
        xmin -= .5;
        xmax += .5;
    }
    if (ymax <= ymin) {
        ymin -= .5;
        ymax += .5;
    }
    const double xp = (xmax - xmin) * .02, yp = (ymax - ymin) * .04;
    xmin -= xp;
    xmax += xp;
    ymin -= yp;
    ymax += yp;
    if (bars) {
        xmin = .3;
        xmax = 12.7;
        ymin = 0;
        ymax = 620;
    }
    if (source) {
        xmin = sourceMinimum;
        xmax = sourceMaximum;
    }
    const auto mx = [&](double x) {
        return left + static_cast<float>((x - xmin) / (xmax - xmin)) * (right - left);
    };
    const auto my = [&](double y) {
        return bottom + static_cast<float>((y - ymin) / (ymax - ymin)) * (top - bottom);
    };
    const auto ndc = [&](Point p) { return Point{2 * p.x / width - 1, 2 * p.y / height - 1}; };
    const auto draw = [&](const std::vector<Point> &p, float size, Color color, float alpha = 1) {
        context_.Draw(Stroke(p, size, width, height), Primitive::Triangles, color, 1, alpha);
    };
    const Color grid = source ? Color{90 / 255.f, 103 / 255.f, 114 / 255.f}
                              : Color{49 / 255.f, 64 / 255.f, 74 / 255.f},
                muted = source ? Color{205 / 255.f, 214 / 255.f, 220 / 255.f}
                               : Color{159 / 255.f, 167 / 255.f, 173 / 255.f};
    const auto text = [&](const std::string &value, Point p, Color color, float size = 10,
                          HorizontalAlignment align = HorizontalAlignment::Center) {
        TextStyle s;
        s.font = context_.Fonts().Load();
        s.size = size;
        s.color = color;
        s.shadow = false;
        s.horizontalAlignment = align;
        canvas.DrawText(TextLayout(context_.Fonts()).Layout(value, s), p);
    };
    if (!spark) {
        const auto ya = CstTrendModel::NiceAxis(ymin, ymax, 5);
        for (const auto tick : CstTrendModel::Ticks(ya)) {
            if (tick < ymin || tick > ymax)
                continue;
            const float y = my(tick);
            draw({{left, y}, {right, y}}, 1, grid, .1f);
            text(CstTrendModel::FormatTick(tick, ya.step), {left - 5, y}, muted, 10,
                 HorizontalAlignment::Right);
        }
        if (bars) {
            for (int i = 1; i <= 12; ++i)
                text(std::to_string(i), {mx(i), bottom - 11}, muted, 9);
        } else {
            const auto xa = CstTrendModel::NiceAxis(xmin, xmax, 6);
            for (const auto tick : CstTrendModel::Ticks(xa)) {
                if (tick < xmin || tick > xmax)
                    continue;
                const float x = mx(tick);
                draw({{x, bottom}, {x, top}}, 1, grid, .1f);
                text(CstTrendModel::FormatTick(tick, xa.step), {x, bottom - 11}, muted);
            }
        }
        draw({{left, top}, {left, bottom}, {right, bottom}}, 1, grid, 170 / 255.f);
        if (!source)
            text(bars ? "TRIM COIL" : "Time (s)", {(left + right) / 2, 8}, muted);
        if (!bars)
            text(monitorTitle, {(left + right) / 2, height - 12},
                 source ? Color{242 / 255.f, 245 / 255.f, 247 / 255.f}
                        : Color{32 / 255.f, 156 / 255.f, 1},
                 source ? 13.3333f : 14.6667f);
    }
    float legendY = top - 8;
    for (const auto &series : monitorTraces) {
        if (bars) {
            if (series.x.empty() || series.y.empty() || !std::isfinite(series.y[0]))
                continue;
            const float x1 = mx(series.x[0] - .275), x2 = mx(series.x[0] + .275);
            const float y1 = my(0), y2 = my(std::clamp(series.y[0], 0., 620.));
            const auto a = ndc({x1, y1}), b = ndc({x2, y1}), c = ndc({x1, y2}), d = ndc({x2, y2});
            context_.Draw({a.x, a.y, b.x, b.y, c.x, c.y, d.x, d.y}, Primitive::TriangleStrip,
                          series.color, 1, 1, a.y, c.y, 4);
            draw({{x1, y1}, {x1, y2}, {x2, y2}, {x2, y1}}, .8f, series.color, 180 / 255.f);
            continue;
        }
        std::vector<Point> points;
        const auto flush = [&]() {
            if (points.empty())
                return;
            if (!spark && !source) {
                std::vector<float> fill;
                float peak = bottom;
                for (auto p : points) {
                    peak = std::max(peak, p.y);
                    auto a = ndc({p.x, my(0)}), b = ndc(p);
                    fill.insert(fill.end(), {a.x, a.y, b.x, b.y});
                }
                context_.Draw(fill, Primitive::TriangleStrip, series.color, 1, 1, ndc({0, my(0)}).y,
                              ndc({0, peak}).y, 3);
                draw(points, 5, series.color, 45 / 255.f);
            }
            if (source)
                draw(points, 6, series.color, 42 / 255.f);
            draw(points, spark ? 1.4f : 1.8f, series.color);
            points.clear();
        };
        for (std::size_t i = 0; i < series.x.size(); ++i) {
            if (!std::isfinite(series.x[i]) || !std::isfinite(series.y[i])) {
                flush();
                continue;
            }
            if (source && (series.x[i] < xmin || series.x[i] > xmax))
                continue;
            points.push_back({mx(series.x[i]), my(series.y[i])});
        }
        flush();
        if (!spark && !source) {
            draw({{right - 75, legendY}, {right - 57, legendY}}, 1.8f, series.color);
            text(series.name, {right - 8, legendY}, muted, 10, HorizontalAlignment::Right);
            legendY -= 16;
        }
    }
    canvas.Flush();
}
void CstTrendPlot::RenderTransport(float width, float height, float pixelRatio) {
    // CST BeamTransportMonitoringWindow: zero-inclusive Y, fixed receipt-age X,
    // two halos and a separate shadow ending at the visible plot floor.
    if (width <= 0 || height <= 0 || !std::isfinite(monitorSeconds) || monitorSeconds <= 0)
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip,
                  {11 / 255.f, 17 / 255.f, 21 / 255.f}, 1, 1);
    const float left = 58, right = width - 10, bottom = 42, top = height - 28;
    if (right <= left || top <= bottom)
        return;
    double low = 0, high = 0;
    for (std::size_t i = 0; i < monitorX.size(); ++i) {
        if (monitorX[i] >= -monitorSeconds && monitorX[i] <= 0 && std::isfinite(monitorY[i])) {
            low = std::min(low, monitorY[i]);
            high = std::max(high, monitorY[i]);
        }
    }
    const double padding = high > low ? (high - low) * 0.04 : 0.5;
    low -= padding;
    high += padding;
    const auto axis = CstTrendModel::NiceAxis(low, high, 5);
    const auto mapX = [&](double x) {
        return left + static_cast<float>((x + monitorSeconds) / monitorSeconds) * (right - left);
    };
    const auto mapY = [&](double y) {
        return bottom + static_cast<float>((y - low) / (high - low)) * (top - bottom);
    };
    const auto ndc = [&](Point p) { return Point{2 * p.x / width - 1, 2 * p.y / height - 1}; };
    const auto draw = [&](const std::vector<Point> &points, float size, Color color, float alpha) {
        context_.Draw(Stroke(points, size, width, height), Primitive::Triangles, color, 1, alpha);
    };
    const Color grid{49 / 255.f, 64 / 255.f, 74 / 255.f},
        muted{159 / 255.f, 167 / 255.f, 173 / 255.f};
    const auto text = [&](const std::string &value, Point position, Color color, float size = 10.f,
                          HorizontalAlignment align = HorizontalAlignment::Center,
                          float rotation = 0) {
        TextStyle style;
        style.font = context_.Fonts().Load();
        style.size = size;
        style.color = color;
        style.shadow = false;
        style.horizontalAlignment = align;
        style.rotationDegrees = rotation;
        canvas.DrawText(TextLayout(context_.Fonts()).Layout(value, style), position);
    };
    for (int i = 0; i < 3; ++i) {
        const double age = monitorSeconds * (1 - i / 2.0);
        const float x = mapX(-age);
        draw({{x, bottom}, {x, top}}, 1, grid, .1f);
        std::ostringstream label;
        if (i == 2)
            label << "Now";
        else
            label << "\xE2\x88\x92" << (age >= 60 ? age / 60 : age) << (age >= 60 ? " min" : " s");
        text(label.str(), {x, bottom - 12}, muted);
    }
    for (const auto tick : CstTrendModel::Ticks(axis)) {
        if (tick < low || tick > high)
            continue;
        const float y = mapY(tick);
        draw({{left, y}, {right, y}}, 1, grid, .1f);
        text(CstTrendModel::FormatTick(tick, axis.step), {left - 5, y}, muted, 10,
             HorizontalAlignment::Right);
    }
    draw({{left, top}, {left, bottom}, {right, bottom}}, 1, grid, 170 / 255.f);
    text(monitorTitle, {(left + right) / 2, height - 12}, {32 / 255.f, 156 / 255.f, 1}, 13.3333f);
    text("Time before now", {(left + right) / 2, 8}, muted);
    text("Current [A]", {11, (bottom + top) / 2}, muted, 10, HorizontalAlignment::Center, 90);
    std::vector<Point> segment;
    const auto flush = [&]() {
        if (segment.empty())
            return;
        // Geometry clips at the fixed receipt-age window before submission.
        std::vector<float> fill;
        for (const auto p : segment) {
            auto a = ndc({p.x, bottom}), b = ndc(p);
            fill.insert(fill.end(), {a.x, a.y, b.x, b.y});
        }
        context_.Draw(fill, Primitive::TriangleStrip, actualColor, 1, 1, ndc({0, bottom}).y,
                      ndc({0, top}).y, 2);
        draw(segment, 10, actualColor, 32 / 255.f);
        draw(segment, 4.5f, actualColor, 90 / 255.f);
        draw(segment, 1.8f, actualColor, 1);
        segment.clear();
    };
    for (std::size_t i = 0; i < monitorX.size(); ++i) {
        const double x = monitorX[i], y = monitorY[i];
        if (!std::isfinite(x) || !std::isfinite(y)) {
            flush();
            continue;
        }
        if (x < -monitorSeconds || x > 0)
            continue;
        segment.push_back({mapX(x), mapY(y)});
    }
    flush();
    canvas.Flush();
}
void CstTrendPlot::Render(float width, float height, float pixelRatio) {
    RenderStyled(width, height, pixelRatio, false);
}
void CstTrendPlot::RenderCalibration(float width, float height, float pixelRatio) {
    RenderStyled(width, height, pixelRatio, true);
}
void CstTrendPlot::RenderStyled(float width, float height, float pixelRatio, bool calibration) {
    if (!std::isfinite(width) || !std::isfinite(height) || width <= 0 || height <= 0)
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    const auto ndc = [&](float x, float y) { return Point{2 * x / width - 1, 2 * y / height - 1}; };
    const auto draw = [&](const std::vector<Point> &points, float size, Color color,
                          float alpha = 1.f) {
        context_.Draw(Stroke(points, size, width, height), Primitive::Triangles, color, 1, alpha);
    };
    context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip,
                  calibration ? Color{12 / 255.f, 20 / 255.f, 36 / 255.f}
                              : Color{11 / 255.f, 17 / 255.f, 22 / 255.f},
                  1, 1);
    // CST margins and plot semantics. Coordinates here are bottom-origin.
    const float left = 78, right = width - 16, bottom = 48, top = height - (calibration ? 34 : 12);
    if (right - left <= 20 || top - bottom <= 20)
        return;
    const auto xAxis = model.XAxis(), yAxis = model.YAxis();
    const auto mapX = [&](double v) {
        return left + static_cast<float>((v - xAxis.minimum) / (xAxis.maximum - xAxis.minimum)) *
                          (right - left);
    };
    const auto mapY = [&](double v) {
        return bottom + static_cast<float>((v - yAxis.minimum) / (yAxis.maximum - yAxis.minimum)) *
                            (top - bottom);
    };
    const Color border = calibration ? Color{56 / 255.f, 90 / 255.f, 134 / 255.f}
                                     : Color{39 / 255.f, 50 / 255.f, 58 / 255.f},
                muted = calibration ? Color{169 / 255.f, 198 / 255.f, 209 / 255.f}
                                    : Color{170 / 255.f, 181 / 255.f, 188 / 255.f};
    const auto text = [&](const std::string &value, Point p,
                          HorizontalAlignment align = HorizontalAlignment::Center,
                          float rotation = 0) {
        TextStyle style;
        style.font = context_.Fonts().Load();
        style.size = 10.666667f;
        style.color = muted;
        style.shadow = false;
        style.horizontalAlignment = align;
        style.rotationDegrees = rotation;
        canvas.DrawText(TextLayout(context_.Fonts()).Layout(value, style), p);
    };
    // All grid segments are submitted together; labels are flushed once at end.
    std::vector<float> grid;
    const auto segment = [&](float x1, float y1, float x2, float y2) {
        const auto a = ndc(x1, y1), b = ndc(x2, y2);
        grid.insert(grid.end(), {a.x, a.y, b.x, b.y});
    };
    for (const auto tick : CstTrendModel::Ticks(xAxis)) {
        const auto x = mapX(tick);
        segment(std::floor(x), bottom, std::floor(x), top);
        text(CstTrendModel::FormatTick(tick, xAxis.step), {x, bottom - 13});
    }
    for (const auto tick : CstTrendModel::Ticks(yAxis)) {
        const auto y = mapY(tick);
        segment(left, std::floor(y), right, std::floor(y));
        text(CstTrendModel::FormatTick(tick, yAxis.step), {left - 6, y},
             HorizontalAlignment::Right);
    }
    context_.Draw(grid, Primitive::Lines, border, 1, 135 / 255.f);
    draw({{left, bottom}, {right, bottom}}, 1, border);
    draw({{left, bottom}, {left, top}}, 1, border);
    text(model.relativeTime && model.IsTimeAxis() ? "TIME (s; 0 = latest)" : model.xLabel,
         {(left + right) / 2, 11});
    text(model.yLabel, {12, (bottom + top) / 2}, HorizontalAlignment::Center, 90);
    if (calibration) {
        text(chartTitle, {(left + right) / 2, height - 15});
        if (model.rows.size() < 2)
            text("No curve points", {(left + right) / 2, (bottom + top) / 2});
    }
    if (model.rows.size() >= 2) {
        std::vector<Point> target, actual, third;
        for (const auto &row : model.rows) {
            target.push_back({mapX(row[0]), mapY(row[1])});
            actual.push_back({mapX(row[0]), mapY(row[2])});
            if (model.hasThird)
                third.push_back({mapX(row[0]), mapY(row[3])});
        }
        if (calibration) {
            draw(actual, 8, actualColor, .18f);
            draw(actual, 2.2f, actualColor);
            for (auto p : actual)
                draw({p}, 5, actualColor);
            // Reference is the straight line through the configured endpoints.
            // Subdivide in screen space so dashes have stable pixel lengths.
            const auto a = actual.front(), b = actual.back();
            const float length = std::hypot(b.x - a.x, b.y - a.y);
            for (float start = 0; start < length; start += 10) {
                const float finish = std::min(length, start + 6);
                draw({{a.x + (b.x - a.x) * start / length, a.y + (b.y - a.y) * start / length},
                      {a.x + (b.x - a.x) * finish / length, a.y + (b.y - a.y) * finish / length}},
                     1.4f, targetColor, .8f);
            }
        } else {
            if (!model.hasThird) {
                std::vector<float> fill;
                fill.reserve(actual.size() * 4);
                for (const auto p : actual) {
                    const auto a = ndc(p.x, bottom), b = ndc(p.x, p.y);
                    fill.insert(fill.end(), {a.x, a.y, b.x, b.y});
                }
                context_.Draw(fill, Primitive::TriangleStrip, actualColor, 1, 1, ndc(0, bottom).y,
                              ndc(0, top).y);
                draw(actual, 9, actualColor, 45 / 255.f);
            }
            draw(target, 2, targetColor);
            draw(actual, model.hasThird ? 1.5f : 2.f, actualColor,
                 model.hasThird ? 170 / 255.f : 1.f);
            if (model.hasThird) {
                draw(third, 7, thirdColor, 50 / 255.f);
                draw(third, 2.5f, thirdColor);
            }
            draw({actual.back()}, 7, actualColor);
            if (model.hasThird)
                draw({third.back()}, 8, thirdColor);
        }
    }
    canvas.Flush();
}
void CstTrendPlot::RenderBeam(float width, float height, float pixelRatio, double now) {
    // Port of CST MagneticFieldControllerWindow._ControllerBeamPlot. Keep its
    // independent 30-second axis and autoscale; do not substitute PID axes.
    if (!std::isfinite(width) || !std::isfinite(height) || width <= 0 || height <= 0 ||
        !std::isfinite(now))
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    const float left = 54, right = std::max(left + 1, width - 12), bottom = 26,
                top = std::max(bottom + 1, height - 12);
    const Color panel{11 / 255.f, 17 / 255.f, 22 / 255.f}, area{14 / 255.f, 20 / 255.f, 25 / 255.f};
    const Color border{27 / 255.f, 37 / 255.f, 44 / 255.f},
        dim{116 / 255.f, 129 / 255.f, 138 / 255.f};
    const auto ndc = [&](float x, float y) { return Point{2 * x / width - 1, 2 * y / height - 1}; };
    context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip, panel, 1, 1);
    const auto bl = ndc(left, bottom), tr = ndc(right, top);
    context_.Draw({bl.x, bl.y, tr.x, bl.y, bl.x, tr.y, tr.x, tr.y}, Primitive::TriangleStrip, area,
                  1, 1);
    std::vector<std::pair<double, double>> samples;
    for (const auto &row : model.rows)
        if (row[0] >= now - 30 && row[0] <= now)
            samples.emplace_back(row[0], row[2]);
    double lo = 0, hi = 1;
    if (!samples.empty()) {
        lo = hi = samples.front().second;
        for (const auto [stamp, value] : samples) {
            lo = std::min(lo, value);
            hi = std::max(hi, value);
        }
        const auto pad = std::max({.05, std::abs(hi) * .06, (hi - lo) * .3});
        lo -= pad;
        hi += pad;
    }
    const auto text = [&](const std::string &value, Point p,
                          HorizontalAlignment align = HorizontalAlignment::Center) {
        TextStyle style;
        style.font = context_.Fonts().Load();
        style.size = 10;
        style.color = dim;
        style.shadow = false;
        style.horizontalAlignment = align;
        canvas.DrawText(TextLayout(context_.Fonts()).Layout(value, style), p);
    };
    std::vector<float> grid;
    const auto segment = [&](float x1, float y1, float x2, float y2) {
        const auto a = ndc(x1, y1), b = ndc(x2, y2);
        grid.insert(grid.end(), {a.x, a.y, b.x, b.y});
    };
    const char *captions[] = {"\xe2\x88\x92"
                              "30 s",
                              "\xe2\x88\x92"
                              "20 s",
                              "\xe2\x88\x92"
                              "10 s",
                              "now"};
    for (int i = 0; i < 4; ++i) {
        const auto fraction = i / 3.f, x = left + (right - left) * fraction,
                   y = top - (top - bottom) * fraction;
        segment(left, y, right, y);
        segment(x, bottom, x, top);
        const auto value = hi - (hi - lo) * fraction;
        std::ostringstream label;
        if (std::abs(value) < 100)
            label << std::fixed << std::setprecision(2) << value;
        else
            label << std::setprecision(3) << value;
        text(label.str(), {48, y}, HorizontalAlignment::Right);
        text(captions[i], {x, bottom - 15});
    }
    context_.Draw(grid, Primitive::Lines, border, 1, 1);
    if (samples.empty())
        text("Waiting for beam data", {(left + right) / 2, (bottom + top) / 2});
    else {
        std::vector<Point> points;
        double previous = samples.front().first;
        for (const auto [stamp, value] : samples) {
            if (stamp - previous > 1)
                points.push_back({0, std::numeric_limits<float>::quiet_NaN()});
            points.push_back(
                {right - static_cast<float>((now - stamp) / 30) * (right - left),
                 bottom + static_cast<float>((value - lo) / (hi - lo)) * (top - bottom)});
            previous = stamp;
        }
        context_.Draw(Stroke(points, 1.7f, width, height), Primitive::Triangles, targetColor, 1, 1);
        context_.Draw(Stroke({points.back()}, 5, width, height), Primitive::Triangles, targetColor,
                      1, 1);
    }
    canvas.Flush();
}
void CstTrendPlot::RenderManual(float width, float height, float pixelRatio) {
    // CST controller_theme.TrendPlot deliberately has no numeric tick labels.
    if (width <= 0 || height <= 0)
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    const Color panel{11 / 255.f, 17 / 255.f, 22 / 255.f},
        border{39 / 255.f, 50 / 255.f, 58 / 255.f}, muted{170 / 255.f, 181 / 255.f, 188 / 255.f};
    context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip, panel, 1, 1);
    const float left = 62, right = width - 18, bottom = 42, top = height - 18;
    if (right - left <= 10 || top - bottom <= 10)
        return;
    const auto ndc = [&](float x, float y) { return Point{2 * x / width - 1, 2 * y / height - 1}; };
    const auto stroke = [&](const std::vector<Point> &points, float size, Color color,
                            float alpha = 1.f) {
        context_.Draw(Stroke(points, size, width, height), Primitive::Triangles, color, 1, alpha);
    };
    std::vector<float> grid;
    for (int i = 0; i < 9; ++i) {
        const auto x = left + (right - left) * i / 8, y = bottom + (top - bottom) * i / 8;
        const auto a = ndc(x, bottom), b = ndc(x, top), c = ndc(left, y), d = ndc(right, y);
        grid.insert(grid.end(), {a.x, a.y, b.x, b.y, c.x, c.y, d.x, d.y});
    }
    context_.Draw(grid, Primitive::Lines, border, 1, 120 / 255.f);
    stroke({{left, bottom}, {right, bottom}}, 1, border);
    stroke({{left, bottom}, {left, top}}, 1, border);
    TextStyle style;
    style.font = context_.Fonts().Load();
    style.size = 12;
    style.color = muted;
    style.shadow = false;
    style.horizontalAlignment = HorizontalAlignment::Left;
    style.verticalAlignment = VerticalAlignment::Baseline;
    canvas.DrawText(TextLayout(context_.Fonts()).Layout(model.xLabel, style), {left, 12});
    style.rotationDegrees = 90;
    canvas.DrawText(TextLayout(context_.Fonts()).Layout(model.yLabel, style),
                    {16, (bottom + top) / 2 - 34});
    if (model.rows.size() >= 2) {
        double xMin = model.rows[0][0], xMax = xMin, yMin = model.rows[0][1], yMax = yMin;
        for (const auto &row : model.rows) {
            xMin = std::min(xMin, row[0]);
            xMax = std::max(xMax, row[0]);
            yMin = std::min({yMin, row[1], row[2]});
            yMax = std::max({yMax, row[1], row[2]});
        }
        if (std::abs(xMax - xMin) < 1e-12)
            xMax = xMin + 1;
        const auto pad = std::abs(yMax - yMin) < 1e-12 ? std::max(1.0, std::abs(yMax) * .1)
                                                       : .08 * (yMax - yMin);
        yMin -= pad;
        yMax += pad;
        const auto map = [&](double x, double y) {
            return Point{left + static_cast<float>((x - xMin) / (xMax - xMin)) * (right - left),
                         bottom + static_cast<float>((y - yMin) / (yMax - yMin)) * (top - bottom)};
        };
        std::vector<Point> target, actual;
        std::vector<float> fill;
        for (const auto &row : model.rows) {
            target.push_back(map(row[0], row[1]));
            actual.push_back(map(row[0], row[2]));
            const auto a = ndc(actual.back().x, bottom), b = ndc(actual.back().x, actual.back().y);
            fill.insert(fill.end(), {a.x, a.y, b.x, b.y});
        }
        context_.Draw(fill, Primitive::TriangleStrip, actualColor, 1, 1, ndc(0, bottom).y,
                      ndc(0, top).y, 1);
        stroke(actual, 10, actualColor, 50 / 255.f);
        stroke(target, 2, targetColor);
        stroke(actual, 2, actualColor);
        stroke(actual, 1, {1, 218 / 255.f, 150 / 255.f}, 165 / 255.f);
        stroke({actual.back()}, 9, actualColor);
    }
    canvas.Flush();
}
void CstTrendPlot::RenderGains(float width, float height, float pixelRatio) {
    // CST PIDGainRadar geometry/scaling; no plotting math is done by Python.
    if (width <= 0 || height <= 0)
        return;
    context_.SetPixelRatio(pixelRatio);
    Canvas2D canvas(context_);
    canvas.BeginFrame();
    const Color panel{11 / 255.f, 17 / 255.f, 22 / 255.f},
        border{39 / 255.f, 50 / 255.f, 58 / 255.f};
    context_.Draw({-1, -1, 1, -1, -1, 1, 1, 1}, Primitive::TriangleStrip, panel, 1, 1);
    const float cx = width * .5f, cy = height * .48f,
                radius = std::max(36.f, std::min(width, height) * .34f);
    const std::array<float, 3> angles{90, -30, 210};
    const auto point = [&](float r, float degrees) {
        const float a = degrees * .017453292519943295f;
        return Point{cx + r * std::cos(a), cy + r * std::sin(a)};
    };
    const auto stroke = [&](const std::vector<Point> &points, float size, Color color) {
        context_.Draw(Stroke(points, size, width, height), Primitive::Triangles, color, 1, 1);
    };
    for (const float fraction : {.25f, .5f, .75f, 1.f}) {
        std::vector<Point> ring;
        for (const auto angle : angles)
            ring.push_back(point(radius * fraction, angle));
        ring.push_back(ring.front());
        stroke(ring, 1, border);
    }
    for (const auto angle : angles)
        stroke({{cx, cy}, point(radius, angle)}, 1, border);
    std::array<double, 3> values{}, scales{};
    const std::array<double, 3> base{.05, .001, .001};
    for (int i = 0; i < 3; ++i) {
        values[i] = std::max(0.0, gains[i]);
        scales[i] = std::max({base[i], values[i] * 1.25, 1e-12});
    }
    std::vector<Point> polygon{
        point(radius * static_cast<float>(values[0] / scales[0]), angles[0]),
        point(radius * static_cast<float>(values[2] / scales[2]), angles[1]),
        point(radius * static_cast<float>(values[1] / scales[1]), angles[2])};
    std::vector<float> fill;
    for (const auto p : polygon)
        fill.insert(fill.end(), {2 * p.x / width - 1, 2 * p.y / height - 1});
    context_.Draw(fill, Primitive::Triangles, targetColor, 1, 55 / 255.f);
    auto outline = polygon;
    outline.push_back(outline.front());
    stroke(outline, 2, {120 / 255.f, 201 / 255.f, 1});
    for (const auto p : polygon)
        stroke({p}, 8, actualColor);
    TextStyle style;
    style.font = context_.Fonts().Load();
    style.size = 12;
    style.shadow = false;
    style.color = {232 / 255.f, 237 / 255.f, 240 / 255.f};
    const char *labels[] = {"Kp", "Kd", "Ki"};
    for (int i = 0; i < 3; ++i)
        canvas.DrawText(TextLayout(context_.Fonts()).Layout(labels[i], style),
                        point(radius + 20, angles[i]));
    style.size = 9.333333f;
    style.color = {116 / 255.f, 129 / 255.f, 138 / 255.f};
    std::ostringstream text;
    text << std::setprecision(3) << "axis max: Kp " << scales[0] << "   Ki " << scales[1]
         << "   Kd " << scales[2];
    canvas.DrawText(TextLayout(context_.Fonts()).Layout(text.str(), style), {cx, 12});
    canvas.Flush();
}
} // namespace combination
