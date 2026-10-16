# Combination parity checklist

Status: the first CST controller simulation is integrated and tested with native acquisition, PID calculations, sequences and graphs. Full launcher/monitoring/history/hardware parity remains pending. Checked items below have evidence; unchecked criteria have not been silently approved.

## Completed checks and current findings

- [x] **DONE-17 — CST launcher and remaining active screens integrated in simulation.** Default startup uses CST's bubble launcher, original icons/animation and thirteen navigation routes. Portrait controller, vacuum/beam/RF, settings/calibration, range and snapshot dialogs share one backend. Ten scoped integration tests cover navigation, fan-out, settings, snapshots, query/scaling/marker behavior, native coordinates, save-failure atomicity and write flush/error reporting at shutdown. Evidence: `docs/evidence/shell_history_integration.txt`; details and source defects are in `docs/LAUNCHER_INTEGRATION.md`. This is not full UI/hardware acceptance.
- [x] **DONE-18 — native remaining charts and desktop/report smoke.** Actual desktop check opens launcher, vacuum/beam, calibration and history, initializes the additional eight chart surfaces/contexts and exports a two-page native-rendered PDF. Embedded vacuum histories are composited below CST's readouts; reports use independent native renderers. Evidence: `docs/evidence/launcher_desktop.json`, `launcher_*.png`, `native_history_report.pdf`. Full pixel/DPI and PDF format comparisons remain pending; report graphs are raster rather than Matplotlib vectors.

- [x] **DONE-16 — three monitoring screens integrated in simulation.** Reused CST magnetic, transport and source/extraction views with separate bounded backend subscriptions and C++ chart rendering. Five focused integration tests pass; actual Windows desktop smoke initializes 27 chart surfaces. Evidence: `docs/evidence/monitoring_integration.txt`, `transport_desktop.json` and monitor screenshots. Exact axis/pixel/DPI parity, vacuum/beam, launcher and history remain pending. See `docs/MONITORING_INTEGRATION.md` for the repaired missing scaling-status callback target and unresolved CST range/coil bitmask ambiguity.

- [x] **DONE-01 — source selection recorded.** CST wins all behavioral/settings/style conflicts; RI supplies backend infrastructure.
- [x] **DONE-02 — folder scaffold documented.** Physical folders created; `scripts/create_structure.py` verifies a README in every current directory, including generated build directories.
- [x] **DONE-03 — native graph implementation builds.** CMake/MSVC Release builds `combination_graphics`, `CombinationCharts`, and three native test executables.
- [x] **DONE-04 — numeric CST graph parity.** Five differential tests execute actual active CST `pid_ga_control_tab.TrendPlot` numeric methods (AST-extracted without Qt imports) against C++ filtering, rolling time, point selection, bounds, axes, missing-winner traces and tick formatting. Evidence: `docs/evidence/cst_cpp_numeric_parity.txt`.
- [x] **DONE-05 — CPU and upload regression tests.** Three CTest cases pass: native model, retained font/layout tests, mocked GL buffer storage reuse/growth/release. Evidence: `docs/evidence/native_cpu_and_mock_gl.txt`.
- [x] **DONE-06 — actual native OpenGL smoke.** GL 4.6 offscreen two/three-series rendering, zero GL errors, host point-size/line-width restoration, missing-context rejection and release/recreate pass. Evidence: `docs/evidence/native_render.json` and generated PNGs. This is one renderer, not all widget/context lifecycle parity.
- [x] **DONE-07 — CST BO baseline.** Existing CST `BO.test_bo_integration` reference suite passes 11 tests. The same suite also runs against migrated modules (DONE-15); complete model-fitting/search/validation runs remain pending.
- [x] **DONE-08 — baseline source inventory.** CST source/config hashes and copied/modified RI graphics provenance recorded in `docs/evidence/source_audit.json`. Inventory is not configuration parity.
- [x] **DONE-09 — reference test failure identified.** Existing CST PID suite fails because its test constructs `AdaptiveDirectionSettings(trend_tolerance=...)`, which current CST code does not accept. Evidence: `docs/evidence/cst_pid_reference_suite.txt`. Original files were not changed; TEST-01 remains pending.
- [x] **DONE-10 — install/launch scripts prepared.** Windows PowerShell and Ubuntu Bash installers/runners create/use a Python 3.13 virtual environment, install the chosen requirements and build the native graph module. Both script syntaxes and `main.py --check` were verified. Fresh installation and Ubuntu runtime execution remain unverified; see `scripts/README.md`.
- [x] **DONE-11 — integrated CST simulation.** Eleven integration tests cover defaults, scaling, raw command conversion, direct beam input, range readback, manual output, preview/armed simulated PID, feedback-loss stop, native sequences, an independent live database reader and shutdown persistence. Evidence: `docs/evidence/integrated_simulation.txt`.
- [x] **DONE-12 — native PID parity.** Three tests compare active/legacy native PID against original CST traces and validate error/reset handling. Evidence: `docs/evidence/native_pid_parity.txt`.
- [x] **DONE-13 — native sequence independence.** Integration tests stall Qt while C++ applies rows, check pause/resume and mode handover, preserve masks and use CST's rounded engineering targets. This is simulation evidence, not hardware timing validation.
- [x] **DONE-14 — controller graph ports and actual desktop check.** Manual, PID/GA, embedded beam and gain radar drawing execute in C++. Actual Qt/OpenGL window tests and screenshots are recorded in `docs/evidence/simulation_desktop.json` and `simulation_*.png`; cross-DPI visual parity and other monitoring graphs remain pending.
- [x] **DONE-15 — migrated BO reference behavior.** Eleven existing CST BO tests run against the migrated adapter/recovery/scheduler code. Evidence: `docs/evidence/migrated_bo_suite.txt`. Full real model fitting and complete operator workflows remain unverified.

