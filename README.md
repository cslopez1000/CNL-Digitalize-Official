# Combination: CST frontend with a RecurseIntall backend

## Current status — 2026-10-16

**The CST launcher and its screens are integrated in simulation. Hardware integration is not complete.** Default startup now opens CST's original bubble launcher, with its controller wrapper, all four monitoring screens, history, settings, calibration, beam-range and snapshot navigation connected to one shared backend. The directory tree and migration tables later in this README still describe the broader target architecture; folders do not imply complete hardware or behavioral parity. Both original source trees remain unchanged.

Run `scripts/run.ps1` on Windows or `bash scripts/run_ubuntu.sh` on Ubuntu to open the CST launcher. Use `--controller` for the previous standalone controller entry point. The GUI is simulation-only; there is no hardware connection option. Ubuntu runtime remains untested.

Explicit Windows launch flags are `scripts/run.ps1 -Simulation` and `-ZMQ`.
`-ZMQ` currently exits with an unavailable-backend error; it does not connect to
hardware or fall back to simulation. See [remaining features and BO setup](docs/REMAINING_FEATURES.md)
for the missing work, optional BO dependencies and where to find the BO page.

Optional `--magnetic --transport --source` switches pre-open those monitors. Launcher navigation preserves CST's display averaging and independent fan-out queues; PID sampling and SQLite recording remain full rate. See [launcher integration](docs/LAUNCHER_INTEGRATION.md) for file origins, repaired source defects, testing and remaining acceptance work.

### Implemented and verified within the simulation

- Reused CST controller, manual/PID/GA/BO/sequence views, with PySide6 integration and CST configuration defaults.
- C++ simulated acquisition, adaptive PID calculations and timed single/multi-channel sequence execution. PID workflow scheduling still uses CST's Python/Qt orchestration.
- C++/OpenGL drawing for controller manual trends, PID/GA trends, the embedded beam chart and gain radar; selected RI rendering defects corrected.
- Full-rate beam buffering before display decimation, CST scaling/range handling for the tested controller paths, and asynchronous SQLite recording using the reused RI writer and CST schema.
- Windows PowerShell and Ubuntu Bash installation/run scripts, provenance records, folder documentation and a parity checklist.
- CST launcher/icons/animation, portrait controller navigation, vacuum/beam/RF screen, three-pane history viewer, settings/calibration editors and snapshot dialogs.
- C++ drawing for live histories, logarithmic embedded histories, calibration curves, and history graphs with native bounds, zoom and mouse mapping. PDF charts are rendered offscreen in C++ and placed in reports by Qt; exported charts are raster images rather than CST's original Matplotlib vectors.
- Worker-owned historical SQLite reads, asynchronous snapshot workbook reads/writes, and atomic snapshot saves. CST's existing schema, calibration, workbook format and TC-only recall selection are reused.
- Recorded checks include 11 simulation integration tests, 3 native PID parity tests, 11 migrated BO reference tests, 3 native CTest cases, numeric graph comparisons and an actual Windows Qt/OpenGL controller smoke test. These establish the tested milestone, not full application parity.

### Remaining implementation and acceptance work

