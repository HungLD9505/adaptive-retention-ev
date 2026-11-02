# Actual provider readback and cross-version verification — 2026-10-27

The [private CPU verifier version 362614432](https://www.kaggle.com/code/hungluongduc/hung-provider-cpu-readback-20261027-v1?scriptVersionId=362614432)
finished successfully in 73.4 seconds, with accelerator **None**. This supersedes
the pending storage/cross-version checks in the earlier
[provider execution snapshot](hung-provider-execution-20261027.md) for this pilot only.

The verifier read the persisted
[private local-pilot Dataset](https://www.kaggle.com/datasets/hungluongduc/hung-local-pilot-readback-20261027-v1)
from a different provider machine. The archive matched exactly: 101,854,497 bytes,
SHA `c567611587a247a29ba72ad01cfe700c8296c2609126d117a634609c5c26e833`,
485 unique safe members, six job receipts and every member's CRC passed.
The mounted remote readback took 3.906668 seconds. This verifies storage bytes;
it is not an independent teammate review or a download back to the local machine.
The earlier separate local CPU verifier already authenticated the pilot's stage
receipts and dependencies (exit 0). Model/metric acceptance remains separate.

The same two permitted initial Development examples, canonical Source/Target
checkpoint bytes and frozen tolerances (`atol=1e-5, rtol=1e-4`) were used for
cross-version comparison. The Torch 2.8 CPU reference archive SHA was
`10f4cee9ef8afcda2a27024136f08a9480ffc7116cec02f7215564cafca0ebf5`.
Torch `2.11.0+cpu` passed all 28 forward/latent/loss/gradient/one-Adam-update
comparisons against `2.8.0+cu126` CPU results. Maximum absolute difference was
`9.313225746154785e-8`. The T4 execution version separately passed its 28 CPU/CUDA
checks on `2.11.0+cu128`. These bounded probes do not establish full-trajectory,
controller-trace or research-performance equivalence.

[Evidence JSON](evidence/hung-provider-readback-20261027.json) preserves all
reported comparisons and the SHA of the visible provider-log capture. Large
inputs, reference tensors, checkpoints and forecasts remain outside Git.
The verifier produced its normal environment/export output; provider output
has not been downloaded locally in this phase. No further training job was
executed by the CPU verifier. Independent peer acceptance, Block-7 reconciliation,
#39 substitution decision, remaining Development work and the Final lock remain
pending. The two bounded training shards retain their separate live/terminal
states; this verifier does not certify their completion.
