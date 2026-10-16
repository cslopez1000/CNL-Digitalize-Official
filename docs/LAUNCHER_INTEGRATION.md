# CST launcher and remaining screens

Default `main.py` startup now opens the selected outer CST project's launcher. This is a simulation integration, not a hardware release or complete parity certificate. Original source files are unchanged.

## Run and navigation

Run the updated installer, then `scripts/run.ps1` or `bash scripts/run_ubuntu.sh`. `--controller` retains the standalone controller entry point; `--preview` retains the independent chart demo. `--magnetic --transport --source` pre-opens those monitoring windows alongside the launcher.

The launcher retains CST's thirteen bubble icons, positions, labels, animated orbits and action routing. Field Ctrl opens CST's portrait Magnetic/Beam Meter wrapper with the integrated controller inside it. The RF bubble retains CST's original routing to that wrapper; the dedicated RF gauge is in the Vac/Beam screen. No new home-page design was substituted.

Available screens are magnetic, transport, source/extraction and vacuum/beam/RF monitoring; the three-pane record viewer; settings; scaling/calibration; beam range; snapshot save; and snapshot recall. CST's existing placeholder tabs inside its controller remain placeholders. Source, extraction and transport snapshot apply buttons retain CST's explicit unwired behavior; magnetic TC-only recall is connected.

## Provenance and responsibilities

| Combined location | Origin / treatment |
| --- | --- |
| `python/app/shell/main_control_gui.py` | CST `main_control_gui.py`, preserving launcher painting, controls, icons, averaging and routing. Package/Qt/resource paths changed. Duplicate feeding of the full-rate beam buffer removed because acquisition already owns it. |
| `python/app/controls/cst/SmallScreenMagneticBeam.py` | CST portrait layout and range pad; controller construction is injected through the combined application. Exposes the original local controller as `mag_controller`, required by CST's recall callback. |
| `python/app/configuration/{SettingsDialog,ScaleCalWindow}.py` | CST settings/editor layouts, parsing, persistence and CSV/XLSX callbacks. ScaleCalWindow's plot uses the native curve renderer instead of Matplotlib. |
| `python/app/history/snapshot_*.py` | CST dialogs, workbook schema, scaling and row-selection/apply semantics. Worker adapters reuse these functions. |
| `python/app/history/sqlite_viewer_{qt,scaling,report}.py` | CST viewer controls, aliases, calibration, timestamp/marker data structures and report options. Native plot panes replace the interactive Matplotlib classes. The old report-drawing helpers remain reference code and are not selected by HistoryWindow. |
| `python/app/history/{native_plot_pane,native_pdf,plot_controls}.py` | Native hosts/adapters and extracted CST toolbar. Qt lays out text/images in PDF reports; C++ renders the graphs in independent offscreen contexts. Exports use raster graphs, rather than CST's original Matplotlib vector output. |
| `python/app/monitoring/VacuumBeamMonitoringWindow.py` | CST gauge UI, readouts, unit/range handling, scaling and stability table retained. Beam/RF charts and vacuum histories draw in C++; gauge decoration/needles/text remain CST Qt painting. |
| `python/application/{shell,history,snapshot_recall,vacuum_monitor,simulation_app}.py` | New composition/lifecycle adapters: one backend owner, lazy navigation, window cleanup, reader workers and asynchronous snapshot reads. |
| `python/adapters/background_tasks.py`, `source/Python/Data/snapshot_store.py` | New serial I/O boundaries. Readers own independent SQLite connections; writes preserve CST workbook logic with atomic replacement. Snapshot writes are never coalesced/cancelled as stale display requests. |
| `source/Engine/Visualization/Charts/Cst{History,Vacuum}Plot.cpp` and `CstTrendPlot.cpp` | New CST chart ports using RI graphics/context infrastructure. Numeric bounds/log transforms/zoom/mouse mapping and all graph drawing are native. `ChartStroke.hpp` shares existing triangle stroke tessellation. |
| `source/Python/Services/alarm.py` | CST alarm settings/rules reused. Settings and activation toggle are connected; the original launcher's missing alarm feed/annunciation workflow is not represented as operational alarm certification. |

