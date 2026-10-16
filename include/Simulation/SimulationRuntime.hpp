#pragma once
#include "Controls/ControlTypes.hpp"
#include <condition_variable>
#include <deque>
#include <map>
#include <mutex>
#include <thread>

namespace combination {
// Simulation-only raw-packet boundary. Worker/lifecycle design derives from RI
// SimulatorTransport; payload semantics and control ownership follow CST.
struct SimulationFrame {
    std::array<double, 14> channels{};
    std::array<double, 10> transport{};
    std::array<double, 6> extraction{}, source{}, extractionAngles{};
    std::array<double, 5> vacuum{};
    double rfPower = 0;
    double sourceTime = 0, receiveTime = 0, beamRaw = 0, beamNanoamps = 0;
    int rangeIndex = 0;
    bool directBeam = false;
    std::uint64_t sequence = 0, bitmask = 0;
};
struct TimedTargets {
    double seconds;
    std::map<std::size_t, double> rawTargets;
};
struct TimedStatus {
    std::string state = "IDLE", owner = "MANUAL";
    std::size_t applied = 0, total = 0;
    double elapsed = 0;
    std::array<double, 14> targets{};
};
class SimulationRuntime {
  public:
    explicit SimulationRuntime(double rateHz = 100);
    ~SimulationRuntime();
    SimulationRuntime(const SimulationRuntime &) = delete;
    SimulationRuntime &operator=(const SimulationRuntime &) = delete;
    void Start();
    void Stop();
    bool Running() const;
    void SetMode(const std::string &mode);
    void Send(const std::array<double, 14> &targets, const std::array<bool, 14> &on,
              const std::array<bool, 14> &enabled, const std::string &owner);
    void ConfigureBeam(int range, std::uint64_t bitmask,
                       std::vector<crocker::controls::ScalingPoint> inverseCurve, double gain,
                       double offset, bool direct);
    void ConfigureActuator(std::vector<crocker::controls::ScalingPoint> curve, double gain,
                           double offset);
    void StartSequence(std::vector<TimedTargets> rows, const std::string &owner);
    void PauseSequence(bool paused);
    void StopSequence();
    TimedStatus SequenceStatus() const;
    std::vector<SimulationFrame> Drain();
    std::uint64_t Dropped() const;

  private:
    void Run();
    void Step(double dt, double elapsed);
    void CancelSequence(); // caller holds mutex_
    static double Interpolate(const std::vector<crocker::controls::ScalingPoint> &points,
                              double value);
    static void ValidateCurve(std::vector<crocker::controls::ScalingPoint> &curve);
    const double rateHz_;
    mutable std::mutex mutex_;
    std::mutex lifecycle_;
    std::condition_variable wake_;
    std::thread worker_;
    bool running_ = false;
    std::array<double, 14> raw_{}, targets_{};
    std::array<bool, 14> on_{}, enabled_{};
    std::string owner_ = "MANUAL";
    std::deque<SimulationFrame> frames_;
    std::uint64_t sequence_ = 0, dropped_ = 0;
    int range_ = 0;
    std::uint64_t bitmask_ = 0;
    std::vector<crocker::controls::ScalingPoint> beamCurve_, actuatorCurve_;
    double beamGain_ = 1, beamOffset_ = 0, actuatorGain_ = 1, actuatorOffset_ = 0;
    bool directBeam_ = false;
    std::vector<TimedTargets> timedRows_;
    TimedStatus timed_;
    std::chrono::steady_clock::time_point sequenceStarted_, pauseStarted_;
    double pausedSeconds_ = 0;
};
} // namespace combination
