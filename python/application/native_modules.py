"""Select the native build for the current interpreter and platform."""
from importlib.machinery import EXTENSION_SUFFIXES
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def configure_native_path():
    explicit = os.environ.get("COMBINATION_CHARTS_DIR")
    candidates = [Path(explicit)] if explicit else [ROOT/"build/windows/Release", ROOT/"build/ubuntu", ROOT/"build/Release"]
    for directory in candidates:
        if all(any((directory/f"{module}{suffix}").is_file() for suffix in EXTENSION_SUFFIXES)
               for module in ("CombinationCharts", "CombinationBackend")):
            resolved = str(directory.resolve())
            if resolved in sys.path:
                sys.path.remove(resolved)
            sys.path.insert(0, resolved)
            return directory.resolve()
    raise RuntimeError("Native modules missing or incompatible. Run scripts/install.ps1 or bash scripts/install_ubuntu.sh.")
