# First integrated simulation

This document describes the first controller milestone. Default startup now opens the integrated CST launcher; see [LAUNCHER_INTEGRATION.md](LAUNCHER_INTEGRATION.md) for the added navigation, monitoring/history and configuration screens. Use `--controller` to open this standalone controller milestone. Its existing placeholder subsystem tabs remain as supplied by CST; the complete monitoring windows are reached through the launcher.

## Run

From Combination, install/build once with `scripts/install.ps1` on Windows or `bash scripts/install_ubuntu.sh` on Ubuntu. Run `scripts/run.ps1` or `bash scripts/run_ubuntu.sh`. Python 3.13, CMake, a C++20 compiler and OpenGL 4.6 core are required. The installers locate the sibling RI native dependency checkout.

`python main.py --check` validates native imports without opening a window. `python main.py --simulation` explicitly selects the default mode; `--preview` opens the independent graph demo. There is no hardware/server launch option in this milestone.

Existing development builds under `build/Release` are also recognized when using the current RI Python environment. The production installer uses `Combination/.venv` and platform-specific build folders; it does not depend on RI's virtual environment.

## Reused code and necessary changes

| Responsibility | Existing source retained | Integration change |
| --- | --- | --- |
| Controller views, labels, layout and workflows | CST `MagneticFieldControllerWindow.py`, controller context/theme, manual and sequence editors, PID/GA and BO pages | PyQt6 imports become PySide6; imports become explicit packages; log/resource paths become absolute. Large inherited modules are retained to avoid changing behavior during migration. |
| Scaling, beam ranges, calibration and defaults | CST `scaling.py`, `beam_range.py`, `beam_cal.py`, `app_settings.py` and JSON | Copied values and algorithms, not RI defaults. Editable runtime configuration is seeded from those exact files without overwriting existing edits. |
| Adaptive PID math | RI `NLAPID.cpp/.hpp`, corresponding to CST's adaptive controller | Thin Python adapter reuses CST dataclasses/validation and delegates calculations to native code. Native negative-gain rejection was aligned with CST. Differential tests compare against the original CST Python implementation. |
| High-rate beam sampling and control-cycle policy | CST `pid_beam_buffer.py`, controller/PID callbacks | Existing fresh-window averaging, response waits, stale checks and baseline policy remain in CST Python orchestration. This milestone does **not** claim a fully native deterministic PID scheduling loop. |
| Simulation acquisition | RI SimulatorTransport worker/lifecycle pattern | New raw-domain `SimulationRuntime` is needed for full-rate packet buffering, CST range calibration and timed row execution. No original network server or logger process is started. |
| Timed sequence execution | CST sequence editor validation, clamping, two-decimal targets and pause semantics | Small mixin submits plans to the C++ acquisition worker. RI's general sequence policy was not reused unchanged because it forces channel power/enable, which would conflict with CST's mask-preserving behavior. |
| Graphs in this controller | CST manual trend, PID/GA trend, embedded beam plot and gain radar definitions | Native C++ preparation/drawing, with small Qt hosts. Each graph retains its own CST style; the manual plot is not silently restyled as a PID chart. |
| Telemetry persistence | CST `sqlite_logger.py` schema/packet flattening and RI `async_writer.py` | Reuse the CST `channel_data` contract with RI's bounded, ordered SQLite worker. Views do not issue telemetry inserts. CST's disabled PID-SQLite logger remains disabled; its decision logs remain supported. |

`docs/evidence/cst_migration_manifest.json` records exact CST files and hashes. Originals were read/copied, not edited. Most of the visible application is reused code; new code is concentrated at the integration boundaries.

## Runtime boundaries

```text
CST operator action
  -> CST context / calibration / command callback
  -> SimulationBridge
  -> native SimulationRuntime command state
  -> native 100 Hz first-order plant and bounded raw packet buffer
  -> background collector
       -> original CST high-rate BeamSampleBuffer
       -> RI AsyncSQLiteWriter -> CST channel_data
       -> latest display packet -> CST controller views

CST sequence editor -> native timed rows -> native command state
CST PID cycle -> native adaptive PID math -> CST output gate -> native command state
CST plot data -> Qt OpenGL host -> native chart geometry/text/drawing
```

The simulator consumes raw targets after CST's engineering-to-raw conversion and emits raw readbacks. CST performs the corresponding display calibration exactly as before. Channel order remains TC1–TC12, Main Magnet, Centering Beam. No extra RI target limits or arming defaults are overlaid.

The simple plant uses RI's first-order response and a synthetic beam relationship `2.0 + 0.002 * TC10_actual_A`, with a tiny deterministic ripple. It is a functional simulation, not an identified cyclotron model. Native code inverts the selected CST calibration to produce raw beam input. Curve endpoints saturate according to that calibration; an incompatible/noninvertible simulated calibration produces an explicit error. Other Devices uses numerical nA identity. Unsimulated source/extraction/RF/vacuum fields remain absent/NULL, rather than invented telemetry.

## Configuration and data

Defaults are in `config/`, copied from CST. First launch seeds editable files under `runtime/config/`; existing files and explicit CNL configuration environment overrides are preserved. `COMBINATION_RUNTIME_DIR` selects another runtime directory.

Telemetry is stored in `runtime/databases/cyclotron_data.db`, with CST raw fields and timestamp/range metadata. Decision logs go under `runtime/logs/pid_decisions`; tuning exports go under `runtime/exports`. Closing the application cancels producers, stops native acquisition, collects remaining packets and waits for the database writer to flush. Shutdown errors are reported and return a failing application status.

CST's existing BO executor can finish an already-running fit after stop; its model-fit cancellation and full tuning shutdown remain outside the verified scope of this first simulation milestone.

## Verified and remaining

Headless integration tests cover CST defaults, packet scaling, manual rounding/output, range confirmation, direct beam input, preview and armed simulated PID, stale-feedback stop, single/multi sequences, pause/handover, execution while Qt is stalled and database shutdown persistence. Native PID tests compare both active and legacy modes against CST. CST's BO adapter/scheduler tests are reused against migrated modules.

Real desktop testing checks actual QOpenGLWidget initialization and captures the controller in `docs/evidence/simulation_*.png`. Offscreen GL tests also render manual, PID, beam and gain styles and check resource release/recreation. Source font-atlas oversampling was corrected so small CST native labels remain legible.

Still pending: full home/monitoring/history/snapshot/calibration-editor integration; full GA/BO search/validation runs with real model fitting; moving any remaining control-cycle orchestration to native workers where required; native ports of the other monitoring graphs; hardware protocol replay and controlled hardware validation; Ubuntu execution; cross-DPI visual parity; CUDA kernels and performance profiling. Existing CST placeholder tabs remain placeholders. The main parity checklist is not marked universally complete.
