# Primary-reference check — 12 November 2026

The manuscript has nine scientific references. Papers support the stated precedent;
project losses, thresholds, grids and results require project evidence.

| Reference | Primary locator checked | Supported use and boundary |
|---|---|---|
| UrbanEV, Li et al., Scientific Data 12:523 (2025) | [Publisher](https://www.nature.com/articles/s41597-025-04874-4), [publisher Crossmark record](https://crossmark.crossref.org/dialog/?doi=10.1038%2Fs41597-025-04874-4) | Dataset identity/authors/DOI verified through publisher-indexed text and Crossmark. Direct full article/PDF retrieval hit the publisher identity redirect. No raw archive authentication follows. |
| CHARGED, Guo et al., Scientific Data 12:1254 (2025) | [Publisher PDF](https://www.nature.com/articles/s41597-025-05584-7.pdf) | Dataset identity/authors/DOI and six-city scope verified in publisher-indexed PDF text. Direct fetch hit the publisher identity redirect. The dataset paper's own split does not define this project's split. |
| Cho et al., EMNLP (2014), pp.1724–1734 | [ACL Anthology](https://aclanthology.org/D14-1179/) | GRU provenance. The executed gate convention is attributed separately to PyTorch. |
| PyTorch 2.11 GRU | [Versioned documentation](https://docs.pytorch.org/docs/2.11/generated/torch.nn.GRU.html) | Reset gate after recurrent affine transform explicitly checked against the note and native manuscript equations. |
| Wang et al., TimeXer, NeurIPS 37 (2024) | [Proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/0113ef4642264adc2e6924a3cbbdf532-Abstract-Conference.html) | Patch self-attention, exogenous cross-attention and global tokens. The project adapter's result comes from the benchmark ledger, not the paper. |
| Li, Grandvalet and Davoine, ICML/PMLR 80 (2018), pp.2825–2834 | [PMLR](https://proceedings.mlr.press/v80/li18a.html) | Explicit regularization toward pretrained parameters. Does not justify the project's coordinate-scaled latent penalty or numeric lambda interval. |
| Künsch, Annals of Statistics 17(3) (1989), pp.1217–1241 | [Publisher/DOI](https://doi.org/10.1214/aos/1176347265) | Historical moving-block-bootstrap precedent; bibliographic identity checked. Publisher response exposed only an iframe, so no fresh full-text theorem verification is claimed. Segment length, resample count and decision threshold are executed project choices. No stationary/asymptotic guarantee is claimed for this replay. |
| Luketina et al., ICML/PMLR 48 (2016), pp.2952–2960 | [PMLR](https://proceedings.mlr.press/v48/luketina16.html) | Validation-driven gradients for regularization hyperparameters. Our one-step Adam derivative, A/V rule and numeric bounds are specified by code/configuration; the paper does not establish their EV effectiveness. |
| Herbster and Warmuth, Machine Learning 32 (1998), pp.151–178 | [Author-hosted original paper](https://mwarmuth.bitbucket.io/pubs/J39.pdf) | Loss update followed by share-to-other checked in original equations (3), (4), (6). At two experts, normalization gives w+ = (1−alpha)p + alpha(1−p). This paper includes some unbounded-loss settings; the manuscript does not transfer a regret guarantee to these adapting GRUs and this loss/prediction rule. |

**Verified:** bibliographic identities and the accessible principles above.
**Unknown in this audit:** inaccessible full texts and publisher raw-archive
integrity. These are explicitly outside the fresh saved-output verification.