| Order | Work remaining | Completion requirement |
| --- | --- | --- |
| 1 | Full UI acceptance | Navigation and screens are wired and smoke-tested. Finish repeated close/reopen, mixed-window stress, long-running control handover and complete visual comparison at representative screen sizes. |
| 2 | Protocol ambiguities | Resolve CST's overlapping range/coil-status bits and differing launcher/controller range-follow interpretations against authoritative hardware packet fixtures. No RI defaults were substituted. |
| 3 | Rendering acceptance | Finish differential tick/auto-padding, clipping, marker-label layout and cross-DPI comparisons. Gauges retain CST's Qt-painted UI; their embedded history graphs render in C++. Profile GPU throughput. |
| 4 | Data/configuration acceptance | Broaden historical database/workbook migration, PDF layout/format comparisons, edit/restart/live-reload coverage and error/queue-pressure tests. Existing CST source/extraction/transport snapshot apply actions remain unwired, as in CST; TC-only magnetic recall is integrated. |
| 5 | Alarm acceptance | CST settings and activation toggle are connected; the original source does not wire alarm-rule feeding/annunciation into the launcher. Complete that operator workflow separately before claiming operational alarms. |
| 6 | Complete tuning workflows | Validate full GA and BO searches, model fitting, cancellation, recovery, validation/apply and saved results. Reused views and passing reference tests do not establish complete operator workflows. |
| 7 | Hardware backend | Adapt RI transport/gateway services to CST packet semantics and command authority; validate protocol replay, range acknowledgments, stale/disconnected feedback and reconnect. The current entry point exposes simulation only. |
| 8 | Performance and optional CUDA | Profile real workloads, address measured OpenGL/queue bottlenecks, and implement useful CUDA acceleration with numerical parity and a CPU fallback. CUDA is not implemented. |
| 9 | Final verification and packaging | Complete end-to-end CST parity, queue/error/shutdown tests, cross-DPI visual checks, fresh Windows installation and actual Ubuntu build/run; resolve or document remaining reference-suite failures. |

**Known verification limits:** the original CST PID suite fails on an obsolete `trend_tolerance` constructor argument; this is recorded, not marked passing. Full hardware operation, complete tuning runs, clean installation and Ubuntu runtime remain unverified. See [the parity checklist](PARITY_CHECKLIST.md), [implementation status](docs/IMPLEMENTATION_STATUS.md) and [simulation guide](docs/INTEGRATED_SIMULATION.md) for evidence and scope.

**Rules for resuming:** CST remains authoritative for UI, settings, ranges, scaling, safety and observable behavior. Reuse existing CST/RI code wherever suitable; adapt conflicting RI behavior to CST. Keep graph preparation/rendering in C++ and record each migrated file's origin. Mark checklist items complete only after verification.

The broader backend migration, hardware validation, CUDA and full parity certification remain unfinished.

Install/run scripts are in [scripts/README.md](scripts/README.md). Windows: `scripts/install.ps1`, then `scripts/run.ps1`. Ubuntu: `bash scripts/install_ubuntu.sh`, then `bash scripts/run_ubuntu.sh`. `main.py` launches CST's launcher by default; `--controller` opens the standalone controller and `--preview` retains the independent native chart demo.

## Mandatory conflict policy

**Control System Tune wins every conflict.** The reference is the outer `Control System Tune 10_15_NewVersion/` project. Its UI, workflows, algorithms, beam ranges, packet semantics, safety settings, limits, scaling/calibration, defaults, saved configuration and data/export behavior take precedence over conflicting RecurseIntall behavior. Adapt the RecurseIntall backend to implement those requirements. Do not blend defaults, choose a stricter/looser RI value, or substitute an RI policy silently. A proposed correction to CST behavior must be recorded separately rather than introduced as a parity change.

RecurseIntall supplies C++/OpenGL and optional CUDA infrastructure, transport execution, threading and asynchronous storage. RI-only capabilities may be retained when they do not change CST behavior; keep conflicting additions inactive. CST runtime behavior and loaded configuration take precedence over older documentation or copied/archive variants. Unresolved ambiguity within CST must be marked pending rather than resolved by falling back to RI.

See [PARITY_CHECKLIST.md](PARITY_CHECKLIST.md) for evidence-backed completed checks and pending integration criteria, and [docs/GRAPHICS_IMPLEMENTATION.md](docs/GRAPHICS_IMPLEMENTATION.md) for implemented rendering work and build commands.

## Recommended combination

**UI source: Control System Tune. Backend foundation: RecurseInstall (the actual folder on disk is spelled `RecurseIntall`).** Preserve Control System Tune's updated workflows as well as its appearance. Replace its backend execution/infrastructure with RecurseIntall, porting feature logic where the selected backend does not yet implement equivalent behavior.

