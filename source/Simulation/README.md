# source/Simulation

`SimulationRuntime.cpp` implements the current simulation-only native worker, bounded full-rate packets, raw channel response, selected CST beam calibration and timed single/multi-channel rows. Its worker/lifecycle design comes from RI SimulatorTransport; CST semantics govern the integration. No network/hardware API is exposed.

An identified cyclotron plant may be added later. The current functional plant and its units are documented in `docs/INTEGRATED_SIMULATION.md`.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
