# source/Python/Data

`async_writer.py` is reused from RI. `cst_schema.py` retains CST's existing table/packet helpers; its original standalone logger function is not started. `simulation_recorder.py` uses those helpers through the RI asynchronous writer. `pid_decision_log.py` is CST's existing diagnostic CSV recorder, with its output redirected to runtime/logs. Further history/PID database adapters remain pending; do not create a competing SQLite writer.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
