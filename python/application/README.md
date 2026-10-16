# python/application

`simulation.py` composes the reused CST controller, native simulation bridge and native sequence editor mixins, and coordinates shutdown. `paths.py` resolves/seeds runtime configuration without overwriting edits. `native_modules.py` chooses the platform/interpreter-compatible build. The root main.py selects simulation or the standalone graph preview.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.

`simulation_app.py` owns one SimulationSession and defaults through main.py to the CST launcher in `shell.py`. The launcher opens all active CST screens using the shared backend; the standalone controller remains available with `--controller`. `history.py` owns background SQLite requests, `snapshot_recall.py` loads workbooks asynchronously, and `vacuum_monitor.py` composes the reused CST vacuum/beam view. Session shutdown attempts every view cleanup, then stops acquisition and flushes SQLite, including startup-failure paths. See `docs/LAUNCHER_INTEGRATION.md` for provenance and limits.