Numeric trend and native PID parity are verified on the supplied fixtures. Full visual parity across displays and the remaining application/hardware integration are not complete. See `docs/INTEGRATED_SIMULATION.md` for the current milestone and reuse decisions.

## Binding source-selection rule

**Use Control System Tune whenever the projects conflict.** This includes beam range definitions, raw/engineering scaling, calibration coefficients, safety rules, arming, limits, defaults, control algorithms, timing, packet encoding, database field meaning and operator workflows. RecurseIntall is the implementation foundation and must be adapted to match.

- **CST**: `../Control System Tune 10_15_NewVersion/` (outer folder).
- **RI**: `../RecurseIntall/Crocker-Digitlization-GUI/CrockerGUI/`.
- **NEW**: integration code created in Combination.

CST's active code and loaded configuration are the reference. Do not assume a nested, numbered, `_working` or archived file is newer. If CST sources disagree, trace the active entry point and configuration loader; record any remaining ambiguity as pending. Do not silently select an RI alternative. Preserve CST behavior first; propose intentional behavior changes separately.

## Evidence and completion

For each item record: CST file/symbol and configuration key, reference input/state, CST result, combined result, tolerance where numerical, test/artifact location, and pass/fail. Mark an item complete only with recorded evidence. Exact equality is required for enums, bit patterns, command gating and discrete state transitions; establish numerical tolerances explicitly for conversions and graphics. No guessed safety/range/calibration values qualify as evidence.

The criteria below describe what to verify, not claims about behavior already established. For features with no RI equivalent, port CST behavior. For RI-only features, verify they leave CST behavior unchanged.

## UI and application lifecycle

- [ ] **UI-01 — shell and navigation.** CST `main_control_gui.py`, `gui_window.py`: capture the active shell, window routing, titles, default tabs and navigation. Combined `python/app/shell/` reproduces them; RI shell/theme does not replace them.
- [ ] **UI-02 — monitoring views.** CST `MagneticFieldMonitoringWindow.py`, `BeamTransportMonitoringWindow.py`, `SourceExtractionMonitoringWindow.py`, `VacuumBeamMonitoringWindow.py`, `SmallScreenMagneticBeam.py`: compare labels, channel placement, units, meters, ranges and refresh behavior using the same telemetry.
- [ ] **UI-03 — theme/assets.** CST `controller_theme.py`, `neon_style.py`, root assets and `icons/`: compare screenshots at representative window sizes, including dialogs, plots and multimedia resources.
- [ ] **UI-04 — single Qt binding.** Port CST views to PySide6 for RI compatibility; verify signals, enums, timers, dialogs, media and any web views without loading PyQt6 alongside it.
- [ ] **UI-05 — startup/close/reopen.** NEW bootstrap uses RI runtime and CST initial state; verify no duplicate ZMQ/logging/PID workers, no stale callbacks, and clean window reopen/shutdown.