Use `RecurseIntall/Crocker-Digitlization-GUI/CrockerGUI` as the backend foundation. Preserve its `source/`, `include/`, and `source/Python/` organization, C++20 engine, OpenGL renderer, CycloViz pybind11 extension, control gateway, transport workers, and asynchronous database pipeline.

Use the outer `Control System Tune 10_15_NewVersion` project as the visual UI source: its main window, monitoring windows, controller tabs, dialogs, themes, icons, and backgrounds. Treat the nested `Control System Tune 2_23_NewVersion` and numbered/working copies as reference variants until their differences are reviewed.

Keep one application entry point and one backend owner. UI modules display snapshots and submit commands through adapters; backend modules own acquisition, control execution, processing, and persistence.

## Proposed tree

The tree below is the target layout, not a list of files already implemented. Existing backend module names are retained; adapter, application, build-helper, and test directories describe proposed additions.

```text
Combination/
|-- README.md
|-- main.py                         # composition root: configure, start, stop
|-- CMakeLists.txt                  # preserve backend targets; update paths
|-- CMakePresets.json               # proposed CPU/CUDA build presets
|-- requirements.txt               # reconcile dependencies; one Qt binding
|-- .gitignore
|
|-- source/                        # backend structure from RecurseIntall
|   |-- Bindings/                  # CycloViz pybind11 bindings
|   |-- Controls/
|   |   |-- ControlSystem/         # NLAPID and native control algorithms
|   |   |-- Network/               # ZMQProtocol, receiver, sender, server
|   |   |-- Transport/             # ServerTransport, SimulatorTransport
|   |   |-- Service/               # ControlService, CommandGateway
|   |   `-- Sequencer/             # validation, sequencing, runner
|   |-- Engine/
|   |   |-- Core/
|   |   |-- Graphics/              # RenderContext, Canvas2D, OpenGL/
|   |   |-- Text/
|   |   `-- Visualization/         # Charts/, Gauges/, Plots/
|   |-- Simulation/                # CyclotronModel
|   |-- Cuda/                      # optional acceleration; currently placeholder
|   `-- Python/
|       |-- Data/                  # preserve existing persistence modules
|       |   |-- async_writer.py
|       |   |-- telemetry_database.py
|       |   |-- pid_database.py
|       |   |-- pipeline_manager.py
|       |   |-- pipeline_schema.py
|       |   |-- data_logger.py
|       |   |-- data_processor.py
|       |   `-- file_writer.py
|       |-- Services/              # alarms, calibration, signal map, interlocks
|       |-- Control/               # Python control and C++ adapters
|       |-- Automation/
|       |-- Optimization/
|       |-- PID_Tuner/
|       |-- AI/
|       |-- DataExploration/
|       `-- Simulator/
|
|-- include/                       # preserve matching native public headers
|   |-- Controls/
|   |-- Engine/
|   `-- Simulation/
|
|-- python/
|   |-- application/               # new lifecycle and dependency wiring
|   |   |-- bootstrap.py
|   |   |-- runtime.py
|   |   `-- paths.py               # absolute asset/config/database paths
|   |-- adapters/                  # new boundary between UI and backend
|   |   |-- telemetry_adapter.py   # snapshots -> named display models
|   |   |-- command_adapter.py     # UI intent -> existing CommandGateway
|   |   |-- database_adapter.py    # asynchronous query/export requests
|   |   `-- plot_adapter.py        # display arrays and native plot lifecycle
|   `-- app/                       # UI from Control System Tune
|       |-- shell/                 # main_control_gui.py, gui_window.py
|       |-- monitoring/            # magnetic, beam transport, source, vacuum
|       |-- controls/              # manual, PID, GA and sequence views
|       |-- configuration/         # settings, scaling, alarms, calibration
|       |-- history/               # database viewer, snapshot save/recall
|       |-- widgets/               # shared meters, buttons, plot widgets
|       `-- theme/                 # controller_theme.py, neon_style.py
|
|-- assets/
|   |-- ui/                        # UI icons, backgrounds, video, static JS
|   `-- engine/                    # backend shaders, fonts, render resources
|-- config/                        # defaults; no live records or credentials
|-- external/                      # backend dependency layout/submodules
|-- cmake/                         # optional CUDA detection/build helpers
|-- scripts/                       # build, simulation launch, data migration
|-- tests/
|   |-- native/                    # retained C++ backend tests
|   |-- python/                    # retained backend tests
|   `-- integration/               # adapters, shutdown, schema, UI smoke
|-- docs/                          # contracts, migration notes, build guide
|-- runtime/                       # generated; ignored by version control
|   |-- databases/
|   |-- logs/
|   |-- snapshots/
|   `-- exports/
`-- build/                         # generated native output; ignored
```

