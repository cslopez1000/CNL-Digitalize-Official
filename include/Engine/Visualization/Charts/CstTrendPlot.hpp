#pragma once
#include "CstTrendModel.hpp"
#include "Engine/Graphics/Canvas2D.hpp"
#include <limits>
namespace combination {
inline constexpr double MissingHistoryValue = std::numeric_limits<double>::quiet_NaN();
struct HistoryMarker {
    double x;
    std::string text;
    crocker::engine::Color color;
};
struct MonitorTrace {
    std::vector<double> x, y;
    crocker::engine::Color color;
    std::string name;
};
class CstTrendPlot {
  public:
    CstTrendModel model;
    crocker::engine::Color targetColor{105 / 255.f, 189 / 255.f, 247 / 255.f};
    crocker::engine::Color actualColor{244 / 255.f, 154 / 255.f, 40 / 255.f};
    crocker::engine::Color thirdColor{98 / 255.f, 232 / 255.f, 115 / 255.f};
    void Render(float width, float height, float pixelRatio = 1);
    void RenderCalibration(float width, float height, float pixelRatio);
    void RenderVacuum(float width, float height, float pixelRatio, bool embedded, double minimum,
                      double maximum, int maxPoints, double pulse, double seconds);
    std::string chartTitle;
    void RenderBeam(float width, float height, float pixelRatio, double now);
    void RenderManual(float width, float height, float pixelRatio);
    void RenderGains(float width, float height, float pixelRatio);
    // CST beam-transport view uses receipt-relative time, not PID's latest-time axis.
    void RenderTransport(float width, float height, float pixelRatio);
    std::vector<double> monitorX, monitorY;
    double monitorSeconds = 120;
    std::string monitorTitle;
    std::vector<MonitorTrace> monitorTraces;
    std::array<double, 2> historyX{MissingHistoryValue, MissingHistoryValue},
        historyY{MissingHistoryValue, MissingHistoryValue};
    bool historyLog = false, historyScientific = false, historyPaper = false;
    double cursorX = MissingHistoryValue, cursorY = MissingHistoryValue;
    std::string historyLabel, cursorText;
    std::vector<HistoryMarker> historyMarkers;
    std::array<double, 4> HistoryBounds() const;
    std::array<double, 2> HistoryPoint(double x, double y, double width, double height) const;
    void ZoomHistory(double factor, double center);
    void RenderHistory(float width, float height, float pixelRatio);
    void RenderMagnetic(float width, float height, float pixelRatio, int kind);
    std::array<double, 3> gains{};
    void Release() {
        context_.Release();
    }

  private:
    void RenderStyled(float width, float height, float pixelRatio, bool calibration);
    crocker::engine::RenderContext context_;
};
} // namespace combination
