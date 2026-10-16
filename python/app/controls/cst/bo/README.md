# Reused CST BO views and adapter

CST's existing BO view, PID adapter and recovery gate are ported here. The sole optimizer implementation is in `source/Python/Optimization/bo`. Package imports changed; tuning/recovery/validation policy remains CST's.

The page loads without optional Torch/BoTorch/GPyTorch dependencies and reports missing packages before starting. Migrated adapter/scheduler reference tests are included; complete real fitting/search/validation runs remain pending.