Preserve actual source subtrees during migration even when omitted from this abbreviated tree. Do not create empty packages or split every widget into a new file merely to match a diagram. Keep this shallow layout and add files when needed.

## Ownership and migration mapping

| Existing source | Combined location | Treatment |
| --- | --- | --- |
| RecurseIntall `source/`, `include/` | Same relative paths | Backend infrastructure; retain organization while adapting any conflicting behavior to CST. |
| RecurseIntall `external/`, config and engine assets | `external/`, `config/`, `assets/engine/` | Preserve dependency revisions and update explicit resource paths. |
| RecurseIntall `source/Bindings/` | Same path | Retain CycloViz module name and binding contracts. |
| UI `main_control_gui.py`, `gui_window.py` | `python/app/shell/` | Preserve appearance; consolidate overlapping launch responsibilities. |
| UI monitoring window files | `python/app/monitoring/` | Preserve layouts and interactions; replace acquisition/storage calls with adapters. |
| UI manual/PID/GA/sequence tabs | `python/app/controls/` | Preserve view behavior; route control actions through backend services. |
| UI settings, alarm, scaling, calibration dialogs | `python/app/configuration/` | Views use existing backend services through adapters. |
| UI SQLite viewer and snapshot dialogs | `python/app/history/` | Preserve screens; adapt queries to backend schema and move I/O off UI thread. |
| UI images, icons, video, static JavaScript | `assets/ui/` | Copy only assets referenced by the selected UI. |
| UI `sqlite_logger.py`, `pid_sqlite_logger.py`, ZMQ server/sender and controller implementations | Backend adapters and feature ports | Replace infrastructure ownership with RecurseIntall services; preserve required packet semantics, recorded fields and updated controller behavior. Compare before retiring code. |
| UI DB/XLSX records and logs | Explicit import/export into `runtime/` | Review schema and units; do not copy live DB/WAL/SHM files as application assets. |

## Runtime and threading model

```text
LabVIEW / simulator <-> native ZMQ transport <-> ControlService / CommandGateway
                                                  |
                                             snapshots
                                                  |
                                adapters -> Qt views / OpenGL charts
                                                  |
                              DataPipelineManager publishes snapshots
                                                  |
                              bounded AsyncSQLiteWriter mailbox
                                                  |
                                     telemetry SQLite database
                                                  |
                                   independent read/processor worker
                                                  |
                               processed metrics -> writer mailbox
```

