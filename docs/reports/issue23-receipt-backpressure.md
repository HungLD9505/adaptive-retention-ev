# Issue23 receipt backpressure repair

Refs #23 and the Final delivery in #52. This branch starts from `dev` and adds
only an operational policy/queue plus independent fixtures. It does not modify
models, losses, adaptation, the controller, cohort selection, seeds, inputs,
checkpoint retention or the frozen scientific execution files.

## Verified failure and implemented behavior

The old queue stopped before its next unit when a Root receipt took more than
180 seconds. Unit166 completed all14 methods normally, but Root credit arrived
207.61 seconds after producer exit. The saved queue scripts contain the180-second
timeout; the scientific runner's receipt contract validates identity/content,
not this waiting duration. A fixed short wait incorrectly converted a completed
publication into an operational dead end.

`ReceiptPolicy` now permits a finite, reviewed600-second receipt wait. The queue
keeps **at most one completed unit awaiting Root per lane**: no speculative next
fit starts before the exact predecessor Root receipt has14 method cells and
both independent-content/native-readback flags. Duplicate JSON fields and wrong
types/identity are rejected. Source/execution/lock/operator pins are rechecked
before each unit. An exclusive durable intent precedes `Popen`; existing output,
log, publication, receipt or uncertain prior intent blocks an implicit refit.

Before every producer, an actual quota observation must be at most15 minutes
old. Admission subtracts the observation's elapsed estimated consumption and
reserves30 units plus the aggregate rate times the complete worst-case20-minute
unit,10-minute receipt wait and5-minute allocation-release margin. Actual
observation timestamps/balances remain distinct from the current estimate.
The original20-minute unit cap and120-second no-completed-method deadman remain.
Queue start horizons are finite; failed/partial work and per-run backups remain
preserved. The producer never creates its own Root acceptance.

The coordinating native transport implementation is separately pinned in the
operational envelope. Its two lane loops discover/fetch/verify independently,
and only receipt upload/canonical ledger credit is serialized. A slow listing
on one lane no longer forms a global iteration barrier. The original fresh raw
archive byte/hash/CRC, exact identity, daily/state/initialization/origin checks
and14-method acceptance body are retained. Producer failure is detected even
when no complete ZIP was published. No accepted fit is rerun.

## Bounded hardware measurement

Two complete independent synthetic Development units used the same frozen14
method configurations,90-day replay, synthetic input/CPU-created Source fixtures,
scientific bytes and actual721-package inventory. No real Final values or
accepted Source/Development fits were used for these measurements.

| Hardware | Unit end-to-end seconds | Displayed units/hour | Rate-derived units/unit |
|---|---:|---:|---:|
| Tesla T4 |104.854|1.07|0.03116|
| NVIDIA L4 |107.879|1.54|0.04615|

L4 had no observed time advantage and about48% greater rate-derived unit cost
in this single matched fixture. Production therefore retains T4. These are not
exact account debits, a broad hardware ranking, production async-export timings
or a Final ETA. Two preliminary L4 setup attempts were incomplete (one7-method
censored run and one failed download reference before fitting); neither is
counted as a complete unit. Every probe allocation was released within the
5-minute/0.5-unit session bound. Small bootstraps now obtain a fresh native file
reference per attempt and release the owned allocation even after setup errors.

The matched fresh-session inventories differ at33 package versions from the
original production inventory, including NumPy. This does not qualify the
fresh image for Final. Exact original dependency restoration and the original
721-package/runtime/code/Source/input gates must pass before production resumes.
The old lock and all170 accepted units retain their original provenance.

## Validation and remaining scope

Twelve independent CPU regressions cover measured207-second delay, finite
deadlines, corruption/duplicate fields, missing receipt, failed fit preservation,
exclusive restart admission, wrong operator identity and reserve/freshness gates.
Eight coordinating transport fixtures cover independent progress under a slow
lane, serialized credit, bounded slots, corruption, missing failed publication,
duplicate names, failed upload, accepted restart and reserve admission. These
fixtures establish operational behavior, not research effectiveness.

At the repair boundary Final remains170/810 units (2,380/11,340 cells), with640
units missing. First missing lane boundaries remain A168 and B173. The full
frozen scope and30-unit shared reserve are unchanged. This report does not claim
production resumption, whole-Final analysis, independent peer approval, passing
cloud CI, a merge, main promotion or issue closure.
