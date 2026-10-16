# python/app/widgets

`CstTrendWidget.py` owns the shared Qt/OpenGL lifecycle for native PID/GA trends. `CstManualWidget.py`, `CstBeamWidget.py` and `CstGainWidget.py` reuse that lifecycle while selecting the corresponding CST native renderer. Graph axes/geometry/drawing execute in C++; Python exposes the view APIs and hands off data. Complete visual/DPI parity remains acceptance work.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.

The launcher stage adds `CstCalibrationWidget`, `CstVacuumWidget` and `NativeVacuumHistory`. Calibration, beam/RF trends, embedded TP histories and the history pane use native rendering. `NativeChartSurface` provides private offscreen contexts for transparent gauge histories and report-sized graph rendering without changing live views. Gauge backgrounds, needles and readouts remain the original CST Qt UI. See `docs/LAUNCHER_INTEGRATION.md`.

`CstMagneticWidget.py` hosts native grouped coil histories, fixed-range bars, metric sparklines and source/extraction histories. `CstTransportWidget.py` hosts native receipt-age transport plots. Their series adapters preserve the reused CST views' update calls; the native renderer draws glow/fill/line together. History pane hosts live under `python/app/history/native_plot_pane.py`.