- Retain the backend transport and control worker ownership. Do not start the UI project's old multiprocessing ZMQ server and logger alongside them.
- Preserve `DataPipelineManager` publication on the Qt thread, `AsyncSQLiteWriter` SQL execution on its writer thread, and the telemetry database's independent read/processor thread. PID persistence continues through the existing PID database abstraction.
- A database connection belongs to its worker. All writes for a given database pass through its designated writer; readers use independent connections. Keep the existing queue capacity, critical-event reservation, and status/error reporting, then verify saturation and shutdown behavior.
- Historical queries and exports run in workers and deliver results using queued Qt signals. UI refresh uses snapshots; it does not wait for disk writes or query completion.
- Keep OpenGL context creation, painting, and destruction on the owning Qt render thread. Workers prepare arrays; they do not update Qt widgets or use a context owned by another thread.
- CUDA receives batches of numeric data and returns arrays/metrics through an explicit worker boundary. It does not own widgets, hardware commands, or SQLite connections. Preserve a CPU path.
- Shutdown stops publication and new commands, stops acquisition/processing workers, flushes and closes writers, joins workers, and releases render resources on the owning thread. Verify the current backend stop methods before claiming this ordering is guaranteed.

## Qt and plotting decision

The selected UI imports PyQt6; the backend Python layer imports PySide6. Standardize on **PySide6**, porting UI imports, signals/slots, enum/API differences, multimedia and any web widgets while preserving the selected UI's visual design. Do not load both bindings in the same application process.

**Graph appearance and semantics come from CST; graph preparation and drawing run in C++.** Python owns the Qt host, UI controls and data handoff. Do not ship CST's Python/QPainter/JavaScript graph drawing as the final backend. Port each selected graph to native code while preserving CST axes, colors, units, ticks, overlays and interaction. The first implemented port is `CstTrendPlot`, based on active CST `pid_ga_control_tab.py::TrendPlot`; other graph/meter types remain pending. Reuse RI context lifecycle infrastructure, not its conflicting chart styles or smoothing defaults.

## Build and data decisions

Retain the existing `crocker_engine` and `CycloViz` CMake targets and the documented Python 3.13 baseline initially. The current backend CMake enables C/C++ and OpenGL; its CUDA README explicitly identifies CUDA as planned and not yet enabled. Add optional CUDA detection and targets only when a concrete kernel and CPU implementation exist. Keep standalone GLFW diagnostics separate from the production UI.

Update CMake asset paths, tests and extension output/import paths for the new layout. Do not copy machine-specific CMake caches, compiled extensions, virtual environments, vendored build outputs or duplicate project archives.

Use RecurseIntall's asynchronous database implementation as infrastructure, with CST's observable data contract taking precedence. Preserve CST field meaning, units, timestamps, query results and export formats. RI's run/readings/processed-metrics schema may be used internally only with lossless mapping or a compatibility view; otherwise extend or change it to satisfy CST. Define the mapping in the adapter and validate representative records. Snapshot recall submits commands through the same command gateway as manual control while preserving CST recall behavior.

## Suggested implementation order

1. Copy the selected backend sources, dependency metadata and tests into the preserved layout; establish a simulation/build baseline.
2. Port the main UI shell and one monitoring window to PySide6 with the original assets and appearance.
3. Wire telemetry and command adapters to the existing backend. Verify channel mapping, units, enabled states and command acknowledgements in simulation.
4. Connect history, settings, alarms and snapshot screens to backend services; validate schema conversion and asynchronous reads/writes.
5. Port remaining control/GA/sequence views, removing duplicate backend ownership as each view is connected.
6. Integrate native OpenGL plot surfaces where they improve the selected UI; check context cleanup and window reopen behavior.
7. Add optional CUDA acceleration after profiling a concrete workload. Verify CPU/GPU result agreement and CPU-only startup.
8. Run retained backend tests and focused integration checks for queue pressure, disconnect/reconnect, database persistence, shutdown and visual parity.

The first deliverable should be the selected UI shell displaying simulated backend telemetry and issuing commands through the existing gateway. That validates the integration boundary before moving every screen.

## Source provenance and update comparison

This section refines the earlier mapping: choosing RecurseIntall as the backend does **not** mean discarding newer nonvisual behavior in Control System Tune. The combined application must retain those behaviors while using the backend architecture above.

