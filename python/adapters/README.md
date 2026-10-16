# python/adapters

`simulation_bridge.py` provides CST's queue-compatible command/data boundary, background full-rate collection, CST beam-buffer publication and asynchronous recording. `native_sequence.py` reuses CST's sequence views while submitting timed rows to C++ and refreshing progress in Qt. Further hardware/history adapters belong here when those milestones are implemented. Do not start duplicate CST/RI acquisition or logger processes.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
