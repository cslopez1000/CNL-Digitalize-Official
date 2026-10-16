# python/app/monitoring

CST magnetic, transport, source/extraction, vacuum and small-screen views. Display RI snapshots using CST units/ranges.

Implemented: migrated MagneticFieldMonitoringWindow, BeamTransportMonitoringWindow, SourceExtractionMonitoringWindow and VacuumBeamMonitoringWindow. Their layout/receive/scaling callbacks come from CST; graph hosts submit numeric arrays to C++. The vacuum view retains CST's Qt-painted gauge UI while beam/RF trends and embedded logarithmic histories render natively. Application wrappers accept launcher fan-out queues or independent simulation subscriptions and clean up on close. The portrait controller wrapper is under controls/cst. See `docs/LAUNCHER_INTEGRATION.md` for current provenance and limitations.

Status: see the root README and PARITY_CHECKLIST.md for implemented versus pending work. A folder's presence does not mean its migration is complete.
