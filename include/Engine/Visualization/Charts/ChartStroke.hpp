#pragma once
#include "Engine/Graphics/Canvas2D.hpp"
#include <cmath>
#include <vector>
using crocker::engine::Point;
namespace combination::detail {
// Round caps and joins are tessellated, avoiding driver-dependent wide lines.
inline std::vector<float> Stroke(const std::vector<Point> &points, float width, float w, float h) {
    std::vector<float> vertices;
    vertices.reserve(points.size() * 84);
    const auto add = [&](Point p) {
        vertices.push_back(2 * p.x / w - 1);
        vertices.push_back(2 * p.y / h - 1);
    };
    const auto radius = width / 2;
    for (std::size_t i = 1; i < points.size(); ++i) {
        const auto a = points[i - 1], b = points[i];
        if (!std::isfinite(a.x) || !std::isfinite(a.y) || !std::isfinite(b.x) ||
            !std::isfinite(b.y))
            continue;
        const auto length = std::hypot(b.x - a.x, b.y - a.y);
        if (length <= 0)
            continue;
        const float nx = -(b.y - a.y) / length * radius, ny = (b.x - a.x) / length * radius;
        const Point p{a.x + nx, a.y + ny}, q{a.x - nx, a.y - ny}, r{b.x + nx, b.y + ny},
            s{b.x - nx, b.y - ny};
        add(p);
        add(q);
        add(r);
        add(r);
        add(q);
        add(s);
    }
    for (const auto p : points)
        for (int i = 0; i < 12; ++i) {
            if (!std::isfinite(p.x) || !std::isfinite(p.y))
                continue;
            const auto a = i * 6.28318530718f / 12, b = (i + 1) * 6.28318530718f / 12;
            add(p);
            add({p.x + radius * std::cos(a), p.y + radius * std::sin(a)});
            add({p.x + radius * std::cos(b), p.y + radius * std::sin(b)});
        }
    return vertices;
}
} // namespace combination::detail