Comparison scope: the outer Control System Tune folder and RecurseIntall's active `source/`, `include/`, and `python/app/` files were inspected, with direct text comparisons of the PID, GA candidate, evaluation and recovery modules. This is a static architecture review, not a runtime parity certification or a claim that every file has been exhaustively compared. Folder dates and file size alone do not establish which implementation is newer.

Paths in the tables use these exact roots:

- **CST** = `Control System Tune 10_15_NewVersion/`.
- **RI** = `RecurseIntall/Crocker-Digitlization-GUI/CrockerGUI/`.
- **NEW** = integration code to be implemented inside `Combination/`.
- **MIXED** = CST behavior/UI combined with RI infrastructure; not a verbatim copy.

### Confirmed shared algorithms: preserve one implementation

| CST source | RI source | Observed difference | Proposed source and action |
| --- | --- | --- | --- |
| `pid_controller.py` | `source/Python/Control/NLAPID.py` | Direct diff shows the adaptive controller renamed to `NLAPID`, with a compatibility alias; the algorithm body is shared. | **RI** `source/Python/Control/NLAPID.py`; preserve CST-facing API through adapter. Do not invent a second PID engine. Native `NLAPID.cpp` is a separate implementation whose parity still needs tests. |
| `ga_pid_tuner.py` | `source/Python/Optimization/october_ga.py` | Direct text diff shows no content changes despite byte hashes differing. | **RI** existing module, exposing the interface required by CST's updated view. |
| `ga_recovery_manager.py` | `source/Python/Automation/ga_recovery.py` | Direct text diff shows no content changes. | **RI** existing recovery algorithm; retain CST's additional workflow gates separately. |
| `ga_test_runner.py` | `source/Python/Automation/ga_evaluation.py` | Import relocation plus RI compatibility aliases `FitnessTerms` and `Phase`. | **RI** evaluator; preserve CST scoring settings and results presentation. |

These shared modules do not establish parity between the entire applications: much of the orchestration currently lives inside UI/controller files.

### Control System Tune updates and integration gaps

“Gap” below means missing or different in the inspected active path, not necessarily absent from all archives. RI already contains `ExperimentFiles/OctoberPID/pid_beam_buffer.py`, `pid_decision_log.py`, and the older project's application files; archived presence alone does not wire a feature into RI's active application.

