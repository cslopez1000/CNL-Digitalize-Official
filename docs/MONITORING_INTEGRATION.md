# CST monitoring integration

This document records the earlier three-monitor milestone. The subsequent [launcher integration](LAUNCHER_INTEGRATION.md) adds CST navigation, vacuum/beam/RF monitoring, history and configuration screens. Default startup now opens the launcher; use `--controller` for the earlier standalone controller entry point.

Three CST views are runnable with the native controller simulation: magnetic field, beam transport, and source/extraction. Their original source projects remain untouched. The full CST launcher, vacuum/beam monitor, history and configuration dialogs remain unfinished.

## Run

From Combination, build/install as documented in the root README, then run:

```powershell
scripts/run.ps1 --magnetic --transport --source
```

Ubuntu equivalent: `bash scripts/run_ubuntu.sh --magnetic --transport --source`. Ubuntu execution has not been tested. The controller and requested monitors open together; these switches are intermediate entry points, not a replacement design for CST's launcher.

## Sources and integration changes

| Combined files | Origin and retained behavior |
| --- | --- |
| `python/app/monitoring/MagneticFieldMonitoringWindow.py` | CST file of the same name: layout, channel grouping, table/status, calibration, peak-to-peak errors, plot selection, retention and metric cards. Qt/package/resource imports and native graph hosts adapted. |
| `python/app/monitoring/BeamTransportMonitoringWindow.py` | CST file of the same name: all ten channels, table/errors, receipt-relative history, stale readouts, branding and splitter layout. Native graph hosts replace pyqtgraph helpers. |
| `python/app/monitoring/SourceExtractionMonitoringWindow.py` | CST file of the same name: extraction/source/angle tables, scaler calls, legacy packet fallback, impedance calculation, eleven plots, receipt buffering and panel decoration. Native graph hosts replace pyqtgraph helpers. |
| `python/application/{magnetic_monitor,transport_monitor,source_monitor}.py` | New composition adapters: subscribe/unsubscribe, simulation identification, graph error collection and timer/resource cleanup. Magnetic targets follow the existing CST controller context. |
| `python/adapters/simulation_bridge.py` | Existing combined RI/CST adapter extended with independent bounded display mailboxes. Full-rate PID buffering and SQLite recording still precede display publication. |
| `source/Simulation/SimulationRuntime.cpp` | Existing RI-derived combined native worker. Transport fixtures use CST's demo formula. Source/extraction fixtures use CST demo nominal values/oscillations with random noise omitted for reproducibility. They are raw simulated values passed through CST calibration, not a device model. |
| `source/Engine/Visualization/Charts/CstTrendPlot.cpp` and `python/app/widgets/Cst{Magnetic,Transport}Widget.py` | New native monitor rendering using RI graphics/context infrastructure and CST per-view palettes, grouping, history semantics, halos, fills and bars. No pyqtgraph dependency or Python graph painting is used by these three views. |

Source hashes and destinations are recorded in `evidence/monitor_migration.json`. `scripts/import_cst_monitors.py` reads originals and refuses to overwrite migrated files.

## Lifecycle and threading

The application owns one SimulationBridge. Every view gets a separate latest-packet queue of capacity one; a slow display drops display frames without blocking acquisition or stealing another window's data. A late subscriber immediately receives the last packet. Subscription changes and publication are protected by one lock. The native worker supplies all simulated numeric sensor values. The collector records every acquired frame before display decimation. UI queues are consumed only by their own Qt windows.

Closing a borrowed controller or monitor stops its timers, unsubscribes and releases native graphics resources. It does not close the shared backend. Application exit stops views, then stops acquisition and flushes recording. Standalone SimulationControllerWindow retains its existing ownership behavior for callers/tests that do not inject a bridge.

## Verification and known differences

- `tests/integration/test_monitoring.py`: five tests cover independent/bounded subscriptions, late join and unsubscribe, simultaneous views, CST scaling and targets, hold-last behavior, close/reopen, recorded sensor fields, and application-wide ownership/shutdown flushing.
- `tests/integration/test_monitoring_desktop.py`: Windows desktop smoke initialized ten transport, six magnetic and eleven source chart contexts, received telemetry, saved screenshots and closed without reported errors. Evidence: `evidence/transport_desktop.json`, `transport_monitor.png`, `magnetic_monitor.png`, `source_monitor.png`.
- `tests/integration/test_native_render.py` also exercises transport and all four native monitoring render modes with finite gaps, input validation and GL host-state restoration. It remains a rendering smoke test, not an exact pixel comparison with pyqtgraph.
- Native monitor axes currently use explicit padding and the native nice-tick implementation. Exact pyqtgraph auto-padding/tick selection, raster parity across DPI, long-history clipping and GPU throughput remain acceptance work. A smoke pass does not certify complete visual parity.
- CST's magnetic layout no longer creates `scaling_status`, but its calibration refresh/toggle callbacks still access it. The migrated view creates a hidden label so those callbacks work without changing the visible layout. This is an explicit defect repair; original CST code is unchanged.
- CST's active magnetic monitor interprets bits 0..13 as coil ON and 14..27 as remote, while its RangeCodec puts mirrored range nibbles in bits 0..7. The same mask can therefore display coil states unrelated to simulated command masks. The port retains CST's active interpretation rather than inventing a protocol. This source ambiguity remains unresolved for hardware acceptance; the monitor is not evidence of physical power state.
- Hardware communication, full application navigation and the remaining screens are not implemented by this milestone.