## Beam ranges and packet compatibility — CST wins

- [ ] **RANGE-01 — definitions and defaults.** CST `beam_range.py`, `beam_cal.py`, `beam_cal.json`, `main_control_gui.py`: enumerate every active range index, label, full scale, default and manual/automatic selection rule. Store a reference table with exact source keys.
- [ ] **RANGE-02 — encode/decode.** CST `RangeCodec` and `build_packet_51_52`: compare every supported range through 4-bit/one-hot modes, mirror behavior and bit preservation. Adapt RI `source/Controls/Network/ZMQProtocol.cpp` to CST results.
- [ ] **RANGE-03 — bit representation.** Verify CST unsigned-mask/double reinterpretation and resulting packet bytes; do not substitute numerical conversion where CST reinterprets bits.
- [ ] **RANGE-04 — packet precedence.** Verify CST explicit range-index versus bitmask selection, invalid/missing values and fallback behavior in `BeamCalManager.select_index_for_pkt` / `RangeCodec.parse`.
- [ ] **RANGE-05 — live range transitions.** Replay packets crossing ranges; match displayed units, calibration selection and buffer invalidation/mixing policy. RI services must not reinterpret CST indices.
- [ ] **PACKET-01 — protocol contract.** CST `zmq_rep_server.py`, `zmq_field_controller_sender.py`, `beam_range.py`: capture message lengths, channel order, timestamps, control masks and request/reply behavior. Native RI transport matches these fixtures.

## Scaling and calibration — CST wins

- [ ] **SCALE-01 — authoritative configuration.** Trace CST `scaling.py` configuration loading and `calibration.json`, `beam_cal.json`, `app_settings.json`; record effective paths, defaults, keys and precedence. Combination loads the same selected values without RI default overlay.
- [ ] **SCALE-02 — raw to engineering.** Compare CST `Scaler.raw_to_eng` across every active channel, endpoints, interior points and out-of-range inputs. Include linear, curve and special conversions used by CST.
- [ ] **SCALE-03 — engineering to raw.** Compare `Scaler.eng_to_raw` and round trips, including interpolation, endpoint behavior and invalid values. Verify command targets are converted exactly once.
- [ ] **SCALE-04 — beam calibration.** CST `BeamCalManager.volts_to_nA`, curve interpolation and display-unit selection match for every range, including invalid/missing calibration behavior. RI `BeamCalibrationService.py` is adapted as necessary.
- [ ] **SCALE-05 — persisted edits.** CST `ScaleCalWindow.py`, `scale_cal_editor.py`, `SpinWheelCalWindow.py`: save/reload/restart and live reload reproduce CST behavior; stale RI configuration cannot overwrite edits.
- [ ] **SCALE-06 — workbook workflow.** Compare active CST calibration/scaling workbook import/export, channel names, coefficients and history records. RI workbook service preserves the CST contract without silent omission.

## Safety, alarms and command authority — CST wins

- [ ] **SAFE-01 — settings inventory.** Extract all active CST arming flags, channel bounds, stale limits, ramp-related settings, timeout values, alarm thresholds and enable defaults from code plus loaded JSON. Record exact source/key/value and RI counterpart.
- [ ] **SAFE-02 — output arming.** CST `MagneticFieldControllerWindow.py`, `pid_ga_control_tab.py`, `controller_context.py`: verify preview/disarmed/armed behavior and all rejection paths. RI gateway enforces the same observable rules.
- [ ] **SAFE-03 — power/enable/channel bounds.** Exercise valid/invalid actuators, OFF/disabled coils, boundary targets and nonfinite inputs. Match CST acceptance, clipping/rejection, status and stop behavior.
- [ ] **SAFE-04 — fresh feedback.** Match missing/stale/duplicate/out-of-order feedback handling, timestamp basis and recovery behavior; do not substitute RI timeout defaults.
- [ ] **SAFE-05 — mode ownership.** Manual, PID, GA, BO, single sequence and multi-sequence handovers reproduce CST stop/restore behavior. Map CST context state to RI gateway authority without duplicate command owners.
- [ ] **SAFE-06 — alarm semantics.** CST `alarm.py`, `alarm_config.json`, `AlarmSettingsDialog.py`: compare thresholds, timing, latches, activation, reset and persistence using matching traces.
- [ ] **SAFE-07 — RI-only policies.** Inventory RI `InterlockService.py` and native gateway checks against CST. Conflicting RI policy/defaults remain inactive or are adapted; do not silently introduce stricter or looser limits as parity work.
- [ ] **SAFE-08 — interruption.** Compare CST stop, abort, disconnect and error paths during active operations; verify targets, output state, messages and recovery choices follow CST.