| Feature / evidence from CST | RI counterpart / observed gap | Combined destination and provenance |
| --- | --- | --- |
| `pid_beam_buffer.py`: thread-protected high-rate packet buffer, source/receive timestamps, cycle marks, range-consistent raw-voltage averaging followed by calibration | Active `source/Python/Control/FeedbackAverage.py` provides a simpler window average; the inspected active GA page does not use CST's `BeamSampleBuffer` integration. | **MIXED** new `source/Python/Control/beam_sample_buffer.py` derived from **CST**; feed it from **RI** acquisition before GUI decimation. Keep packet timing and range validity semantics. |
| `pid_ga_control_tab.py`: separate beam-average window, post-command response wait, complete fresh averages, raw/averaged display traces | RI GA page has loop/direction timing controls but a different orchestration path. Existing averaging alone does not establish these semantics. | UI controls/plots from **CST**; extract timing/state execution into **NEW** `source/Python/Control/pid_cycle_service.py`, using **RI** gateway and controller. Response wait starts after callback, not proof of hardware application or physical settling. |
| `pid_ga_control_tab.py`: automatic baseline refresh after sustained averaged error inside deadband | RI has baseline capture/recovery, but equivalence to this sustained-deadband refresh was not established. | Preserve **CST** policy in the new cycle service; use **RI** persistence and gateway. Test reset conditions and operator changes. |
| `pid_decision_log.py` and calls in `pid_ga_control_tab.py`: per-decision/event diagnostic records | RI has `pid_database.py` and PID recording infrastructure; no equivalent active `PIDDecisionLog` wiring was found in the inspected GA page. | **MIXED** new `source/Python/Data/pid_decision_recorder.py`: field/event contract from **CST**, asynchronous storage from **RI**; add schema migration/export only for fields not already represented. |
| `controller_context.py`: shared state/signals, manual/PID/GA/single-sequence/multi-sequence modes, power/enable state and beam freshness | RI `python/app/Automation/GA/ControllerContext.py` is a smaller, different context; RI also has `ControlOwnership.py` and native gateway ownership. | **MIXED** `python/adapters/controller_context.py`: CST's view-facing state API backed by RI authority. UI mode changes request backend ownership; they cannot merely set a local mode string. |
| `BO/bo_control_tab.py`, `bo_pid_adapter.py`, `bo_trial_runner.py`: BO operator workflow, asynchronous proposals, measured baseline recovery, validation and explicit apply | RI already supplies BO optimizer modules, but that alone does not provide CST's exact search/validate/apply workflow. CST's BO README explicitly says its optimizer was ported from RI. | View from **CST** into `python/app/controls/bo_control_tab.py`; orchestration port into **NEW/MIXED** `source/Python/Automation/bo_trial_service.py`; optimizer from **RI** `source/Python/Optimization/`. Do not keep a second `BO/optimization/` copy. |
| `BO/README.md`, `bo_trial_runner.py`: measured beam/TC recovery gate, stable hold, timeout, minimum validation scoring duration and approval invalidation | RI GA recovery is shared, but these BO-specific workflow gates must be preserved explicitly. | **CST** policy port into backend trial service. Current documented values include 3 s stable recovery, 60 s timeout, at least 60 s validation, and a 120% score heuristic; preserve as explicit settings and validate behavior. They are not stability guarantees. |
| `sequence_control_tab.py`, `multi_tc_sequence_tab.py`: single/multiple TC timed rows, pause/stop and mode handover | RI `source/Controls/Sequencer/` and `python/app/Controls/SequencePanel.py` already implement sequencing; exact UI row/interpolation/pause semantics need comparison. | Views from **CST**, execution from **RI** sequencer. Add conversion/validation in **NEW** `python/adapters/sequence_adapter.py`; port any unsupported semantics into the backend rather than running a second UI timer executor. |
| `beam_range.py`, `beam_cal.py`, `scaling.py`: range encodings, raw/engineering conversion, packet building | RI `ZMQProtocol.cpp`, `BeamCalibrationService.py`, `SignalMapService.py` and scaling configuration serve related roles. Packet and calibration equivalence is unverified. | **RI** transport/services with **CST** compatibility requirements. Verify range bit layouts, packet widths, channel order, units and calibration curves using representative packets. Do not duplicate encoders or calibrate twice. |
| `snapshot_save_qt.py`, `snapshot_recall_qt.py`, `sqlite_viewer_qt.py`, `sqlite_viewer_scaling.py`, `sqlite_viewer_report.py`, `ScaleCalWindow.py`, `scale_cal_editor.py`, `SpinWheelCalWindow.py` | RI has snapshot stores, history/export pages and workbook services; schemas and workflows differ. | UI from **CST** into history/configuration; data operations from **RI** through adapters. Preserve CST's export, recall and calibration workflows with explicit field mapping. |
| `alarm.py`, `AlarmSettingsDialog.py`, `SettingsDialog.py`, `app_settings.py` | RI has alarm/interlock services and settings/configuration pages. Settings keys, defaults and alarm transitions still require mapping. | Dialogs and operator behavior from **CST**; service execution from **RI**. **NEW** configuration migration must report unsupported keys instead of silently dropping them. |

### File-level provenance for the selected UI

The following files come from the **outer CST folder**, with Qt/API/import changes only where required by integration. Backend operations embedded in these views are extracted or routed through adapters.

