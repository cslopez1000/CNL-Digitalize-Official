#include "Engine/Visualization/Charts/CstTrendPlot.hpp"
#include <glad/glad.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
using namespace combination;
using crocker::engine::RenderContext;
namespace {
thread_local const py::function *loader = nullptr;
void *Load(const char *name) {
    const auto result = (*loader)(name);
    return result.is_none() ? nullptr : reinterpret_cast<void *>(result.cast<std::uintptr_t>());
}
void SetData(CstTrendModel &model, const std::vector<double> &x, const std::vector<double> &target,
             const std::vector<double> &actual, py::object third) {
    if (third.is_none())
        model.SetData(x, target, actual);
    else {
        const auto values = third.cast<std::vector<double>>();
        model.SetData(x, target, actual, &values);
    }
}
} // namespace
PYBIND11_MODULE(CombinationCharts, m) {
    m.def("set_render_viewport", [](int width, int height) { glViewport(0, 0, width, height); });
    m.def("clear_transparent_frame", [] {
        GLfloat color[4];
        glGetFloatv(GL_COLOR_CLEAR_VALUE, color);
        glClearColor(0, 0, 0, 0);
        glClear(GL_COLOR_BUFFER_BIT);
        glClearColor(color[0], color[1], color[2], color[3]);
    });
    m.def("font_diagnostics", [] {
        crocker::engine::FontManager fonts;
        const auto id = fonts.Load();
        const auto &face = fonts.Face(id);
        crocker::engine::TextStyle style;
        style.font = id;
        style.size = 10.666667f;
        const auto run = crocker::engine::TextLayout(fonts).Layout("1.00", style);
        py::dict report;
        report["path"] = face.path;
        report["baked_em_size"] = face.bakeSize;
        report["tick_width"] = run.advance;
        report["atlas_width"] = face.atlasWidth;
        report["atlas_height"] = face.atlasHeight;
        return report;
    });
    m.def("set_current_render_context", &RenderContext::SetCurrentContext);
    m.def("load_opengl", [](const py::function &callback) {
        loader = &callback;
        try {
            RenderContext::LoadOpenGL(&Load);
        } catch (...) {
            loader = nullptr;
            throw;
        }
        loader = nullptr;
    });
    py::class_<crocker::engine::Color>(m, "Color")
        .def(py::init<float, float, float>())
        .def_readwrite("r", &crocker::engine::Color::r)
        .def_readwrite("g", &crocker::engine::Color::g)
        .def_readwrite("b", &crocker::engine::Color::b);
    py::class_<Axis>(m, "Axis")
        .def_readonly("minimum", &Axis::minimum)
        .def_readonly("maximum", &Axis::maximum)
        .def_readonly("step", &Axis::step);
    py::class_<CstTrendModel>(m, "CstTrendModel")
        .def(py::init<>())
        .def_readwrite("x_label", &CstTrendModel::xLabel)
        .def_readwrite("y_label", &CstTrendModel::yLabel)
        .def_readwrite("relative_time", &CstTrendModel::relativeTime)
        .def_readwrite("rolling_window", &CstTrendModel::rollingWindow)
        .def_readwrite("allow_missing_target", &CstTrendModel::allowMissingTarget)
        .def_readwrite("max_points", &CstTrendModel::maxPoints)
        .def_readwrite("x_ticks", &CstTrendModel::xTicks)
        .def_readwrite("y_ticks", &CstTrendModel::yTicks)
        .def_readonly("rows", &CstTrendModel::rows)
        .def_readonly("has_third", &CstTrendModel::hasThird)
        .def("set_data", &SetData, py::arg("x"), py::arg("target"), py::arg("actual"),
             py::arg("third") = py::none())
        .def("raw_bounds", &CstTrendModel::RawBounds)
        .def("x_axis", &CstTrendModel::XAxis)
        .def("y_axis", &CstTrendModel::YAxis)
        .def_static("nice_axis", &CstTrendModel::NiceAxis)
        .def_static("ticks", &CstTrendModel::Ticks)
        .def_static("format_tick", &CstTrendModel::FormatTick);
    py::class_<CstTrendPlot>(m, "CstTrendPlot")
        .def(py::init<>())
        .def_readwrite("model", &CstTrendPlot::model)
        .def_readwrite("target_color", &CstTrendPlot::targetColor)
        .def_readwrite("actual_color", &CstTrendPlot::actualColor)
        .def_readwrite("third_color", &CstTrendPlot::thirdColor)
        .def("render", &CstTrendPlot::Render, py::arg("width"), py::arg("height"),
             py::arg("pixel_ratio") = 1.f)
        .def("render_beam", &CstTrendPlot::RenderBeam)
        .def("render_manual", &CstTrendPlot::RenderManual)
        .def("render_calibration", &CstTrendPlot::RenderCalibration)
        .def("render_vacuum", &CstTrendPlot::RenderVacuum)
        .def("set_vacuum_data",
             [](CstTrendPlot &plot, const std::vector<double> &values) { plot.monitorY = values; })
        .def("render_history", &CstTrendPlot::RenderHistory)
        .def("history_bounds", &CstTrendPlot::HistoryBounds)
        .def("history_point", &CstTrendPlot::HistoryPoint)
        .def("zoom_history", &CstTrendPlot::ZoomHistory)
        .def_readwrite("history_x", &CstTrendPlot::historyX)
        .def_readwrite("history_y", &CstTrendPlot::historyY)
        .def_readwrite("history_log", &CstTrendPlot::historyLog)
        .def_readwrite("history_scientific", &CstTrendPlot::historyScientific)
        .def_readwrite("history_paper", &CstTrendPlot::historyPaper)
        .def_readwrite("history_label", &CstTrendPlot::historyLabel)
        .def_readwrite("cursor_x", &CstTrendPlot::cursorX)
        .def_readwrite("cursor_y", &CstTrendPlot::cursorY)
        .def_readwrite("cursor_text", &CstTrendPlot::cursorText)
        .def("clear_monitor_series", [](CstTrendPlot &plot) { plot.monitorTraces.clear(); })
        .def("set_history_markers",
             [](CstTrendPlot &plot, const std::vector<double> &x,
                const std::vector<std::string> &labels,
                const std::vector<crocker::engine::Color> &colors) {
                 if (x.size() != labels.size() || x.size() != colors.size())
                     throw std::invalid_argument("Marker arrays must align");
                 plot.historyMarkers.clear();
                 for (std::size_t i = 0; i < x.size(); ++i)
                     plot.historyMarkers.push_back({x[i], labels[i], colors[i]});
             })
        .def_readwrite("chart_title", &CstTrendPlot::chartTitle)
        .def("render_gains", &CstTrendPlot::RenderGains)
        .def("render_transport", &CstTrendPlot::RenderTransport)
        .def("render_magnetic", &CstTrendPlot::RenderMagnetic)
        .def("set_monitor_series",
             [](CstTrendPlot &plot, std::size_t index, const std::vector<double> &x,
                const std::vector<double> &y, crocker::engine::Color color,
                const std::string &name) {
                 if (index >= 64 || x.size() != y.size())
                     throw std::invalid_argument(
                         "Invalid monitor series index or unequal coordinates");
                 if (plot.monitorTraces.size() <= index)
                     plot.monitorTraces.resize(index + 1);
                 plot.monitorTraces[index] = {x, y, color, name};
             })
        .def_readwrite("monitor_seconds", &CstTrendPlot::monitorSeconds)
        .def_readwrite("monitor_title", &CstTrendPlot::monitorTitle)
        .def("set_monitor_data",
             [](CstTrendPlot &plot, const std::vector<double> &x, const std::vector<double> &y) {
                 if (x.size() != y.size())
                     throw std::invalid_argument("Monitoring coordinates must have equal lengths");
                 plot.monitorX = x;
                 plot.monitorY = y;
             })
        .def_readwrite("gains", &CstTrendPlot::gains)
        .def("release_resources", &CstTrendPlot::Release);
}
