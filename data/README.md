# Data sources — acquire raw archives for the new pipeline

The reference catalog is [sources.json](sources.json). It records download URLs, releases, local paths, byte sizes, SHA-256 hashes, and publisher checksums where available. Values were copied from the [historical acquisition manifest](https://github.com/HungLD9505/adaptive-retention-ev/blob/528680dd73791322ed12f32b2c72a3b58618a428/reports/data/acquisition_20261002_03/source_manifest.json), dated 2026-10-02.

**Real archives were not downloaded or reverified in this foundation task.** SHA-256 values are fingerprints recorded by the team during the earlier acquisition, not publisher-provided SHA-256 hashes. The manifest also records the publisher's MD5 for CHARGED. The `list` command reads the catalog; it does not verify current URL availability.

## Which archives are needed?

| Source ID | Archive | Recorded bytes | Required? |
|---|---|---:|---|
| `urbanev-main` | `UrbanEVDataset.zip` from the official Drive mirror | 647,305,188 | Yes, for UrbanEV |
| `urbanev-supplemental` | `UrbanEVSupplemental.zip` | 6,052,188 | No; weather/POI features are not enabled by default |
| `charged-hourly` | Standard `Hourly.zip`, Zenodo record 15814263 | 268,720,500 | Yes, for CHARGED |

Official sources: [UrbanEV repository](https://github.com/IntelligentSystemsLab/UrbanEV), [CHARGED Zenodo release](https://zenodo.org/records/15814263), [CHARGED repository](https://github.com/IntelligentSystemsLab/CHARGED).

## Download and verify

1. From the repository root, list the URLs and required local paths:

   ```sh
   python -m tools.sources list
   ```

2. If the team still has the original raw archives, copy their bytes unchanged to the correct paths. Otherwise, open the catalog URLs to download from the providers. Verify existing files before considering a replacement; do not overwrite them. Drive downloads may require browser interaction. If a link expires, consult the official source and record evidence; do not silently change releases or hashes.

   ```text
   data/raw/urbanev/official_2026_05_11/UrbanEVDataset.zip
   data/raw/urbanev/official_2026_05_11/UrbanEVSupplemental.zip  # optional
   data/raw/charged/zenodo_15814263/Hourly.zip
   ```

3. Verify the recorded size, SHA-256, and publisher checksum:

   ```sh
   python -m tools.sources verify --dataset urbanev
   python -m tools.sources verify --dataset charged
   ```

   Without a dataset argument, both required archives are checked. Add `--include-optional` to check the supplemental archive as well; a missing supplemental file then also returns failure.

   Data may live on another drive with the same `data/raw/` structure:

   ```sh
   python -m tools.sources verify --root /path/to/storage-root
   ```

4. Exit code **0** means all selected files match; **1** means files are missing or have incorrect sizes/checksums; **2** means an invalid catalog/path or a read error. The tool only reads: it does not download, extract, modify, quarantine, or replace raw files. Preserve checksum failures separately for investigation; never change an expected hash just to obtain PASS.

Only use `verify --include-optional` when you intend to acquire the supplemental archive. CI checks the catalog and synthetic fixtures; it does not download hundreds of MB of data.

## Raw, processed data, and inputs

- **Raw:** original archive bytes received from the publisher, preserved outside Git as traceable inputs.
- **Processed:** outputs produced by the new pipeline, which is not implemented yet.
- **Inputs:** splits/scalers/windows/tensors produced by the next phase, not implemented in the new foundation yet.

"Raw" does not imply every value is an unprocessed physical observation. UrbanEV station volume is estimated/derived, and the archive includes raw and processed variants. CHARGED Hourly has already been processed by its publisher. A checksum match confirms recorded bytes, not upstream causality, completeness, or suitability for modeling.

The new pipeline must audit target/unit definitions, schema, time/bin/availability, missing/zero treatment, and reproducibility before handoff. Do not replace station-level data with zone-level data; a CHARGED site is a charger cluster. Do not claim Shenzhen is an independent external dataset without mapping/evidence. Strict online readiness remains unverified.

## Historical sources

Code and reports from before the reset remain on [backup branch `master`](https://github.com/HungLD9505/adaptive-retention-ev/tree/master). Historical manifests document the earlier acquisition, not successful execution of the new pipeline. A different release requires a reviewed catalog PR with provenance and protocol implications; do not adjust this catalog to match an arbitrary file.
