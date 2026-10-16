# source/Python/Services

Current modules `beam_cal.py`, `beam_range.py`, `scaling.py` and `app_settings.py` are reused from CST with explicit package/Qt imports. They are the authority for calibration, range codecs and configuration semantics. Runtime paths are established before import. RI service infrastructure can be reused later where it reproduces these same CST contracts; it must not silently replace their settings or formulas.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
