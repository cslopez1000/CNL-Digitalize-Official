# include/Simulation

`SimulationRuntime.hpp` declares immutable simulation frames, timed target plans/status and the native worker API. Implementations belong in source/Simulation. Raw channel values are intentionally separated from engineering display values; CST calibration belongs at that boundary.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
