# CST graphs with a C++ backend

Current milestone: the integrated CST controller uses native PID/GA trends, manual trends, beam-meter history and gain radar. See [INTEGRATED_SIMULATION.md](INTEGRATED_SIMULATION.md). Python hosts own Qt lifetime; C++ owns axes, geometry and drawing. Other monitoring-window graphs are still pending.

## Implemented scope and provenance

The graph requirement is CST appearance/semantics with native C++ preparation and OpenGL drawing. Python provides Qt widget lifetime, input coercion and data handoff. It does not paint the new trend graph.

`source/Engine/`, `include/Engine/`, fonts and shaders were copied from RI into Combination. Original projects remain unchanged. `docs/evidence/source_audit.json` records file origins and hashes. Other RI native chart classes are retained infrastructure; their presence does not imply CST parity.

New `CstTrendModel.hpp/.cpp` ports the active CST `pid_ga_control_tab.py::TrendPlot`, which embeds and extends the separate `pid_axis_trend_plot.py` design: finite-row filtering, shortest-series alignment, 120-second relative-time history, 600-point default display limit, Python ties-to-even index selection, evaluation-axis anchoring, padded/nice axes and numeric/scientific ticks. Missing best-valid GA targets remain gaps rather than invented winners. Epoch timestamps remain doubles until converted to display geometry.

New `CstTrendPlot.hpp/.cpp` uses RI's render context/text infrastructure with CST panel/cyan/orange/green colors, margins, straight traces, two-series response fill, three-series raw/average overlays, glow widths and endpoint markers. It does not apply RI's default curve smoothing. Native triangles provide round joins/caps independently of driver wide-line support. The fill shader uses CST's four alpha-gradient stops.

`source/Bindings/ChartBindings.cpp` exposes `CombinationCharts`; the `Cst*Widget.py` hosts provide the existing CST graph APIs and explicit context cleanup. They are wired into the integrated controller. `CombinationBackend` separately exposes the simulation and PID engine.

## Concrete RI graphics fixes in Combination

- `Graphics/OpenGL/Objects.hpp`: retain buffer capacity and upload with subdata; geometrically grow storage rather than allocate for every primitive/text draw. Tests cover reuse, growth, bounds and release/recreation. This reduces allocation calls; no before/after GPU throughput benchmark is claimed.
- `Graphics/OpenGL/StateGuard.*`, `Graphics/RenderContext.cpp`: preserve host line width and program-point-size state; use deterministic one-pixel native grid lines and fixed-function point size. Wide curves use triangles.
- `Graphics/RenderContext.cpp`, `Text/TextRenderer.cpp`: separate RGB and alpha blending so alpha accumulation uses source alpha once rather than squaring it.
- `Graphics/RenderContext.cpp`: reject malformed XY buffers and invalid primitive enums before GPU calls.
- `Text/Internal/GlyphAtlas.cpp`: generate mipmaps for the oversampled font atlas to improve small CST tick-label sampling. Native font rendering still needs comparison with CST Qt text at every target DPI.
- `Text/Internal/FontRasterizer.cpp`: normalize baked ascent/descent height to em units before scaling CST font sizes; Qt and Nuklear otherwise interpret the same numeric size differently, producing undersized native labels.
- `Text/Internal/FontRasterizer.cpp`: use isotropic atlas sampling instead of Nuklear's horizontal-only 3x oversampling. Combined with mipmaps, this fixes the blurry/fragmented small labels observed during desktop integration. Add the Unicode minus glyph used by CST beam history.
- `assets/engine/shaders/primitive2d.*`: support CST measured-response gradient; ordinary native primitives explicitly disable the gradient.

## Build and verify

From the workspace root in PowerShell, using the existing RI Python 3.13 environment:

```powershell
$graphPython = Resolve-Path 'RecurseIntall/Crocker-Digitlization-GUI/CrockerGUI/.venv/Scripts/python.exe'
cmake -S Combination -B Combination/build -G 'Visual Studio 17 2022' -A x64 "-DPython_EXECUTABLE=$graphPython"
cmake --build Combination/build --config Release -- /m:1 /nodeReuse:false /p:TrackFileAccess=false
& $graphPython -B Combination/scripts/run_verification.py
```

The verification command records a nonzero result when any check fails, including the pre-existing CST PID reference-test/API mismatch. Consult `docs/evidence/verification.json` and individual logs. It does not label that failure a pass.

This build currently reuses RI's sibling `external/` checkout for GLAD, GLM and the font rasterizer dependency. Override `COMBINATION_REFERENCE_ROOT` to relocate it. It is not a portable packaged full application. The native extension is in `build/Release`; add that directory to Python's import path before importing the widget. CUDA and the full control/database application are not part of this build.

## Visual evidence and remaining work

Offscreen integration tests create a real OpenGL 4.6 context, render two/three-series graphs, check errors and host state, reject missing context identity, then release/recreate GPU resources. PNGs and GL details are in `docs/evidence/`.

Reference screenshots run CST's chart code with only PyQt6/PySide6 import spellings adapted in memory; both original files remain untouched. These screenshots support manual comparison, not a pixel-equivalence claim. Text rasterization, antialiasing and the one-pixel QRect edge convention can still differ; verify target DPI and window sizes before checking full visual parity off.

Remaining graph work: port the separate CST monitoring plots/meters and any JavaScript graphs, preserve their individual style, cache geometry after profiling, benchmark concurrent panels/large histories, and test context destruction across real window/monitor moves. The first controller integration is not a claim that all visualization work is finished or optimized.
