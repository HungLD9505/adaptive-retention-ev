# Issue #99 Kaggle bundle preflight

This is a packaging procedure, not an upload or a completed T4 pilot. It uses
only the locally audited UrbanEV input ZIP and Source10 seed 42/43/44 ZIPs.
The script refuses an existing destination or a dirty code worktree, so the
Git archive and executed source hashes belong to one exact commit.

After committing the issue #99 code, create a new ignored bundle directory:

```powershell
python -m tools.issue99_kaggle_package create `
  --destination .cache/issue99-kaggle-bundle-NEW `
  --input-zip 'D:\Đồ Án\.cache\sprint2-hung-model\.cache\data-downloads\inputs-urbanev-SZH-v1.zip' `
  --source-directory 'D:\Đồ Án\.cache\issue99-source-duration' `
  --audit docs/reports/issue99-local-audit-v2.json
```

Record the printed **manifest SHA-256** outside the bundle. Kaggle automatically
extracts uploaded ZIPs, including nested ZIPs. Create an outer transport ZIP
that gives each inner ZIP a `.zip.bin` suffix; these bytes stay opaque until
the preflight restores their original names:

```powershell
python -m tools.issue99_kaggle_package wrap `
  --bundle .cache/issue99-kaggle-bundle-NEW `
  --destination .cache/issue99-kaggle-transport-NEW.zip `
  --expected-manifest-sha256 LOCAL_MANIFEST_SHA256
```

Upload the new outer ZIP as a private Kaggle dataset/version. Preserve the local
bundle, transport ZIP and older uploads. In the Kaggle notebook, compare the
locally pinned manifest SHA against the auto-extracted dataset and rehydrate
into two **fresh** paths:

```sh
python /kaggle/input/ISSUE99_DATASET/preflight.py rehydrate \
  --extracted-outer /kaggle/input/ISSUE99_DATASET \
  --bundle-destination /kaggle/working/issue99-NEW-BUNDLE \
  --stage-destination /kaggle/working/issue99-NEW-RUN-ID \
  --expected-manifest-sha256 LOCAL_MANIFEST_SHA256 \
  --require-t4
```

The preflight restores each `.zip.bin` to its exact original `.zip` name and
recomputes SHA-256 of the code archive, input ZIP, all three Source ZIPs and
standalone script. It checks CRC and inner manifest/checkpoint hashes, then
extracts only to a fresh path. It rejects an unsafe ZIP member or a missing T4.
The staged code root contains `.issue99-code-commit` with the verified 40-hex
commit and trailing newline, so the runner can bind its code identity without
a private Git clone. `runtime.json` records Python, platform, package, CUDA and
GPU versions. Include the outer ZIP SHA, manifest SHA and runtime record in the
pilot artifact package. A dataset metadata acknowledgement alone does not prove
that Kaggle read the same bytes; retain the notebook preflight output.

This preflight does not establish GPU quota, scientific validity, scoreability,
or readiness for scored search. The protocol's pilot measurements and finite
search/controller settings must be filled before running that search.
