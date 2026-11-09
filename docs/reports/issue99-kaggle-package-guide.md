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

Record the printed **manifest SHA-256** outside the bundle. Upload the complete
bundle as a new private Kaggle dataset/version; preserve the local bundle and
all older uploads. In the Kaggle notebook, compare that local SHA against the
mounted dataset before extraction:

```sh
python /kaggle/input/ISSUE99_DATASET/preflight.py verify \
  --bundle /kaggle/input/ISSUE99_DATASET \
  --expected-manifest-sha256 LOCAL_MANIFEST_SHA256
python /kaggle/input/ISSUE99_DATASET/preflight.py stage \
  --bundle /kaggle/input/ISSUE99_DATASET \
  --expected-manifest-sha256 LOCAL_MANIFEST_SHA256 \
  --destination /kaggle/working/issue99-NEW-RUN-ID \
  --require-t4
```

The preflight recomputes SHA-256 of the code archive, input ZIP, all three
Source ZIPs and standalone script, checks CRC and inner manifest/checkpoint
hashes, then extracts only to a fresh path. It rejects an unsafe ZIP member or
a missing T4. The new stage records Python, platform, package, CUDA and GPU
versions in `runtime.json`. Include the manifest SHA and `runtime.json` in the
pilot artifact package. A dataset metadata acknowledgement alone does not prove
that Kaggle read the same bytes; retain the notebook output from `verify`.

This preflight does not establish GPU quota, scientific validity, scoreability,
or readiness for scored search. The protocol's pilot measurements and finite
search/controller settings must be filled before running that search.
