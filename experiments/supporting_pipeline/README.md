# Supporting forecasting pipeline

An alternate end-to-end GRU, source-retention, prequential replay, baseline and
evaluation implementation. Settings and bounded results are separate from the
primary root `ev_*` packages; numerical scores must not be pooled across them.

Current module entry point:

```sh
python -m experiments.supporting_pipeline.cli --help
```

The package contains model/training, controller, replay/state, dispatch, transport
and artifact-verification modules. Configuration and source/runtime identities
are checked before execution. Renaming the package does not authorize new runs or
make historical locks valid for a changed source checkout.

The 48 notebooks retain their original saved-source bytes and may refer to legacy
paths. Use their identified historical checkout for exact reproduction. See the
[experiment directory guide](../README.md#historical-reproduction) for retained
source identity and import compatibility.
