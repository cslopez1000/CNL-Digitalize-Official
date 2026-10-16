# CST graph port inventory

Static candidates from outer CST Python files. Some are legacy/demo or container widgets; active imports must be traced before selecting them. C++ must reproduce the selected CST style and behavior, not replace it with RI defaults.

| CST file | Symbol / line | Native port status |
| --- | --- | --- |
| `4 meters with time domian.py` | `TimeSeriesPlot` : 16 | Pending active-path classification and native port |
| `4 meters with time domian.py` | `NeonGauge` : 105 | Pending active-path classification and native port |
| `4 meters with time domian.py` | `GaugeWithPlot` : 320 | Pending active-path classification and native port |
| `4 meters with time domian.py` | `FourGaugeWindow` : 363 | Pending active-path classification and native port |
| `4 meters.py` | `TimeSeriesPlot` : 68 | Pending active-path classification and native port |
| `4 meters.py` | `NeonGauge` : 135 | Pending active-path classification and native port |
| `4 meters.py` | `SemiArcPowerGauge` : 276 | Pending active-path classification and native port |
| `4 meters.py` | `SemiArcVacuumGauge` : 363 | Pending active-path classification and native port |
| `4 meters.py` | `FourGaugeWindow` : 484 | Pending active-path classification and native port |
| `4 meters_done.py` | `TimeSeriesPlot` : 65 | Pending active-path classification and native port |
| `4 meters_done.py` | `LogVacuumGauge` : 369 | Pending active-path classification and native port |
| `4 meters_done.py` | `FourGaugeWindow` : 601 | Pending active-path classification and native port |
| `controller_theme.py` | `PlotToggle` : 181 | Pending active-path classification and native port |
| `controller_theme.py` | `TrendPlot` : 224 | Native C++ port used by integrated simulation; full cross-DPI parity pending |
| `MagneticFieldControllerWindow.py` | `_ControllerBeamPlot` : 278 | Native C++ port used by integrated simulation; full cross-DPI parity pending |
| `new meter_10_6_2025.py` | `NeonRadialGauge` : 24 | Pending active-path classification and native port |
| `pid_axis_trend_plot.py` | `AxisTrendPlot` : 34 | Pending active-path classification and native port |
| `pid_ga_control_tab.py` | `TrendPlot` : 151 | Native C++ port used by integrated simulation; full cross-DPI parity pending |
| `SourceExtractionMonitoringWindow.py` | `TeslaPlotCard` : 209 | Pending active-path classification and native port |
| `sqlite_viewer_qt.py` | `PlotPane` : 313 | Native C++ port used by integrated simulation; full cross-DPI parity pending |
| `sqlite_viewer_report.py` | `PlotSnapshot` : 70 | Pending active-path classification and native port |
| `untitled12.py` | `TimeSeriesPlot` : 136 | Pending active-path classification and native port |
| `untitled12.py` | `LogVacuumGauge` : 793 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindow.py` | `TimeSeriesPlot` : 152 | Native C++ port used by integrated simulation; full cross-DPI parity pending |
| `VacuumBeamMonitoringWindow.py` | `LogVacuumGauge` : 873 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindow.py` | `RFNeonGauge` : 1638 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindow1.py` | `TimeSeriesPlot` : 71 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindow1.py` | `LogVacuumGauge` : 372 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindow3.py` | `TimeSeriesPlot` : 111 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindow_working.py` | `TimeSeriesPlot` : 136 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindow_working.py` | `LogVacuumGauge` : 831 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindowO.py` | `TimeSeriesPlot` : 136 | Pending active-path classification and native port |
| `VacuumBeamMonitoringWindowO.py` | `LogVacuumGauge` : 831 | Pending active-path classification and native port |

Selected magnetic/transport/source monitoring graphs now use native hosts in the combined launcher. Calibration curves and embedded TP histories are also native. Vacuum gauge decoration/readouts remain CST Qt UI. Archived web/JavaScript charts are not selected by the launcher. Exact axes, layout, DPI and full chart parity remain acceptance work. A class-name scan is not an exhaustive graph inventory.
