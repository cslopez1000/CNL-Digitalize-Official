# python/app/history

Migrated CST snapshot dialogs, workbook-format functions, history viewer controls, calibration/alias helpers and marker/report data structures live here. `native_plot_pane.py` hosts the C++ history renderer and preserves CST's toolbar, drag/drop and synchronized-range contract. `native_pdf.py` renders charts through independent C++ offscreen surfaces and places those raster images plus CST metadata in atomic A4 PDF reports. Old Matplotlib graph helpers remain reference code and are not selected by the application.

SQLite reads belong to `python/application/history.py` workers; snapshot I/O is serialized by `source/Python/Data/snapshot_store.py`. Keep record meaning, units, filenames and TC-only recall semantics from CST. The remaining source/extraction/transport recall apply buttons are unwired in the selected CST source and remain so. See `docs/LAUNCHER_INTEGRATION.md` for verification limits.

CST SQLite viewer, report and snapshot dialogs using RI asynchronous storage adapters with CST results/export formats.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
