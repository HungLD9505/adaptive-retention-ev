# External artifact verification

These 18 checks were previously mixed into default offline discovery. A fresh
checkout reproduced 16 errors and two failures because they require historical
manifests, trained checkpoints, input ZIPs or separately staged pinned source files
under ignored `.cache/` locations. Their assertions, expected numbers and hashes
are preserved here; they are not passing or waived numerical checks.

Default `python -m unittest discover -s tests -v` runs synthetic/offline fixtures.
This directory deliberately has no `__init__.py`, so root discovery does not recurse.
After restoring the exact artifacts required by the referenced audit tools, run:

```sh
python -m unittest discover -s tests/artifact -v
```

Missing or mismatched artifacts must fail that explicit command. Do not download
raw data, train models, fabricate fixtures or update expected hashes to make these
checks pass. The source reports and tool constants retain the historical artifact
paths and identities. These checks were not rerun successfully by integration.
See `docs/reports/external-artifact-test-inventory-20261102.json` for the exact move.
