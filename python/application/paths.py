"""Resolve application resources without relying on the launch directory."""
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def runtime_path(relative=""):
    return Path(os.environ.get("COMBINATION_RUNTIME_DIR", str(ROOT/"runtime"))).resolve()/relative


def configure_environment():
    """Seed editable runtime config from CST defaults without overwriting edits.

    Existing CNL_* overrides are retained. Defaults are copied byte-for-byte
    from CST into config/ by the migration utility; RI defaults are not merged.
    """
    for filename, variable in (("calibration.json","CNL_CALIB"), ("beam_cal.json","CNL_BEAM_CAL"),
                               ("app_settings.json","CNL_APP_SETTINGS"), ("alarm_config.json","CNL_ALARM_CONFIG")):
        destination=runtime_path("config")/filename
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists(): shutil.copyfile(ROOT/"config"/filename,destination)
        os.environ.setdefault(variable,str(destination))
    os.environ.setdefault("CNL_DB_PATH",str(runtime_path("databases/cyclotron_data.db")))
    os.environ.setdefault("CNL_SQLITE",os.environ["CNL_DB_PATH"])
    # CST's alarm service uses a different variable from its settings editor.
    os.environ.setdefault("CNL_ALARM_CFG",os.environ["CNL_ALARM_CONFIG"])
    os.environ.setdefault("MPLCONFIGDIR",str(runtime_path("cache/matplotlib")))
