"""Record reproducible checks and CST source baseline; never mark failures passed."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
CST=ROOT.parent/"Control System Tune 10_15_NewVersion"
RI=ROOT.parent/"RecurseIntall/Crocker-Digitlization-GUI/CrockerGUI"
OUT=ROOT/"docs/evidence"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1")
    sys.path.insert(0,str(ROOT))
    from python.application.native_modules import configure_native_path
    native_directory = configure_native_path()
    build_directory = native_directory.parent if native_directory.name == "Release" else native_directory
    env["COMBINATION_CHARTS_DIR"] = str(native_directory)
    tasks=[
        ("native_cpu_and_mock_gl",["ctest","--test-dir",str(build_directory),"-C","Release","--output-on-failure"],ROOT),
        ("cst_cpp_numeric_parity",[sys.executable,"-B",str(ROOT/"tests/python/test_cst_trend_parity.py")],ROOT),
        ("native_pid_parity",[sys.executable,"-B",str(ROOT/"tests/python/test_native_pid_parity.py")],ROOT),
        ("integrated_simulation",[sys.executable,"-B",str(ROOT/"tests/integration/test_simulation_system.py")],ROOT),
        ("monitoring_integration",[sys.executable,"-B",str(ROOT/"tests/integration/test_monitoring.py")],ROOT),
        ("shell_history_integration",[sys.executable,"-B",str(ROOT/"tests/integration/test_shell_history.py")],ROOT),
        ("migrated_bo_suite",[sys.executable,"-B",str(ROOT/"tests/python/test_migrated_bo.py")],ROOT),
        ("native_offscreen_gl",[sys.executable,"-B",str(ROOT/"tests/integration/test_native_render.py")],ROOT),
        ("native_widget_api",[sys.executable,"-B",str(ROOT/"tests/integration/test_widget_api.py")],ROOT),
        ("cst_reference_screenshots",[sys.executable,"-B",str(ROOT/"tests/integration/render_cst_reference.py")],ROOT),
        ("cst_bo_reference_suite",[sys.executable,"-B","-m","unittest","BO.test_bo_integration"],CST),
        ("cst_pid_reference_suite",[sys.executable,"-B","test_pid_modules.py"],CST),
        ("folder_readmes",[sys.executable,"-B",str(ROOT/"scripts/create_structure.py")],ROOT),
    ]
    results=[]
    for name,cmd,cwd in tasks:
        run=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=90)
        log=run.stdout+run.stderr
        (OUT/f"{name}.txt").write_text(log,encoding="utf-8")
        results.append(dict(name=name,command=cmd,cwd=str(cwd),exit_code=run.returncode,status="passed" if run.returncode==0 else "failed",log=f"{name}.txt"))
        print(f"{name}: {results[-1]['status']}")
    files=sorted([*CST.glob("*.py"),*CST.glob("*.json"),*CST.glob("BO/**/*.py")])
    sources=[]
    graphs=[]
    for path in files:
        item=dict(project="CST",path=path.relative_to(CST).as_posix(),sha256=sha(path))
        if path.suffix==".json":
            data=json.loads(path.read_text(encoding="utf-8-sig"))
            item["top_level_keys"]=sorted(data) if isinstance(data,dict) else None
        sources.append(item)
        if path.suffix==".py" and path.parent==CST:
            try:
                tree=ast.parse(path.read_text(encoding="utf-8-sig"))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node,ast.ClassDef) and any(word in node.name.lower() for word in ("plot","gauge","meter","chart")):
                    graphs.append((path.name,node.name,node.lineno))
    copied=[]
    for path in sorted([*ROOT.glob("source/Engine/**/*"),*ROOT.glob("include/Engine/**/*"),*ROOT.glob("assets/engine/**/*")]):
        if not path.is_file() or path.name=="README.md": continue
        relative=path.relative_to(ROOT).as_posix()
        origin=RI/(relative.replace("assets/engine/","assets/",1) if relative.startswith("assets/engine/") else relative)
        copied.append(dict(destination=relative,source=str(origin.relative_to(ROOT.parent)) if origin.is_file() else "NEW: CST-derived implementation",sha256=sha(path),modified_from_ri=sha(path)!=sha(origin) if origin.is_file() else None))
    audit=dict(cst_root=str(CST),ri_root=str(RI),cst_files=sources,graphics_provenance=copied,scope="Static file inventory and hashes; not full behavior or configuration parity")
    (OUT/"source_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    reused_backend=[]
    for relative in ("source/Controls/ControlSystem/NLAPID.cpp", "include/Controls/ControlSystem/NLAPID.hpp", "source/Python/Data/async_writer.py"):
        original=RI/relative
        destination=ROOT/relative
        reused_backend.append(dict(source_project="RI",source=relative,destination=relative,
                                   source_sha256=sha(original),destination_sha256=sha(destination),
                                   modified=sha(original)!=sha(destination)))
    (OUT/"backend_provenance.json").write_text(json.dumps(reused_backend,indent=2),encoding="utf-8")
    lines=["# CST graph port inventory", "", "Static candidates from outer CST Python files. Some are legacy/demo or container widgets; active imports must be traced before selecting them. C++ must reproduce the selected CST style and behavior, not replace it with RI defaults.", "", "| CST file | Symbol / line | Native port status |", "| --- | --- | --- |"]
    for file,symbol,line in graphs:
        implemented={('pid_ga_control_tab.py','TrendPlot'),('pid_ga_control_tab.py','PIDGainRadar'),('controller_theme.py','TrendPlot'),
                     ('MagneticFieldControllerWindow.py','_ControllerBeamPlot'),('VacuumBeamMonitoringWindow.py','TimeSeriesPlot'),('sqlite_viewer_qt.py','PlotPane')}
        status="Native C++ port used by integrated simulation; full cross-DPI parity pending" if (file,symbol) in implemented else "Pending active-path classification and native port"
        lines.append(f"| `{file}` | `{symbol}` : {line} | {status} |")
    lines += ["", "Selected magnetic/transport/source monitoring graphs now use native hosts in the combined launcher. Calibration curves and embedded TP histories are also native. Vacuum gauge decoration/readouts remain CST Qt UI. Archived web/JavaScript charts are not selected by the launcher. Exact axes, layout, DPI and full chart parity remain acceptance work. A class-name scan is not an exhaustive graph inventory.", ""]
    (ROOT/"docs/GRAPH_PORT_INVENTORY.md").write_text("\n".join(lines),encoding="utf-8")
    report=dict(recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=results,
                passed=sum(r["status"]=="passed" for r in results),failed=sum(r["status"]=="failed" for r in results),
                limitations=["Launcher, controller, monitoring/history/configuration and snapshot screens are integrated in simulation; hardware, operational alarm workflow and CUDA remain pending", "CST PID reference tests are incompatible with current CST controller settings", "CST screenshot reference uses Qt import spelling adaptation to PySide6 in memory", "Full automatic GA/BO runs and Ubuntu runtime remain unverified", "Axes, PDF layout and cross-DPI visual parity remain unverified; CST range/coil bitmask overlap is unresolved"])
    (OUT/"verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return 1 if report["failed"] else 0


if __name__=="__main__": sys.exit(main())
