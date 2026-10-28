# Hùng Final runner preflight addendum (2026-10-29)

This is a code and synthetic-test milestone. No Final labels were opened and no Final job was launched.

## Exact coverage and aliases

The locked `coverage.variant_seed_policy` names every variant. Only `seasonal_naive` may use a deterministic representative seed; its `alias_seeds` must exactly equal the other declared seed views. These views reuse one physical Seasonal Naive run and are not independent replications. All other variants require one physical job per declared seed. `coverage.missing_cells` must enumerate every genuinely absent selected entity, budget, seed, and variant cell with a reason. City and method shortfalls remain separately declared.

The Development plan maps `without_confidence` to `online_best_lambda` when replay `delta` is zero. Final coverage accepts that single physical run for both labels only with a locked zero `delta`; no separate duplicate job is inferred. `random_target` remains a supported Target initialization and replay route for the no-Source ablation.

## Lock-first input extraction

`python -m experiments.hung_sprint2.final_extract --lock LOCK --lock-sha256 SHA` authenticates the lock, code, ZIP, Source checkpoints, jobset, execution plan, coverage, and analysis before reading ZIP members. It then checks member paths, types, exact selected input-run roots, required files, CRC, and capacity. It creates files only under lock-pinned `data/inputs` paths and refuses any existing destination. After materialization, it verifies the input manifests and Final entity/schedule identities through the full lock validator and writes a create-only file SHA/CRC receipt under ignored `.cache`. An interrupted extraction leaves a partial directory and requires inspection; the command will refuse to overwrite it.

`resources.estimated_output_bytes` is a positive, locked capacity budget for the complete selected extraction and output jobset. Dispatch requires this budget in addition to the 8 GiB minimum reserve before starting; it checks the reserve again at each job boundary. Provider quota and actual disk estimates still require a reviewed resource lock.

The dispatcher status `jobset_complete` means local stages and receipts passed its local readback. Durable Final acceptance additionally requires an immutable archive and independent remote SHA/CRC readback. Those transport and scientific review gates are not implemented by this milestone. Drift's entity-specific reference constants also need a locked, outcome-blind derivation route or an explicit coverage shortfall; no constants should be copied from another entity.
