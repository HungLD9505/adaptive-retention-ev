# Final execution: JSON report export repair

The first real bounded Final dispatch used commit `2d4b1173cfa01a3e67b5b21d481e4162fc6b012c` and lock v1 SHA256 `4cb39248321bae6ce1ea16589e0f202166476ffaf81c998bfc0a3346bc5e4bdd`. Supervisor PID4390 launched child PID4391 on the observed T4 runtime. The child exited1 after24.012seconds: the first replay completed, but export raised `ValueError: Changed completed run report`. No method publication or whole unit was accepted. The failed output and original lock are retained.

`execute()` returns dataclass tuples in the method descriptor; JSON serialization commits these as arrays. The exporter compared the in-memory tuples with decoded arrays. It now canonicalizes the supplied row through strict JSON serialization before the existing exact report, binding, daily-chain and latest-state checks. A regression fixture exercises tuple/array roundtrip and rejects changed method values.

Lock v2 updates only the exporter code fingerprint and records the superseded lock. Cohort, method configurations, replay length, seeds, Source checkpoints, runtime and authorization remain identical. The technical retry uses a fresh output directory; no outcome was used for selection or tuning. Independent peer approval remains absent under the recorded explicit lead exception. GitHub Actions remains billing-blocked, not passed.
