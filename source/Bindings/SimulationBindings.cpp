#include "Simulation/SimulationRuntime.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;
using namespace combination;
using namespace crocker::controls;
namespace {
std::vector<ScalingPoint> Points(const std::vector<std::pair<double, double>> &values) {
    std::vector<ScalingPoint> result;
    for (const auto [x, y] : values)
        result.push_back({x, y});
    return result;
}
py::dict Result(const NLAPIDResult &r) {
    py::dict d;
    d["output"] = r.output;
    d["error"] = r.error;
    d["proportional"] = r.proportional;
    d["integral"] = r.integral;
    d["derivative"] = r.derivative;
    d["saturated"] = r.saturated;
    d["error_magnitude"] = r.errorMagnitude;
    d["pid_magnitude"] = r.pidMagnitude;
    d["direction"] = r.direction;
    d["error_trend"] = r.errorTrend;
    d["direction_changed"] = r.directionChanged;
    d["in_deadband"] = r.inDeadband;
    return d;
}
void ConfigurePid(NLAPID &pid, const py::dict &g, const py::dict &l, const py::dict &s) {
    pid.setGains({g["kp"].cast<double>(), g["ki"].cast<double>(), g["kd"].cast<double>()});
    pid.setLimits({l["output_max"].cast<double>(), l["integral_max"].cast<double>(),
                   l["derivative_filter_tau"].cast<double>()});
    NLAPIDSettings settings;
    settings.deadband = s["deadband"].cast<double>();
    settings.directionCheckInterval = s["direction_check_interval"].cast<double>();
    settings.initialDirection = s["initial_direction"].cast<int>();
    settings.resetIntegralInDeadband = s["reset_integral_in_deadband"].cast<bool>();
    settings.resetIntegralOnDirectionChange = s["reset_integral_on_direction_change"].cast<bool>();
    settings.directionConfirmations = s["direction_confirmations"].cast<int>();
    settings.minimumDirectionSamples = s["minimum_direction_samples"].cast<int>();
    settings.integralWindowMultiplier = s["integral_window_multiplier"].cast<double>();
    settings.maxControlDt = s["max_control_dt"].cast<double>();
    settings.integralMemorySeconds = s["integral_memory_s"].cast<double>();
    settings.directionEachUpdate = s["direction_each_update"].cast<bool>();
    pid.setSettings(settings);
}
} // namespace
PYBIND11_MODULE(CombinationBackend, m) {
    m.doc() = "Simulation-only C++ transport, CST-compatible PID and timed sequencing. No hardware "
              "connection API.";
    m.def("monotonic_seconds", [] {
        return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch())
            .count();
    });
    py::class_<NLAPID>(m, "AdaptiveDirectionPID")
        .def(py::init<>())
        .def("configure", &ConfigurePid)
        .def("reset", &NLAPID::reset, py::arg("setpoint") = py::none(),
             py::arg("measurement") = py::none(), py::arg("direction") = py::none())
        .def(
            "update",
            [](NLAPID &pid, double setpoint, double measured, double dt, bool hold) {
                return Result(pid.update(setpoint, measured, dt, hold));
            },
            py::arg("setpoint"), py::arg("measurement"), py::arg("dt"),
            py::arg("hold_integrator") = false)
        .def_property_readonly("last_result",
                               [](const NLAPID &p) { return Result(p.lastResult()); })
        .def_property_readonly("direction", &NLAPID::direction);
    py::class_<SimulationRuntime>(m, "SimulationRuntime")
        .def(py::init<double>(), py::arg("rate_hz") = 100)
        .def("start", &SimulationRuntime::Start)
        .def("stop", &SimulationRuntime::Stop, py::call_guard<py::gil_scoped_release>())
        .def_property_readonly("running", &SimulationRuntime::Running)
        .def_property_readonly("dropped_packets", &SimulationRuntime::Dropped)
        .def("set_mode", &SimulationRuntime::SetMode)
        .def("send", &SimulationRuntime::Send, py::arg("targets"), py::arg("on"),
             py::arg("enabled"), py::arg("owner") = "MANUAL")
        .def(
            "configure_beam",
            [](SimulationRuntime &r, int index, std::uint64_t mask,
               const std::vector<std::pair<double, double>> &curve, double gain, double offset,
               bool direct) { r.ConfigureBeam(index, mask, Points(curve), gain, offset, direct); },
            py::arg("index"), py::arg("bitmask"), py::arg("inverse_curve"), py::arg("gain"),
            py::arg("offset"), py::arg("direct") = false)
        .def("configure_actuator",
             [](SimulationRuntime &r, const std::vector<std::pair<double, double>> &curve,
                double gain, double offset) { r.ConfigureActuator(Points(curve), gain, offset); })
        .def("start_sequence",
             [](SimulationRuntime &r,
                const std::vector<std::pair<double, std::map<std::size_t, double>>> &rows,
                const std::string &owner) {
                 std::vector<TimedTargets> plan;
                 for (const auto &[at, targets] : rows)
                     plan.push_back({at, targets});
                 r.StartSequence(std::move(plan), owner);
             })
        .def("pause_sequence", &SimulationRuntime::PauseSequence)
        .def("stop_sequence", &SimulationRuntime::StopSequence)
        .def("sequence_status",
             [](const SimulationRuntime &r) {
                 const auto s = r.SequenceStatus();
                 py::dict d;
                 d["state"] = s.state;
                 d["owner"] = s.owner;
                 d["applied"] = s.applied;
                 d["total"] = s.total;
                 d["elapsed"] = s.elapsed;
                 d["targets"] = s.targets;
                 return d;
             })
        .def("drain", [](SimulationRuntime &r) {
            py::list frames;
            for (const auto &f : r.Drain()) {
                py::dict d;
                d["channels"] = f.channels;
                d["transport"] = f.transport;
                d["extraction"] = f.extraction;
                d["source"] = f.source;
                d["extraction_angles"] = f.extractionAngles;
                d["vacuum"] = f.vacuum;
                d["rf_power_kv"] = f.rfPower;
                d["timestamp"] = f.sourceTime;
                d["_pid_source_s"] = f.sourceTime;
                d["_native_rx_mono"] = f.receiveTime;
                d["beam_current"] = f.beamRaw;
                d["simulated_beam_nA"] = f.beamNanoamps;
                d["beam_range_idx"] = f.rangeIndex;
                d["bitmask"] = f.bitmask;
                d["sequence"] = f.sequence;
                d["simulation_direct_beam"] = f.directBeam;
                d["latency"] = 0.;
                d["ts_mode"] = "unix";
                frames.append(d);
            }
            return frames;
        });
}