## PID and fresh beam sampling

- [ ] **PID-01 — algorithm parity.** CST `pid_controller.py` is the reference for RI Python/native PID. Test signed/magnitude error, direction changes, deadband, rate-to-increment timing, filtering and integral behavior with identical traces. Shared Python source does not prove native parity.
- [ ] **PID-02 — source stream.** CST `pid_beam_buffer.py`: feed original packets before GUI decimation through RI acquisition; preserve source and receive timestamps and range metadata.
- [ ] **PID-03 — fresh windows.** Verify cycle marks exclude prior samples, window completeness, duplicate rejection, capacity behavior and range consistency against CST `BeamSampleBuffer`.
- [ ] **PID-04 — average then calibrate.** Match CST raw-voltage averaging followed by range-specific calibration; do not replace with average-of-calibrated-values unless CST does so.
- [ ] **PID-05 — cycle timing.** CST `pid_ga_control_tab.py`: match loop, beam-average and response-wait settings, including edits during operation. A callback timestamp is not a hardware acknowledgment.
- [ ] **PID-06 — baseline.** Match manual capture, sustained-deadband automatic refresh, reset conditions and restoration from CST.
- [ ] **PID-07 — displays.** Match raw/averaged traces, exact decision average, signed error, magnitude, P/I/D terms, direction, proposed/current target and status.
- [ ] **PID-08 — diagnostics.** CST `pid_decision_log.py`: preserve event names, fields, timestamps, decision ordering and export output using RI async persistence. Record any schema additions.

## GA and Bayesian optimization

- [ ] **GA-01 — candidates.** CST `ga_pid_tuner.py` versus RI `october_ga.py`: match bounds, validation, candidate ordering under a fixed random seed and stopping behavior.
- [ ] **GA-02 — scoring.** CST `ga_test_runner.py`: compare phase progression, warm-up, sample acceptance, score terms/weights, invalid trials and result fields against RI evaluator.
- [ ] **GA-03 — recovery.** CST `ga_recovery_manager.py` plus CST page callbacks: compare reference capture, command progression, tolerances, abort/restore and timeout behavior. Preserve page policies beyond the shared algorithm.
- [ ] **GA-04 — orchestration.** CST `pid_ga_control_tab.py`: reproduce sequential trials, progress/history, control ownership and final output/gain states using RI execution.
- [ ] **BO-01 — search lifecycle.** CST `BO/bo_control_tab.py`, `bo_pid_adapter.py`: preserve starting-gain measurement, initial proposals, budget, invalid-trial handling and missing-dependency behavior, reusing RI optimizer internals.
- [ ] **BO-02 — recovery gate.** CST `BO/bo_trial_runner.py`: match measured beam/TC tolerances, continuous stable hold and timeout using boundary-value traces.
- [ ] **BO-03 — validation/apply.** Match minimum scoring duration, score acceptance heuristic, settings-change invalidation, explicit apply and final disarm/gain restoration behavior. CST active code supplies exact values.
- [ ] **BO-04 — workers and records.** Match CST stop/cancel behavior and per-trial/settings/summary output while using one optimizer worker and RI persistence.

## Manual control and sequences

- [ ] **CTRL-01 — manual actions.** CST `manual_control_tab.py`, `controller_context.py`: compare edits, selected/all channel actions, power/enable masks, scaling and command payloads through RI gateway.
- [ ] **SEQ-01 — single channel.** CST `sequence_control_tab.py`: verify row validation, time origin, target progression, pause/resume, stop and mode changes against RI sequencer.
- [ ] **SEQ-02 — multiple channels.** CST `multi_tc_sequence_tab.py`: verify synchronized rows, unchanged-channel handling, current-value loading and simultaneous commands. Extend RI sequencer if needed.
- [ ] **SEQ-03 — persistence/recall.** Compare any active CST sequence save/load or snapshot interactions; retain CST field semantics and validation.

