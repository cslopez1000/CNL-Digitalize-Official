# BO numerical modules

The existing CST `BO/optimization` implementation is reused here as a single package. CST originally obtained these numerical modules from RI. Keep one optimizer implementation; do not copy another duplicate into the UI package.

Only import paths changed. Model fitting/proposal work retains the existing background-worker behavior. Optional dependencies are in `requirements-optimization.txt`.
