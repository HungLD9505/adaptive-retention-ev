# Bounded weighting verification record

Candidate execution is registered at `f165552`; all locked candidate source
hashes remain unchanged at the publication head. The stopping gate is false.
No new neural training, new cohort execution or repeated candidate search occurs.

| Check | Observed result |
|---|---|
| Root suite on clean `3570e1f` | 1,077 tests run, 12 skipped, no failures |
| Six new weighting regressions | Passed: exact paper arithmetic, infinite-rate leader change, scale invariance, endpoint behavior and delayed-feedback guards |
| Fixed-adaptation suite | 9 passed |
| Confidence-controller suite | 12 passed |
| Ruff lint / format | Passed; 701 files formatted |
| Source catalogue list | Passed; not fresh publisher validation |
| Release check | Passed; 17 frozen assets and 92 historical pins |
| Candidate protocol / source / code fingerprints | Match registered bytes |
| Fresh old-expert readback | Passed: 108 fast runs, 4,734 rolling updates, 2,628 original feedback updates, 10,656 original arm vectors |
| Independent candidate oracle | 50-digit Decimal arithmetic; all 144 candidate cells matched; max prediction gap 7.20e-14 kWh |
| Native manuscript | 23 pages, eight vector figures, twelve tables, sixteen references; zero raster images |
| Compiler/layout | No overfull boxes, missing glyphs or undefined references; final page renders reviewed |
| Extracted source package | Fresh compile successful; all 23 pages have identical extracted text |
| Claim/evidence/asset hashes | Match both working files and canonical Git blob bytes |
| Diff/language review | Passed; no conversational assistant attribution in maintained article/README |

One new CSV was initially written with CRLF while Git canonicalized it to LF.
Its manifest bindings were corrected to canonical repository bytes in `a08986f`;
no values, code, decisions or scientific outcomes changed. No source ZIP or
manuscript compilation input depends on that CSV representation.

The twelve root skips are eight optional baseline-dependency tests, three CUDA
tests and one environment-specific identified-input preflight. The actual
Development input vectors were independently authenticated by the separate
source readback. No failed fixture or expected hash was changed to obtain a pass.

Large logs, candidate vectors, source ZIP and prior/final PDF attempts remain
under external `runs/issue123-bounded-weighting-20261113-v1`. The Overleaf web UI,
fresh raw publisher archives, physical issuance timing, independent full
retraining and prospective generalization were not exercised.

The source recipe is unchanged; passing implementation checks does not upgrade
the failed Development progression gate or the earlier confirmation result.
GitHub CI and peer approval are separate. No autonomous merge/main update occurs.
