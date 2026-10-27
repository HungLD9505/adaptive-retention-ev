# Issue23 multiworker Development controls

The coordinator owns acceptance and the canonical ledger. A worker reservation is an immutable complete station/budget/seed unit with all14 methods and pinned original configs, inputs and own-city Sources. Ordered reservations must cover the ledger prefix without overlap. The tested preparer accepts multiple pinned reservations; no fixed two-worker cap is imposed. Actual provider capacity, bounded useful throughput and quota determine concurrency.

At ledger v12 (SHA8244646c4227417830ae5d7c9b9b3c3ea2d72c0288040fce882af900d4e1b3ef),112/231 units are accepted. A06 completed56 cells, external transport/CRC/daily/latest-state/all3Source/within-unit coverage passed, with90 scored days per method in each unit. Frozen v11 reservations remain traceable: B07 is AMS14d/entity110/seed42; C08 is the same entity/budget/seed43. A06's accepted rows remain preserved. Only the coordinator advances the ledger after external raw readback and coverage acceptance.

## Implemented controls and manual limits

The operator enforces the fit deadline and120-second no-completed-run deadman. A slow run is not necessarily hung; this is a predeclared finite-stop policy, and incomplete state/failure evidence is retained. C08 also shares a1200-second staging-through-publication deadline and kills the operator process group if it expires. A07/B07 fit cap is270 seconds on A100. Profiles record actual target environment separately from original Source producer environment; no cross-hardware numerical equivalence is assumed.

The `unit_allowance` and `reserve_units` profile fields are declarations, not live billing enforcement. The existing Goal tracks unfinished work; it does not stop provider billing. The coordinator must read provider balance/rate at allocation, dispatch and publication boundaries, retain30 units, and promptly release the specific GPU runtime after failure or completion when no immediate executable reserved job exists. Provider rates are approximate and aggregate observations cannot be attributed exactly to individual jobs. No automatic UI release or continuously enforced provider-balance watchdog is claimed.

The first B A100 attempt acquired an actual40GB A100 but did not complete staging or execute target fits. Historical T4 mount output was mistakenly treated as current readiness, and editor/run-control delays consumed idle allocation. The approximately14-minute allocation exceeded the1-unit pilot budget at the inferred5.30 units/hour rate. It was released and its historical notebook outputs retained. This is an operational failure, not throughput evidence. A fresh B attempt was prepared completely before allocation; it remounts and authenticates durable artifacts on the actual new VM. It passed bootstrap in66.044 seconds, then dispatched PID2302 after97.470 seconds from its execution clock. Allocation UI overhead and release time are additional costs.

CPU staging is an integrity check and preparation step. Changing accelerator can replace the VM, losing `/content` files and mounts. GPU workers therefore remount Drive and authenticate/restage durable artifacts; old notebook output is historical evidence only. No costly runtime is intentionally kept waiting for a script, review or approval.

## Publication integrity

A06's missing outer `source_epochs` descriptor caused export failure after daily/state checks passed. One CPU packaging repair establishes10 epochs from all three original pinned reports/checkpoints and writes new outputs, preserving the failed export. The maintained preparer now requires the original integer10 and includes it in its reference. No fit was repeated.

The resulting clean Git-history bundle was8267449 bytes. All result ZIPs remained below8MB. Transport permits up to9MB specifically for `code.bundle`, with exact SHA/bytes validation; result ZIP bound stays8MB. This transport-only correction publishes the unchanged verified export. External restoration, daily inputs, latest states and original Sources passed before acceptance. Historical artifacts, failures and prior catalogs remain preserved.

No raw archive was freshly downloaded/checked for this coordination change. Existing authenticated processed input archives and immutable Source artifacts were checked. Routine offline tests run without raw downloads or training.391 tests passed; Ruff lint and format checks passed for200 files. These tests establish implementation checks, not research effectiveness. Development remains active; human acceptance and Final execution are separate gates.
