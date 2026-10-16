# python/app/configuration

`SettingsDialog.py` and `ScaleCalWindow.py` reuse the active CST layouts, persistence, curve parsing and CSV/XLSX workflows. Settings use the shared CST services and seeded runtime files. Calibration previews draw through `CstCalibrationWidget` in C++; no live Matplotlib canvas is used. Other archived editor variants are not automatically part of the active launcher. See `docs/LAUNCHER_INTEGRATION.md`.

CST alarm/settings/scaling/calibration editors. CST files/keys/defaults remain authoritative.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
