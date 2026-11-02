# Hùng Final input transport — independent Kaggle CPU readback

**Observed 29 October 2026, before Final execution.** This proves transport of the bounded Final input package. It does not prove any Final job, Final metric or scientific acceptance.

The executable lock remains SHA-256 `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`, code commit `929480bfb123aaecab2cb9178f0e9088fb4d6593`, with 360 candidate UrbanEV jobs. No cohort, seed, method, threshold or analysis choice changed after lock.

| Provider object | Observed identity and result |
| --- | --- |
| Private input Dataset | [hungluongduc/hung-final-handoff-20261029-e5e8fe1c-bin](https://www.kaggle.com/datasets/hungluongduc/hung-final-handoff-20261029-e5e8fe1c-bin), current version **1**, API status `ready`, 25 exact file names (24 payload + manifest). |
| Frozen handoff manifest | SHA-256 `db7a82308008f66b01844d6a779e77389379556d2de555c00c5c93ccdad3d162`. The original input ZIP SHA `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7` was carried as `inputs.zip.bin`, preventing Kaggle's automatic ZIP expansion. Its overlay target in the manifest remains the exact locked `inputs.zip`. |
| Independent CPU saved version | [hung-final-readback-e5e8fe1c-bin-20261029-v4/1](https://www.kaggle.com/code/hungluongduc/hung-final-readback-e5e8fe1c-bin-20261029-v4), `COMPLETE`, GPU disabled. Pulled metadata names the private Dataset (Kaggle normalizes the source to an unversioned slug); the Dataset's API current version is 1. |
| Saved output | `final-input-readback.json`, 349 bytes, SHA-256 `38fd8466d191c465f4ee0eb13e136b4ffe81d9d06ca3a5900237991b23a6743d`, status `REMOTE_BYTES_VERIFIED_NO_FINAL_EXECUTION`, 24 payload files, exact manifest and lock SHA. Downloaded create-only under `.cache/hung-final-readback-e5e8fe1c-bin-20261029-v4/saved-output-v1/`; local comparison to the expected receipt passed. |

The CPU source locates exactly one mounted manifest by SHA, checks its Dataset identity and exact file-name set, hashes all 24 payload files and compares each size/SHA to that manifest, then checks the lock/code identity. It neither extracts Final labels nor runs a Final job. The submitted LF source SHA-256 is `03a9f75a938ba0bfc4427c0e3b7fd653eeadee925e22b50903d41fbe38b88267`; the provider-pulled source SHA is `83ec3be7556b38257718b26215d0178e0947b46c53ce5907b4614cffe97e5a2e` because Kaggle returned CRLF line endings. The decoded source text is identical.

**Preserved failed attempts:** The first Dataset's `.zip` was automatically expanded by Kaggle. CPU readback v1 lacked the Dataset source because the original OAuth token lacked `datasets.get`; v2 mounted that Dataset but rejected its changed file set. The proposed v3 request used a 52-character slug and received HTTP 400 before a saved version was created; a distinct shorter v4 slug was accepted. None was retried or relabeled as success. A new OAuth grant with `resources.admin:* datasets.get:*` was authenticated to account `hungluongduc`; credentials remain ignored under repository `.cache` and are not in Git.

**Next gate:** Recheck free-tier GPU quota and actual session/output capacity, then submit one lock-bound Final GPU saved version only if the complete exact-jobset preflight passes. Independently download and verify the Final archive, journal, receipt and job→artifact map before claiming any Final result. The 370 other eligible UrbanEV IDs, six CHARGED scopes and scientific reviewer dispositions remain separate open gates.