| Proposed destination | Exact CST source files | RI contribution |
| --- | --- | --- |
| `python/app/shell/` | `main_control_gui.py`, selected functionality from `gui_window.py` | Application startup/backend handles; no RI visual shell replacement. |
| `python/app/monitoring/` | `MagneticFieldMonitoringWindow.py`, `BeamTransportMonitoringWindow.py`, `SourceExtractionMonitoringWindow.py`, `VacuumBeamMonitoringWindow.py`, `SmallScreenMagneticBeam.py` | Snapshot data, native rendering where selected, read/processing services. |
| `python/app/controls/` | `MagneticFieldControllerWindow.py`, `manual_control_tab.py`, `sequence_control_tab.py`, `multi_tc_sequence_tab.py`, `pid_ga_control_tab.py`, `BO/bo_control_tab.py` | Command/control/sequence/optimizer execution. |
| `python/app/widgets/` | Reusable widgets extracted from those windows, plus `pid_axis_trend_plot.py` | `PlotSurface.py` and `NativeRenderLifecycle.py` from `RI/python/app/widgets/` only where native surfaces are used. |
| `python/app/theme/` | `controller_theme.py`, `neon_style.py` | No replacement of CST appearance by RI theme. |
| `python/app/configuration/` | `AlarmSettingsDialog.py`, `SettingsDialog.py`, `ScaleCalWindow.py`, `scale_cal_editor.py`, `SpinWheelCalWindow.py` | RI service APIs and database/configuration adapters. |
| `python/app/history/` | `snapshot_save_qt.py`, `snapshot_recall_qt.py`, `sqlite_viewer_qt.py`, `sqlite_viewer_scaling.py`, `sqlite_viewer_report.py` | RI database reader/writer and export infrastructure. |
| `assets/ui/` | Referenced files from CST `icons/`, root images/video, `static/` | RI engine resources stay separately in `assets/engine/`. |

Numbered, `_working`, nested-project and zipped alternatives must be diffed before selecting a replacement for these canonical files. `main.py` in Combination is **NEW**, not either project's launcher copied unchanged.

### RecurseIntall features to retain while replacing its UI

Retain RI's native transport/control/sequencer, simulation modes, asynchronous telemetry/PID persistence, calibration and signal services, optimizer library, and OpenGL engine. Also retain reusable nonvisual logic currently located under its UI tree: `Automation/ControlOwnership.py`, `Controls/SnapshotStore.py`, history readers/export helpers, and native render lifecycle support as needed. Move such logic behind CST views rather than dropping it solely because its current path contains `python/app/`.

RI also offers `HybridPIDPage.py`, Python/native PID paths, cruise automation, hardware profiles, surrogate/response plots, monitor-window assignment and `FPSMonitor.py`. These are RI capabilities to preserve or expose through CST-styled screens when required; equivalent CST screens were not established by this review. They should not replace the selected CST shell or silently disappear during migration. `web_app.py` / `web-app.py` and LabVIEW `.vi` assets in CST require a separate scope check; they are not automatically part of the desktop UI migration.

### Required additions to the proposed tree

```text
source/Python/Control/
    beam_sample_buffer.py          # CST packet-buffer behavior, RI acquisition
    pid_cycle_service.py          # extracted CST timing/baseline policy
source/Python/Automation/
    bo_trial_service.py           # CST search/recovery/validation, RI optimizer
source/Python/Data/
    pid_decision_recorder.py       # CST event fields, RI async persistence
python/adapters/
    controller_context.py         # CST state API, RI control authority
    sequence_adapter.py           # CST rows -> RI sequencer
python/app/controls/
    bo_control_tab.py             # CST BO view ported to PySide6
```

These are proposed responsibility boundaries, not implementations. Before merging, build a parity checklist from the actual CST callbacks: packet timing/range changes, fresh-window decisions, response waits, baseline refresh, arming/ownership, GA recovery, BO search/validation/apply, sequence pause/resume, alarm transitions, snapshot recall and recorded/exported fields. Use CST's `test_pid_modules.py` and `BO/test_bo_integration.py` as behavioral references alongside RI's existing tests. Resolve differences explicitly; neither matching filenames nor an existing archived copy proves active feature parity.