## Database, snapshots and exports

- [ ] **DATA-01 — contract mapping.** CST `sqlite_logger.py`, `pid_sqlite_logger.py`, viewer queries: enumerate active tables, columns, channel order, units and timestamp formats. RI internal schema must support lossless CST results/compatibility views.
- [ ] **DATA-02 — acquisition records.** Replay a deterministic stream; compare stored values, sample inclusion/order and timestamps with CST. Document intentional storage-internal differences without changing observable meaning.
- [ ] **DATA-03 — history queries.** CST `sqlite_viewer_qt.py`, `sqlite_viewer_scaling.py`: compare filtering, time windows, scaling, sorting and empty-data behavior through background RI readers.
- [ ] **DATA-04 — snapshot save/recall.** CST `snapshot_save_qt.py`, `snapshot_recall_qt.py`: preserve selected fields, file formats, overwrite handling and recall commands, including power/enable behavior.
- [ ] **DATA-05 — reports/exports.** CST `sqlite_viewer_report.py` and active export callbacks: compare headers, units, precision, timestamps, plots and filenames against representative output.
- [ ] **DATA-06 — async robustness.** RI writer/reader ownership remains intact; verify bounded queues, error/status visibility, critical-record behavior and shutdown flush with CST-required fields preserved. No UI SQL or duplicate logger process.
- [ ] **DATA-07 — migration.** Import representative CST databases/workbooks into a separate destination; compare row counts and values, retain originals and record incompatible records explicitly.

## Native rendering, acceleration and final acceptance

- [ ] **NATIVE-01 — chart parity.** All selected graphs use CST appearance with C++ preparation/rendering. Numeric trend parity is verified (DONE-04); compare remaining fonts/antialiasing, graph types, interactions and resize/history cases before marking this full criterion complete.
- [ ] **NATIVE-02 — context ownership.** Verify rendering, window reopen and resource cleanup on the owning Qt thread without changing CST UI behavior.
- [ ] **CUDA-01 — optional acceleration.** Current RI CUDA is a placeholder. Any future kernel must match CST/reference CPU numerical results within recorded tolerances, preserve ordering/units and support CPU-only startup.
- [ ] **EXTRA-01 — RI additions.** Inventory hybrid/cruise automation, hardware profiles, monitor assignment and performance panels; confirm retained additions do not override CST settings or alter established workflows.
- [ ] **TEST-01 — existing suites.** Run/adapt CST `test_pid_modules.py`, `BO/test_bo_integration.py` and relevant RI native/Python tests; record results and any conflicting RI assertions updated to CST expectations.
- [ ] **TEST-02 — end-to-end parity.** Run identical simulated telemetry/operator actions through CST and Combination; compare displays, commands, state transitions, records and exports.
- [ ] **TEST-03 — unresolved items.** Review all failures and ambiguities; no conflict may be marked resolved by choosing RI behavior over CST. Keep evidence-backed pending items visible before claiming parity.

## Conflict and evidence register

Create one row per actual discrepancy during implementation. No actual conflicts have been resolved by this document alone.

| Checklist ID | CST file/symbol/config key | CST behavior/value | RI behavior/value | Required adaptation (CST wins) | Evidence/test path | Status |
| --- | --- | --- | --- | --- | --- | --- |
| — | Pending implementation comparison | — | — | — | — | Unverified |
| UI-02 / SCALE-05 | CST `MagneticFieldMonitoringWindow` calibration callbacks | Reference a `scaling_status` label absent from active layout | — | Create a hidden callback target; keep visible CST layout and scaling unchanged | `docs/MONITORING_INTEGRATION.md`, monitoring tests | Repaired in migrated view |
| RANGE-02 / SAFE-03 | CST `RangeCodec` versus magnetic monitor bit interpretation | Range nibbles occupy bits 0..7; magnetic ON display also consumes bits 0..13 | No RI fallback selected | Preserve CST interpretation pending authoritative packet fixtures; do not claim simulated display establishes physical power state | `docs/MONITORING_INTEGRATION.md` | Unresolved CST ambiguity |
