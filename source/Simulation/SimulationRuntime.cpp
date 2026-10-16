#include "Simulation/SimulationRuntime.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace combination {
using Clock = std::chrono::steady_clock;
namespace {
double Seconds(Clock::duration duration) {
    return std::chrono::duration<double>(duration).count();
}
bool KnownOwner(const std::string &mode) {
    return mode == "MANUAL" || mode == "PID" || mode == "GA TUNING" || mode == "SEQUENCE" ||
           mode == "MULTI-TC SEQUENCE";
}
} // namespace
SimulationRuntime::SimulationRuntime(double rateHz) : rateHz_(rateHz) {
    if (!std::isfinite(rateHz) || rateHz < 1 || rateHz > 1000)
        throw std::invalid_argument("Simulation rate must be between 1 and 1000 Hz");
}
SimulationRuntime::~SimulationRuntime() {
    Stop();
}
void SimulationRuntime::Start() {
    std::lock_guard lifecycle(lifecycle_);
    std::lock_guard lock(mutex_);
    if (running_)
        return;
    running_ = true;
    try {
        worker_ = std::thread(&SimulationRuntime::Run, this);
    } catch (...) {
        running_ = false;
        throw;
    }
}
void SimulationRuntime::Stop() {
    std::lock_guard lifecycle(lifecycle_);
    {
        std::lock_guard lock(mutex_);
        running_ = false;
        CancelSequence();
    }
    wake_.notify_all();
    if (worker_.joinable())
        worker_.join();
}
bool SimulationRuntime::Running() const {
    std::lock_guard lock(mutex_);
    return running_;
}
void SimulationRuntime::CancelSequence() {
    if (timed_.state == "RUNNING" || timed_.state == "PAUSED")
        timed_.state = "STOPPED";
}
void SimulationRuntime::SetMode(const std::string &mode) {
    if (!KnownOwner(mode))
        throw std::invalid_argument("Unknown CST control mode");
    std::lock_guard lock(mutex_);
    if (owner_ != mode)
        CancelSequence();
    owner_ = mode;
}
void SimulationRuntime::Send(const std::array<double, 14> &targets, const std::array<bool, 14> &on,
                             const std::array<bool, 14> &enabled, const std::string &owner) {
    for (const auto target : targets)
        if (!std::isfinite(target))
            throw std::invalid_argument("Targets must be finite");
    std::lock_guard lock(mutex_);
    if (!running_)
        throw std::runtime_error("Simulation is stopped");
    if (owner != owner_)
        throw std::runtime_error("Command owner does not match CST active mode");
    auto nextTargets = targets;
    if (timed_.state == "RUNNING" || timed_.state == "PAUSED") {
        // A GUI power/enable change must not overwrite rows the native worker
        // has already applied but the next progress refresh has not shown yet.
        for (const auto &row : timedRows_)
            for (const auto [channel, value] : row.rawTargets)
                nextTargets[channel] = targets_[channel];
    }
    targets_ = nextTargets;
    on_ = on;
    enabled_ = enabled;
}
void SimulationRuntime::ValidateCurve(std::vector<crocker::controls::ScalingPoint> &curve) {
    for (const auto p : curve)
        if (!std::isfinite(p.input) || !std::isfinite(p.output))
            throw std::invalid_argument("Calibration points must be finite");
    std::stable_sort(curve.begin(), curve.end(), [](auto a, auto b) { return a.input < b.input; });
    for (std::size_t i = 1; i < curve.size(); ++i)
        if (curve[i].input == curve[i - 1].input)
            throw std::invalid_argument(
                "Simulation calibration must be invertible with unique input points");
}
void SimulationRuntime::ConfigureBeam(int range, std::uint64_t bitmask,
                                      std::vector<crocker::controls::ScalingPoint> inverseCurve,
                                      double gain, double offset, bool direct) {
    if (range < 0 || range > 9 || !std::isfinite(gain) ||
        (!direct && inverseCurve.empty() && gain == 0) || !std::isfinite(offset))
        throw std::invalid_argument("Invalid CST beam calibration");
    ValidateCurve(inverseCurve);
    std::lock_guard lock(mutex_);
    range_ = range;
    bitmask_ = bitmask;
    beamCurve_ = std::move(inverseCurve);
    beamGain_ = gain;
    beamOffset_ = offset;
    directBeam_ = direct;
}
void SimulationRuntime::ConfigureActuator(std::vector<crocker::controls::ScalingPoint> curve,
                                          double gain, double offset) {
    if (!std::isfinite(gain) || !std::isfinite(offset))
        throw std::invalid_argument("Invalid CST actuator scaling");
    ValidateCurve(curve);
    std::lock_guard lock(mutex_);
    actuatorCurve_ = std::move(curve);
    actuatorGain_ = gain;
    actuatorOffset_ = offset;
}
double SimulationRuntime::Interpolate(const std::vector<crocker::controls::ScalingPoint> &points,
                                      double value) {
    if (value <= points.front().input)
        return points.front().output;
    if (value >= points.back().input)
        return points.back().output;
    const auto hi = std::upper_bound(points.begin(), points.end(), value,
                                     [](double x, auto p) { return x < p.input; });
    const auto lo = hi - 1;
    return lo->output + (value - lo->input) * (hi->output - lo->output) / (hi->input - lo->input);
}
void SimulationRuntime::StartSequence(std::vector<TimedTargets> rows, const std::string &owner) {
    if (owner != "SEQUENCE" && owner != "MULTI-TC SEQUENCE")
        throw std::invalid_argument("Invalid sequence owner");
    if (rows.empty())
        throw std::invalid_argument("Sequence is empty");
    for (const auto &row : rows) {
        if (!std::isfinite(row.seconds) || row.seconds < 0)
            throw std::invalid_argument("Sequence times must be finite and nonnegative");
        for (const auto [channel, value] : row.rawTargets)
            if (channel >= 14 || !std::isfinite(value))
                throw std::invalid_argument("Invalid sequence channel/target");
    }
    std::stable_sort(rows.begin(), rows.end(),
                     [](const auto &a, const auto &b) { return a.seconds < b.seconds; });
    std::lock_guard lock(mutex_);
    if (!running_ || owner_ != owner)
        throw std::runtime_error("Acquire the CST sequence mode before starting");
    timedRows_ = std::move(rows);
    sequenceStarted_ = Clock::now();
    pausedSeconds_ = 0;
    timed_ = {};
    timed_.owner = owner;
    timed_.state = "RUNNING";
    timed_.total = timedRows_.size();
}
void SimulationRuntime::PauseSequence(bool paused) {
    std::lock_guard lock(mutex_);
    if (paused && timed_.state == "RUNNING") {
        pauseStarted_ = Clock::now();
        timed_.state = "PAUSED";
    } else if (!paused && timed_.state == "PAUSED") {
        pausedSeconds_ += Seconds(Clock::now() - pauseStarted_);
        timed_.state = "RUNNING";
    }
}
void SimulationRuntime::StopSequence() {
    std::lock_guard lock(mutex_);
    CancelSequence();
}
TimedStatus SimulationRuntime::SequenceStatus() const {
    std::lock_guard lock(mutex_);
    auto result = timed_;
    result.targets = targets_;
    return result;
}
std::vector<SimulationFrame> SimulationRuntime::Drain() {
    std::lock_guard lock(mutex_);
    std::vector<SimulationFrame> result(frames_.begin(), frames_.end());
    frames_.clear();
    return result;
}
std::uint64_t SimulationRuntime::Dropped() const {
    std::lock_guard lock(mutex_);
    return dropped_;
}
void SimulationRuntime::Step(double dt, double elapsed) {
    // Caller holds mutex_; snapshots, command masks and row application are atomic.
    if (timed_.state == "RUNNING") {
        timed_.elapsed = Seconds(Clock::now() - sequenceStarted_) - pausedSeconds_;
        while (timed_.applied < timedRows_.size() &&
               timed_.elapsed >= timedRows_[timed_.applied].seconds) {
            for (const auto [channel, value] : timedRows_[timed_.applied].rawTargets)
                targets_[channel] = value;
            ++timed_.applied;
        }
        if (timed_.applied == timedRows_.size())
            timed_.state = "COMPLETED";
    }
    SimulationFrame frame;
    const double alpha = std::clamp(4 * dt, 0.0, 1.0); // RI first-order simulation response
    for (std::size_t ch = 0; ch < 14; ++ch) {
        const double requested = on_[ch] && enabled_[ch] ? targets_[ch] : 0;
        raw_[ch] += (requested - raw_[ch]) * alpha;
    }
    frame.channels = raw_;
    // CST SourceExtractionMonitoringWindow demo's nominal values/oscillations.
    // Random demo noise is omitted for reproducible simulated acceptance runs.
    const double t = elapsed;
    // Explicit display fixtures, not measured hardware characteristics.
    for (std::size_t i = 0; i < frame.vacuum.size(); ++i)
        frame.vacuum[i] = 2.0 + .1 * i + .03 * std::sin(t * .3 + i);
    frame.rfPower = 60 + .15 * std::sin(t * .2);
    frame.extraction = {1.45 + .06 * std::sin(t * .40),       7.42 + .16 * std::sin(t * .23 + .6),
                        6.91 + .15 * std::sin(t * .20 + 1.1), 14.80 + .20 * std::sin(t * .14),
                        2.14 + .05 * std::sin(t * .30 + .8),  .36 + .025 * std::sin(t * .18 + 1.5)};
    frame.source = {18.70 + .24 * std::sin(t * .17), 5.62 + .09 * std::sin(t * .21 + .3),
                    92.40 + std::sin(t * .13 + .5),  1.82 + .045 * std::sin(t * .27 + 1),
                    12.40 + .16 * std::sin(t * .11), 1260};
    frame.extractionAngles = {21.3, 20.1, 19.8, 18.9, 17.6, 16.4};
    // Exact CST beam-transport --demo plant, now produced on the native worker.
    // These are display fixtures, not calibrated or identified device models.
    constexpr std::array<double, 10> transportBase{115, 124, 132, 142, 5.2,
                                                   6.1, .40, .43, .36, .39};
    for (std::size_t i = 0; i < transportBase.size(); ++i) {
        const auto base = transportBase[i];
        frame.transport[i] =
            base + std::max(std::abs(base) * .008, .008) * std::sin(.5 * elapsed + i * .6);
    }
    const double actuator = actuatorCurve_.empty() ? actuatorGain_ * raw_[9] + actuatorOffset_
                                                   : Interpolate(actuatorCurve_, raw_[9]);
    // Deliberately simple simulation plant, not an identified hardware model.
    frame.beamNanoamps = std::max(0.0, 2.0 + 0.002 * actuator + 0.0002 * std::sin(elapsed));
    frame.beamRaw = directBeam_          ? frame.beamNanoamps
                    : beamCurve_.empty() ? (frame.beamNanoamps - beamOffset_) / beamGain_
                                         : Interpolate(beamCurve_, frame.beamNanoamps);
    frame.rangeIndex = range_;
    frame.bitmask = bitmask_;
    frame.sequence = ++sequence_;
    frame.directBeam = directBeam_;
    frame.sourceTime =
        std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
    frame.receiveTime = Seconds(Clock::now().time_since_epoch());
    if (frames_.size() >= 4096) {
        frames_.pop_front();
        ++dropped_;
    }
    frames_.push_back(frame);
}
void SimulationRuntime::Run() {
    auto previous = Clock::now(), deadline = previous;
    const auto start = previous;
    const auto period =
        std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(1 / rateHz_));
    std::unique_lock lock(mutex_);
    while (running_) {
        const auto now = Clock::now();
        Step(Seconds(now - previous), Seconds(now - start));
        previous = now;
        deadline = std::max(deadline + period, now);
        wake_.wait_until(lock, deadline, [&] { return !running_; });
    }
}
} // namespace combination
