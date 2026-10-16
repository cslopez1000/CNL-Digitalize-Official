"""Create/document Combination's migration layout; leave existing code intact."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {
    "source": "RI backend implementation tree. Preserve native/Python module boundaries; CST defines all conflicting behavior.",
    "source/Bindings": "C++ pybind11 boundary. ChartBindings.cpp currently exposes the standalone CombinationCharts renderer. Port RI control bindings later; avoid UI policy in bindings.",
    "source/Controls": "Port RI native control infrastructure here and implement CST packet, bounds, arming and mode behavior.",
    "source/Controls/ControlSystem": "RI native PID engines adapted/tested against CST pid_controller.py; keep one active controller per actuator.",
    "source/Controls/Network": "RI ZMQProtocol/receiver/sender/server, adapted to CST zmq_rep_server.py and beam_range.py packet bytes and timestamp semantics.",
    "source/Controls/Transport": "RI ServerTransport and SimulatorTransport. Acquisition must supply full-rate CST beam samples before display decimation.",
    "source/Controls/Service": "RI ControlService and CommandGateway. Enforce CST command/ownership semantics; do not introduce conflicting RI limits.",
    "source/Controls/Sequencer": "RI sequence validator/runner adapted to CST sequence_control_tab.py and multi_tc_sequence_tab.py behavior.",
    "source/Simulation": "RI CyclotronModel and deterministic simulation fixtures for CST parity tests. No hardware dependency in basic tests.",
    "source/Cuda": "Optional future numeric kernels with reference CPU paths. RI CUDA was a placeholder; no completed CUDA acceleration is claimed.",
    "source/Python": "RI Python backend package hierarchy. Keep view code under python/app; extract CST workflow logic into these services.",
    "source/Python/Data": "RI async_writer, telemetry_database, pid_database and schemas. Add CST decision fields and lossless history/export mapping; SQL stays off the Qt thread.",
    "source/Python/Services": "RI service infrastructure implementing CST beam_cal, scaling, alarm and settings behavior/configuration. CST wins all conflicts.",
    "source/Python/Control": "RI NLAPID/CPU adapters plus CST beam_sample_buffer.py and extracted pid_cycle_service.py. Preserve fresh windows, response waits and baseline policy.",
    "source/Python/Automation": "RI automation/recovery infrastructure plus CST BO trial lifecycle ports. Preserve CST search, recovery, validation and explicit apply rules.",
    "source/Python/Optimization": "Single RI optimizer library; keep CST behavior for conflicting tuning settings. Do not duplicate CST BO/optimization, which was ported from RI.",
    "source/Python/PID_Tuner": "RI tuning backend modules still needed after tracing imports. No second control loop; CST tuning semantics take precedence.",
    "source/Python/AI": "Optional RI AI backend modules when referenced; keep additions isolated from CST control/settings behavior.",
    "source/Python/DataExploration": "RI offline exploration and data analysis services. Query via independent readers; export using CST contracts.",
    "source/Python/Simulator": "RI simulator modes adapted to CST channels/ranges/calibration and protocol fixtures.",
    "include": "Public native headers matching source hierarchy. Engine headers have been copied; control/simulation headers remain migration placeholders.",
    "include/Controls": "RI public native control headers; preserve namespace/interfaces while adapting implementation to CST.",
    "include/Controls/ControlSystem": "Native PID/control interfaces with explicit units/timestamps matching CST.",
    "include/Controls/Network": "Public protocol/message types documenting CST packet widths, masks, ranges and channel order.",
    "include/Controls/Transport": "Transport interfaces, immutable snapshots and lifecycle contracts from RI.",
    "include/Controls/Service": "Command/service interfaces including CST arming and mode ownership requirements.",
    "include/Controls/Sequencer": "Public sequence validation/execution types supporting CST single and multi-TC workflows.",
    "include/Simulation": "RI simulation headers and deterministic test hooks; implementations belong in source/Simulation.",
    "python": "Python application layer: startup, adapters and CST views. C++ owns graph numeric preparation and OpenGL drawing.",
    "python/application": "NEW bootstrap.py, runtime.py and paths.py. Start one RI runtime, resolve absolute resource paths and coordinate shutdown.",
    "python/adapters": "NEW telemetry/command/database/plot/sequence adapters and CST-compatible controller context. Adapt RI to CST semantics without duplicate workers.",
    "python/app": "Views derived from outer Control System Tune. Port PyQt6 APIs to PySide6 while preserving CST layout, assets and interactions.",
    "python/app/shell": "CST main_control_gui.py and selected gui_window.py shell behavior. No RI visual shell substitution.",
    "python/app/monitoring": "CST magnetic, transport, source/extraction, vacuum and small-screen views. Display RI snapshots using CST units/ranges.",
    "python/app/controls": "CST controller shell/manual/PID/GA/BO/sequence views. Backend services own execution, not view timers.",
    "python/app/configuration": "CST alarm/settings/scaling/calibration editors. CST files/keys/defaults remain authoritative.",
    "python/app/history": "CST SQLite viewer, report and snapshot dialogs using RI asynchronous storage adapters with CST results/export formats.",
    "python/app/widgets": "CstTrendWidget.py currently hosts the C++ CST trend renderer. Port other CST meters/plots here; Python owns Qt lifetime, not graph drawing.",
    "python/app/theme": "Port CST controller_theme.py and neon_style.py; keep CST color/font/style authority. Avoid applying RI chart palette.",
    "assets": "Keep CST visual resources in ui/ and native RI engine resources in engine/. Resolve paths independently of current working directory.",
    "assets/ui": "Referenced CST icons/backgrounds/video/static JS. Copy selected assets during view migration; do not copy unused variants or historical records.",
    "assets/engine": "Copied RI fonts/shaders. primitive2d shaders now support CST measured-response gradient stops; shaders require OpenGL 4.6 core.",
    "config": "CST defaults and reviewed effective configuration go here during migration. Trace actual CST loaders first; no RI overrides or live DB files.",
    "external": "Dependency location reserved for pinned RI GLAD/GLM/GLFW metadata. Current CMake reuses sibling RI external/ via COMBINATION_REFERENCE_ROOT; no vendor copies yet.",
    "cmake": "Future pinned dependency/CUDA discovery helpers; root CMake currently builds the independent graphics library/module/tests only.",
    "scripts": "Repeatable scaffolding and audit utilities. create_structure.py writes missing folder READMEs without replacing code.",
    "tests": "Evidence-based verification. Passing reference tests does not prove the not-yet-merged application's parity.",
    "tests/native": "CPU C++ model/text tests and mocked GL buffer regression test; separate actual GL rendering validation from mocked checks.",
    "tests/python": "Differential tests executing actual CST numeric methods against C++ model; no PyQt6 import required.",
    "tests/integration": "Offscreen GL/context tests and future full-app CST/Combination telemetry-command-record replay comparisons.",
    "docs": "Source audit, graph contracts, provenance and migration/evidence reports. Keep unresolved checklist items explicit.",
    "docs/evidence": "Machine-readable audit and test outputs with source hashes and commands. Generated evidence is not a parity claim beyond its stated scope.",
    "runtime": "Generated application data only. Preserve originals during import; ignored in version control except explanatory README files.",
    "runtime/databases": "Telemetry/PID databases and SQLite sidecars at runtime. Do not check in active DB/WAL/SHM files.",
    "runtime/logs": "Runtime/decision/diagnostic logs with CST fields and visible error reporting.",
    "runtime/snapshots": "CST-compatible saved snapshots/workbooks; recall routes through the single backend command gateway.",
    "runtime/exports": "CST-compatible CSV/XLSX/PDF and BO trial exports generated from backend readers.",
    "build": "Generated CMake/MSVC outputs and CombinationCharts extension; no application source. Reconfigure/rebuild rather than edit artifacts.",
}


def main():
    for relative in FOLDERS:
        (ROOT / relative).mkdir(parents=True, exist_ok=True)
    # Include copied Engine/header/resource subdirectories and generated build
    # directories too, fulfilling the README-in-every-directory requirement.
    for directory in sorted(p for p in ROOT.rglob("*") if p.is_dir()):
        relative = directory.relative_to(ROOT).as_posix()
        readme = directory / "README.md"
        if readme.exists():
            continue
        description = FOLDERS.get(relative)
        if description is None:
            if relative.startswith("build/"):
                description = "Generated compiler/CMake artifacts. No handwritten source belongs here; this directory may be regenerated."
            elif relative.startswith(("source/Engine/", "include/Engine/")):
                kind = "implementation" if relative.startswith("source/") else "public headers"
                description = f"RI Engine {kind} for {directory.name}. Preserve reusable infrastructure, with CST graph appearance and semantics. New CstTrend* files implement CST trend behavior; legacy chart classes are not evidence of CST visual parity."
            elif relative.startswith("assets/engine/"):
                description = f"Native {directory.name} resources copied from RI. CST graph style is authoritative; retain required font licenses and shader sources."
            else:
                description = f"{directory.name} implementation/resources for its parent module; follow the parent README and root CST conflict policy."
        readme.write_text(f"# {relative}\n\n{description}\n\nStatus: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.\n", encoding="utf-8")
    missing = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_dir() and not (p / "README.md").is_file()]
    if missing:
        raise RuntimeError(f"Undocumented directories: {missing}")
    print(f"All {sum(p.is_dir() for p in ROOT.rglob('*')) + 1} directories have README.md files")


if __name__ == "__main__":
    main()