Migration utilities preserve existing ports rather than overwrite them. File hashes/destinations are recorded in `evidence/shell_migration.json`, `history_migration.json` and `monitor_migration.json`, alongside the earlier controller and RI provenance records.

## Lifecycle and data flow

SimulationSession owns one C++ acquisition worker and the RI asynchronous SQLite writer. The launcher consumes a bounded latest-packet subscription, then uses CST's display averaging and separate queues for each monitor/controller. A dedicated transport queue fixes CST's shared vacuum/transport queue competition. Full-rate PID buffering and recording occur before this display pipeline.

Closing a display never closes a borrowed backend. Closing the launcher/application stops UI producers, cancels pending read requests, joins file workers, releases graphics resources, stops acquisition and flushes storage. The portrait wrapper explicitly shuts down its embedded controller; construction failures also stop the shared session.

Historical queries use read-only, worker-owned connections, parameterized time bounds and quoted validated column names. Stale query results are ignored; clearing all series invalidates a pending query. CST's Unix/LabVIEW epoch selection, aliases, displayed-sample decimation and calibration semantics are retained. Current calibration is used for historical raw values, as in CST.

Snapshot save captures CST-scaled values at the operator's save action, then serializes workbook access on a worker and atomically replaces the destination. The existing file survives a failed save. Recall loads in the background and keeps CST's newest-first preview and TC-only magnetic selection. Remaining fields/actuators are not zeroed by the launcher's older fallback callback.

Embedded vacuum histories render to a transparent native framebuffer and are composited into CST's original gauge painting before its needle/readout. This preserves the source's layer order; a child OpenGL widget would incorrectly cover the readout. PDF graphs similarly use independent native surfaces, preserving live zoom, markers and colors while rendering at the report's aspect ratio.

## Repairs and source limitations

- Adapted `pyqtProperty` and QPen's unsupported `cap=` constructor keyword to PySide6 equivalents without changing gauge styling.
- Restored the portrait controller reference expected by CST recall. TC-only recall follows the active dialog's explicit selection and does not reset main/centering targets through older launcher defaults.
- Connected the launcher's Beam Range dialog signal to the same command sink as the existing controller/range pad.
- The original alarm toggle calls a missing `is_active()` method, so it could only enable alarms. The adapter reads CST's existing `active` property and toggles correctly. Full alarm feeding/annunciation remains separate acceptance work.
- Alarm configuration names `CNL_ALARM_CFG` and `CNL_ALARM_CONFIG` now resolve to the same seeded runtime file. Existing environment overrides are preserved.
- Range-follow logs use ASCII arrows so Windows console encoding cannot interrupt the rest of the follow callback. Repeated identical range packets no longer rewrite identical JSON.
- The known range/coil-status bit overlap and differing launcher/controller nibble policies remain unresolved CST source ambiguities. Hardware acceptance requires authoritative packet fixtures.

## Verification and remaining acceptance

Ten focused integration tests cover the thirteen navigation routes, shared backend ownership, separate fan-out, range commands, settings/alarm persistence, snapshot round trips and failed-save atomicity, persistent-write flush/error reporting on close, TC-only recall, history filtering/scaling/markers, native zoom/log bounds and coordinate mapping. Earlier controller/monitoring/native parity checks remain in the verification runner.

`test_launcher_desktop.py` creates actual Windows Qt/OpenGL windows, saves launcher/vacuum/calibration/history screenshots, checks native contexts and exports a PDF. See `evidence/launcher_desktop.json` and `launcher_*.png`. A successful smoke test does not establish exact axis/pixel/DPI parity. The original CST PID suite still fails on its obsolete `trend_tolerance` argument; this is not hidden.

Remaining work: hardware transport/protocol/gateway adaptation and validation, optional CUDA, full GA/BO runs, alarm operator workflow, all-source database/workbook migration fixtures, comprehensive visual/PDF comparison, long-running error/queue/shutdown tests, performance profiling and actual Ubuntu execution. No full-system or hardware-readiness claim is made by this milestone.
