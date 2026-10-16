# Implementation status

Status reviewed 2026-10-16. CST's launcher is the default entry point. Navigation now opens the portrait controller, all four monitoring screens, history, settings, calibration, range and snapshot dialogs on the shared simulation backend. Ten launcher/history integration tests pass in addition to earlier controller/monitor tests. The desktop check initializes the remaining eight graph surfaces/contexts, including embedded vacuum histories, and exports a native-rendered PDF. See [LAUNCHER_INTEGRATION.md](LAUNCHER_INTEGRATION.md). Hardware, CUDA, full tuning runs, operational alarms and complete parity acceptance remain pending.

## Controller foundation retained under the launcher

The controller milestone remains available with `--controller`. Default `main.py` now opens the CST launcher. Telemetry is recorded asynchronously using CST's schema and RI's writer. Both original source projects remain unchanged.

See [INTEGRATED_SIMULATION.md](INTEGRATED_SIMULATION.md) for run instructions, file origins, thread boundaries, reuse decisions and remaining work. Eleven integrated tests, three native PID parity tests and eleven migrated BO reference tests are included in the evidence runner. Actual desktop captures are in `evidence/simulation_*.png`.

## Graphics/scaffolding baseline

- Created the physical module/folder structure from the proposal and folder READMEs, including build internals. The evidence file records coverage at verification time; `scripts/create_structure.py` can repeat and validate this after regeneration. A documented folder is not an implemented feature.
- Preserved both original projects. Native infrastructure was copied into Combination; source hashes/provenance are in `evidence/source_audit.json`.
- Made CST graph styles/semantics plus a C++ graph backend an explicit requirement.
- Implemented the first native trend model/renderer and PySide6 host, following the active CST PID/GA inline `TrendPlot`, including missing-best-valid GA trace handling.
- Fixed repeated GPU buffer allocations, host point/line state handling, alpha compositing, small-label atlas sampling and font-size unit conversion in the copied RI renderer.
- Added reproducible native/numeric/offscreen rendering tests and evidence-backed checked items in the parity checklist.
- Inventoried candidate CST graph classes in `GRAPH_PORT_INVENTORY.md`, with unported graphs clearly pending.
- Added Windows `scripts/install.ps1` / `run.ps1` and Ubuntu `install_ubuntu.sh` / `run_ubuntu.sh`, dependency files and a runnable native-chart-preview `main.py`. Scripts activate the local venv for their commands and isolate platform build directories. Syntax and import checks passed; clean installs and Ubuntu runtime have not been exercised.

## Recorded verification

| Check | Result | Evidence |
| --- | --- | --- |
| CMake/MSVC Release library/module build | Passed | `build/Release/CombinationCharts.cp313-win_amd64.pyd` and native targets |
| Native text/model/mock GPU upload tests | 3 passed | `evidence/native_cpu_and_mock_gl.txt` |
| Active CST numeric graph differential tests | 5 passed | `evidence/cst_cpp_numeric_parity.txt` |
| Actual OpenGL 4.6 rendering/state/resource smoke | Passed | `evidence/native_render.json`, PNGs |
| PySide6 host API/input coercion smoke | Passed | `evidence/native_widget_api.txt` |
| CST reference screenshots | Generated | `evidence/cst_reference_two_series.png`, `cst_reference_three_series.png` |
| Existing CST BO reference suite | 11 passed | `evidence/cst_bo_reference_suite.txt` |
| Existing CST PID reference suite | Failed: obsolete `trend_tolerance` constructor argument | `evidence/cst_pid_reference_suite.txt` |
| README coverage | Every current folder documented | `evidence/folder_readmes.txt` |

`evidence/verification.json` records commands and statuses. The verification command deliberately returns failure while the reference PID suite fails; that problem is not hidden or marked as passing.

## Still pending

The launcher and active CST screens are integrated in simulation. Remaining work includes hardware protocol/gateway integration and validation, full automatic tuning runs, alarm feeding/annunciation, comprehensive data/configuration/visual acceptance, Ubuntu execution, CUDA and performance profiling. See the root README and launcher guide for the current scoped completion claims.

Some existing native chart classes are copied from RI but still have RI behavior; the new CST renderer avoids selecting their style/smoothing defaults. Use the graph inventory before wiring each CST screen. A successful GL smoke test demonstrates valid rendering/resource behavior; it does not establish all-chart visual parity or optimized GPU throughput.

CST continues to win every conflict. Do not mark remaining checklist entries complete merely because a corresponding folder exists or because reference-only tests pass.
