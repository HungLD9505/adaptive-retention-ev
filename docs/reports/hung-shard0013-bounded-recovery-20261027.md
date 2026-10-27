# Bounded shard13 recovery with completed private Notebook Output

Shard12 independent CPU reconcile version 362686291 passed in 23.9 seconds. It read 452,751,164 bytes with exact SHA `d0f7f0335745843adbf16b5c05aafd7fb7a4505ba13c92ab649849677d9b92dc` and ZIP CRC passed. The observed log is retained locally as `.cache/kaggle-shard12-reconcile-v2-log.txt`; the historical failed Dataset-input readback and claims are preserved.

## Prepared recovery, not completed training

`tools/hung_kaggle_recovery13.py` prepares exactly shard13, carrying the five exact private Dataset archives8–12 into the original group03 absolute base. It preserves model44, runtime plan/partition, original inputs/configurations, job identities, parity and disk/quota guards. Each carried archive is independently SHA/CRC/jobset checked before copying. Unique create-only claims prevent duplicate execution. The CPU launcher requires terminal old failures, successful shard12 reconcile, fresh free GPU quota with one-job estimate plus reserve, then submits one private GPU version. It stops on invalid sources or failure; it never retries a claimed identity.

For this recovery the persistent storage barrier is the private **completed Save & Run All Notebook Output, version1**, followed by an independent CPU VM reading exact canonical receipts/archives for8–13. Dataset publication is not used inside the GPU version, avoiding its asynchronous compression race. Draft saves and upload acknowledgements cannot satisfy this barrier. The CPU child is submitted only after GPU COMPLETE. Its successful readback is required before marking shard13 remotely verified or authorizing successor groups. A bounded three-hour CPU controller does not resubmit on timeout. Groups14+ are not dispatched by this module. Notebook Output version1 must remain private and preserved; independent review/access and long-term archive disposition remain open.

Prepared launcher source SHA `643b5542a7a7c5dea50d3c65532d323dd1d9a27964ef1293b8cdf0513e7c1494`. GPU name `hung-group03-shard13-recovery-20261027-v1`; CPU output proof `hung-group03-shard13-output-readback-20261027-v1`. These are prepared identities until actual SaveKernel/native Save & Run evidence is recorded. No Final labels or method selection.

## Validation and limitations

Offline recovery source guards compile both scripts, require only shard13 in the execution list, original base, all five archive pins, parity/disk/quota checks, exactly two bounded submissions and no next-group relay. Initial source-boundary regression failed closed while the generated module prefix also contained the old template; correction scopes the storage substitution to the emitted GPU execution body. No training or receipts were changed to satisfy a test.

Queue diagnostics commit286d2db passed the full offline suite:375 tests,1skip,exit0,169.041 seconds (wrapper176.053489). This is separate from validation of the new recovery module. Ruff and focused tests pass; a fresh full-suite run will be recorded after the new commit is frozen. Independent peer approval remains pending; this author does not supply independent acceptance. #39 remains open pending explicit substitution approval; full Development coverage and immutable independent Final lock are incomplete.
