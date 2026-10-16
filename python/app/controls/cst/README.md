# Reused CST controller views

These files originate in the outer Control System Tune project. They preserve the existing controller layout, manual controls, sequence editors, PID/GA workflow, BO page, context and theme.

Necessary changes are limited to PySide6 imports, explicit package imports, absolute resource/output paths and native chart aliases. Native execution is connected in `python/application/simulation.py` and `python/adapters/`; it is not duplicated inside the views. See `docs/evidence/cst_migration_manifest.json` for exact origins.

Large source modules were retained to preserve behavior. Split them only after the relevant parity tests protect a concrete refactor; do not rewrite working CST logic merely for style.
