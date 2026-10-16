# Install and run

These scripts install dependencies into `Combination/.venv`, activate it for their own commands, build the C++ backend/graph extensions, and open CST's launcher with integrated simulation screens. Hardware integration remains pending. Installers do not modify either original source project or start hardware control.

Run the examples from the `Combination` directory. The scripts themselves resolve absolute paths and can be called from another directory, including paths with spaces.

## Windows PowerShell

Prerequisites: Python **3.13 64-bit**, CMake, and Visual Studio **2022** / Build Tools with Desktop development with C++ and a Windows SDK. Keep the sibling RI `external/` dependencies available.

```powershell
.\scripts\install.ps1
.\scripts\run.ps1
```

Choose simulation explicitly with `scripts/run.ps1 -Simulation`. `-ZMQ` is
recognized but exits with an explicit error: Combination's ZMQ backend is not
implemented. It never falls back to simulation. The switches are mutually exclusive.
Ubuntu accepts the same spellings, for example `bash scripts/run_ubuntu.sh -Simulation`
or `-ZMQ`; direct Python invocation also accepts `--simulation` and `--zmq`.
See [remaining features](../docs/REMAINING_FEATURES.md) for current limitations and BO access.

To check the environment without opening a window:

```powershell
.\scripts\run.ps1 -Check
```

Select an explicit interpreter or optional future backend packages:

```powershell
.\scripts\install.ps1 -PythonExecutable 'C:\path\to\python.exe' -Dependencies Backend
.\scripts\install.ps1 -Dependencies Optimization
```

`Core` (default) installs `requirements.txt`: PySide6, pybind11, openpyxl, NumPy, pandas and Matplotlib. These support the CST views, workbook workflows and reused history/report data helpers; active graph rendering uses C++. `Backend` adds transport/scientific packages; `Optimization` includes Torch/BO/GP dependencies. Full automatic tuning/validation runs remain unverified.

Default startup is CST's bubble launcher. Add `--magnetic --transport --source` to pre-open monitors; all screens are also available from the launcher. Use `scripts/run.ps1 --controller` or `bash scripts/run_ubuntu.sh --controller` for the standalone controller. `--preview` opens the independent chart demo. Re-run the installer after updating this code to rebuild native modules and install the new workbook/history dependencies.

The installer accepts `-ReferenceRoot 'C:\path\to\CrockerGUI'` to locate RI's native dependencies. It builds in `build/windows` and uses the extension from `build/windows/Release`.

If PowerShell blocks local scripts, use an invocation-scoped policy if permitted by your environment; the installer does not change machine policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1
```

To activate the environment manually in your current shell:

```powershell
. .\.venv\Scripts\Activate.ps1
```

## Ubuntu / Bash

Prerequisites: Python **3.13 64-bit** with its matching venv and development headers, a C++20 compiler, CMake, Ninja, and a desktop/driver supporting OpenGL **4.6 core**. Python 3.13 package availability depends on the Ubuntu release; install it through your chosen supported Python installation method. The script does not add third-party apt repositories. WSL needs WSLg or another working display/GL setup for the preview.

```bash
bash scripts/install_ubuntu.sh --system-deps
bash scripts/run_ubuntu.sh
```

`--system-deps` uses `sudo apt-get` to install build/OpenGL/XCB prerequisites. Omit it if those prerequisites are already installed. Use an explicit Python interpreter as needed:

```bash
PYTHON=/path/to/python3.13 bash scripts/install_ubuntu.sh
bash scripts/run_ubuntu.sh --check
```

Optional dependency sets and RI dependency location:

```bash
bash scripts/install_ubuntu.sh --backend
bash scripts/install_ubuntu.sh --optimization
COMBINATION_REFERENCE_ROOT=/path/to/CrockerGUI bash scripts/install_ubuntu.sh
```

Ubuntu builds in `build/ubuntu`. Run scripts automatically activate/use the local virtual environment. Activation from an executed Bash script does not persist in the parent shell; to keep it active interactively:

```bash
source .venv/bin/activate
```

Do not share a Windows virtual environment with Ubuntu. Use a separate checkout/environment; installers reject an existing incompatible/incomplete `.venv` rather than overwriting it.

## Other scripts and verification

- `create_structure.py`: create missing planned folders and ensure every current folder has a README.
- `run_verification.py`: record native, CST numeric/BO/PID reference and offscreen GL checks. The pre-existing CST PID test/API mismatch is recorded as a failure.

`requirement.txt` at the project root is a compatibility alias for the canonical `requirements.txt`. Scripts use the canonical plural filename.

PowerShell files were syntax-checked, Bash files were checked with `bash -n`, and `main.py --check` passed against the existing native build. Full clean installation/downloads and Ubuntu execution have not been performed on this Windows host.
