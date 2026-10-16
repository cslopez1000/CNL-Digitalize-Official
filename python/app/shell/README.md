# python/app/shell

`main_control_gui.py` is the migrated CST launcher: original bubble layout, icons, orbit animation, display averaging and navigation. `python/application/shell.py` supplies shared-backend factories and file-worker integration. Main.py opens this launcher by default. All graph rendering is delegated to native hosts in the selected screens; the launcher itself is Qt UI decoration. See `docs/LAUNCHER_INTEGRATION.md`.

CST main_control_gui.py and selected gui_window.py shell behavior. No RI visual shell substitution.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
