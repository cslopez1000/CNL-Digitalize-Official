# Remaining features and launch modes

Reviewed 2026-10-16 against the active Combination entry point, CST controller
construction, BO dependency gate and existing implementation evidence. This is
not an exhaustive runtime parity certification. CST remains the authority for
UI, ranges, scaling, safety settings and workflow conflicts.

## Run modes

From Combination on Windows:

```powershell
.\scripts\run.ps1 -Simulation
.\scripts\run.ps1 -Simulation --controller
.\scripts\run.ps1 -ZMQ
```

Simulation is the default. The last command currently exits with a clear error:
the integrated ZMQ backend is unfinished. Recognizing a flag does not implement
the transport. The original RI application supports `main.py -ZMQ`; these scripts
do not launch that different UI. Ubuntu supports `bash scripts/run_ubuntu.sh
-Simulation` and `-ZMQ` through the same application argument parser.

## Bayesian optimization

The migrated CST BO view exists. Open **Field Ctrl**, select **Magnetic**, then
the controller's **BO + PID** tab. `--controller` opens the controller directly.
The view is constructed in `python/app/controls/cst/MagneticFieldControllerWindow.py`.
Its tab can require horizontal navigation in the portrait layout.

The current Combination virtual environment lacks **torch, botorch and gpytorch**
at this review. Install the optional packages with:

```powershell
.\scripts\install.ps1 -Dependencies Optimization
```

Ubuntu: `bash scripts/install_ubuntu.sh --optimization`.
The BO page requires PID output arming and its own BO arming. It reuses CST's
search, recovery, validation and explicit apply workflow with RI optimizer code.
BO now has an independent **Trial duration (s)** field (default 30 seconds).
It controls scored time, excluding shared warm-up and recovery. Validation uses
the greater of this duration and CST's 60-second minimum. GA's scored interval
is unchanged. This is an explicitly requested change from CST's shared duration.
Reference tests pass, but actual complete model-fitting/search/recovery/stop/
validation/apply runs have not been accepted. Do not count BO as fully complete.

## Outstanding work

| Area | Current limitation / remaining work |
| --- | --- |
| ZMQ / hardware | Connect the CST application to RI transport and gateway; verify packet mapping, commands, ownership, reconnects and shutdown against hardware fixtures. |
| Beam ranges | Resolve differing range-index/bitmask interpretations within CST using protocol fixtures before hardware acceptance; preserve CST requirements. |
| Automatic tuning | Complete end-to-end GA and BO simulation runs, including stop, recovery, validation and apply. Optional BO dependencies are absent locally. |
| Alarms | Settings and activation UI exist; telemetry feeding and operational annunciation remain unwired. |
| Subsystem control pages | Source/extraction, vacuum/beam and RF controller pages contain inherited CST placeholders. Their monitoring screens exist. |
| Snapshot recall | TC-only magnetic recall is connected. Source/extraction/transport apply actions are inherited unwired CST actions. |
| Native/CUDA scope | Active charts, simulation PID and sequence execution use C++; optimization orchestration remains Python. CUDA execution is unfinished. |
| Graph acceptance | Complete chart-by-chart visual/DPI/interaction comparisons and throughput profiling. Native PDF charts are rasterized, unlike the original vector output. |
| RI-only capabilities | Hybrid PID/cruise automation, hardware profiles, surrogate/response plots, monitor assignments and FPS UI need explicit retention/exposure decisions using CST styling. |
| Data/config acceptance | Complete protocol, recording/export, configuration migration and calibration acceptance across both sources. |
| Platform verification | Test Ubuntu and clean installation. Existing Windows build/import and desktop checks do not establish cross-platform acceptance. |
| Reference test defect | Original CST PID tests still use obsolete `trend_tolerance`; fix the reference mismatch without changing CST production semantics just to pass it. |

See IMPLEMENTATION_STATUS.md, PARITY_CHECKLIST.md and LAUNCHER_INTEGRATION.md
for evidence and scoped completion claims. Features inherited unfinished from
CST are distinguished above from unfinished Combination integration work.
