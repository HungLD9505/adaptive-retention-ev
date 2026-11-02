# Final execution incident and partial handoff

## Receipt-service stop — October 28, 2026 ICT

Final is **incomplete: 170/810 whole units, 2,380/11,340 method cells**. The
remaining **640 units / 8,960 cells** are indices 168, 170, 172–809 in the immutable
lock. Accepted indices are 0–167, 169, 171. All accepted work is UrbanEV: 90 units
at 7 days and 80 at 14 days, covering 56 complete three-seed entity-budget pairs
and two partial pairs. No 28-day or CHARGED Final result is accepted. The
accepted receipts retain 84 null-MAE cells; these are not replaced or omitted.

Training remains commit `61c32328d9829a69037dca629f727b4863015122`, lock v2 SHA256
`9c65169cced1506a450fdd7b8a57a69d5a720cac7acaa0dcd1c8ccfd1723ce42`.
The full frozen cohort, three seeds, 14 methods and 90-day replay remain required.
No accepted Final, Source or Development fit was repeated. No method was tuned
on Final, and this partial collection does not establish effectiveness or
complete the required Final analyses.

The one bounded queue recovery resumed only proven-undispatched tails 148
and 143 after the original parents exited on receipt timeout. Its first eight
accepted units had producer-exit-to-root-credit latency median 43.76 seconds,
maximum 113.78 seconds. That observation covered an actively served coordinator,
not reliable unattended heartbeat service. The failure subsequently recurred:
A parent 87192 exited 1 waiting for unit 166's Root receipt, before dispatch 168.
Unit 166's producer completed all 14 methods with exit 0/no stop reason at
20:58:33.565 UTC; Root credited it at21:02:01.172 UTC, **207.61seconds later**.
The publication listing call spanned 20:58:40.563–21:01:24.733 UTC. These delays
and the actual 180-second queue timeout are verified; scheduler/context service,
native listing visibility and connector latency were not causally isolated.
The nominal one-minute heartbeat did not establish service within the deadline.

No further automatic recovery was attempted. B's pure waiting notebook cell
was interrupted in `time.sleep`, before launching leaf 173; its detached
producer 171 was untouched, finished all 14 methods with exit 0/no stop reason,
and passed fresh external byte/content acceptance. B parent 78561 then exited 0.
Controller 925 was terminated only at acknowledged `waiting_for_actual_quota`,
after its last bounded pass completed at 21:20:40.236 UTC, with no verification or
credit in flight. Both remaining GPU contexts were the notebook kernels only;
both owned allocations were released through normal Colab runtime controls.
Both actual panes showed **Not connected to runtime**. The heartbeat is paused
to prevent repeated automatic retries of this receipt-service blocker.

The last actual resource-pane observation was 61.91 compute units, two sessions,
2.14 units/hour, at 21:15:36 UTC. It predates release; no fresh post-release
balance or quota exhaustion is claimed. Reserve 30 remains unchanged. Full-scope
capacity was never established, and the 640 missing units have no completion-time
promise. Resumption requires a reliable receipt-service mechanism within the
fixed 180-second deadline, fresh quota and exact runtime/input/Source restoration;
the first missing lane boundaries are A168 and B173. Prepared reservations
173–212 and 213–252 are preparation, not execution or acceptance.

The [terminal checkpoint package](https://drive.google.com/file/d/1NbqmUrDUW699BevHozcv0jmST_829b4r/view)
contains the canonical ledger, exact accepted/missing unit identities, 170 receipt
bindings and incident timings. Its 87,525 fresh native bytes passed SHA256
`007ae78f97abc2348b867d0e3f9c0648ac9eceb5adda0bd26cd24d244882555f`, ZIP CRC
and all five exact members at 21:25:50 UTC. This is metadata checkpoint
verification, not a new download of all historical publications. Each unit
retains its original fresh native archive/content acceptance. The terminal
local audit matched all 170 canonical receipt hashes and 131 later separate
exact-identity proof hashes. The 39 earlier units retain their original receipt
layout without the later separate identity file; no such file was fabricated.
See [the compact checkpoint record](issue23-final-stop-checkpoint-20261028.json).

Independent peer approval remains false under the recorded lead exception.
GitHub Actions is billing-blocked, not passed. Original publisher raw archives
were not freshly checked locally during this continuation. No merge, main
promotion or issue closure occurred. This is an incomplete evidence handoff,
not full Final delivery.

Local README checks passed for this documentation handoff: source catalog listing,
406 offline tests, Ruff lint, Ruff format (222 files), and `git diff --check`.
These checks do not establish GPU throughput, research effectiveness or Windows CI.

## Initial JSON report export repair

The first real bounded Final dispatch used commit `2d4b1173cfa01a3e67b5b21d481e4162fc6b012c` and lock v1 SHA256 `4cb39248321bae6ce1ea16589e0f202166476ffaf81c998bfc0a3346bc5e4bdd`. Supervisor PID4390 launched child PID4391 on the observed T4 runtime. The child exited1 after24.012seconds: the first replay completed, but export raised `ValueError: Changed completed run report`. No method publication or whole unit was accepted. The failed output and original lock are retained.

`execute()` returns dataclass tuples in the method descriptor; JSON serialization commits these as arrays. The exporter compared the in-memory tuples with decoded arrays. It now canonicalizes the supplied row through strict JSON serialization before the existing exact report, binding, daily-chain and latest-state checks. A regression fixture exercises tuple/array roundtrip and rejects changed method values.

Lock v2 updates only the exporter code fingerprint and records the superseded lock. Cohort, method configurations, replay length, seeds, Source checkpoints, runtime and authorization remain identical. The technical retry uses a fresh output directory; no outcome was used for selection or tuning. Independent peer approval remains absent under the recorded explicit lead exception. GitHub Actions remains billing-blocked, not passed.
