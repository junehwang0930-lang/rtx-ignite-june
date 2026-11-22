# Real radar data pipeline

Independent, offline validation and feature engineering for real NRC radar measurements. Phase 2 compares offline BIRD/UAV baselines. Object class is not intent:** this dataset cannot establish whether a UAV is malicious, authorized or threatening.

## Reproduce

Python 3.10+ (validated with Python 3.12). From the repository root:

```powershell
cd "ML Files/real_ml"
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python download_data.py
.venv/Scripts/python preprocess.py
.venv/Scripts/python explore.py
.venv/Scripts/python -m unittest discover -s tests -v
```

For the exact tested dependency set on Python 3.12, install `requirements-lock.txt` instead of `requirements.txt`. The latter pins the direct dependencies; the lock also pins their transitive dependencies. The four real-data integration tests skip when processed outputs are absent; run all commands above to exercise them.

## Validated snapshot results

The complete run imports 81 data files (Demo-0 through Demo-7) plus six provenance/metadata files. It retains **713 unique labeled system tracks**, **367,112 observations**, **51 recording groups** across **9 days**: **492 BIRD, 146 UAV, 63 HUMAN, 12 VEHICLE**. There are 79 output columns: eight provenance/target columns and 71 candidate numerical features.

Fifteen repeated track representations are suppressed. One duplicate metadata annotation collapses; 376 MIXED entries, three UNKNOWN entries, one ambiguous Human/dog track, four labels without measurements and 1,284 unlabeled source tracks are audited and excluded. These are source-entry counts, not additive unique physical-object counts. All 17 unit/integration tests pass against the snapshot. RCS is missing in 1.129% of retained observations and entirely absent for 90 tracks; other retained measurement columns are complete. Class imbalance is 41:1 (BIRD versus VEHICLE).

On macOS/Linux substitute `.venv/bin/python`. Commands work from any working directory because defaults resolve beside each script. Allow several minutes and roughly 1 GB free space for downloads, Python dependencies and parsing. The downloader requires network access on its first run; cached verified downloads and all later stages work offline. It retries transient downloads three times, writes atomically, verifies Git blob SHA-1 and byte length, and repairs corrupt cached files. It does not follow the upstream moving `main` branch.

`download_data.py --raw-dir PATH`, `preprocess.py --raw-dir PATH --processed-dir PATH --reports-dir PATH` and `explore.py --processed-dir PATH --reports-dir PATH` support alternate directories. Use matching paths across stages. Preprocessing verifies the downloaded snapshot before parsing and fails on unexpected schema, label disagreement or corrupt sources. Generated outputs are overwritten when rerunning; retain separate output directories when comparing revisions.

## Source, license and attribution

- [NRC CUAS-sensing-dataset](https://github.com/nrc-cnrc/CUAS-sensing-dataset), release version **1.0.0**, `CITATION.cff` release date **2026-08-08**.
- Immutable revision: [`df3cebae895f4f12d23cd50480dd4c47b09d422e`](https://github.com/nrc-cnrc/CUAS-sensing-dataset/tree/df3cebae895f4f12d23cd50480dd4c47b09d422e).
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Copyright © His Majesty the King in Right of Canada, as represented by the National Research Council of Canada, 2026.
- Attribution: Mehta, V., Bolic, M., Mantegh, I., & Vidal, C. *UAV vs. Bird Radar Tracks Dataset* (2019–2021). National Research Council Canada / University of Ottawa.
- Changes made here: class normalization, validation, exclusions, deduplication and statistical aggregation. Derived reports and tables retain the dataset attribution; no endorsement by NRC is implied.

The downloader preserves `LICENSE`, `CITATION.cff`, `README.md`, `docs/DATA_DICTIONARY.md`, both metadata CSVs, and all 81 measurement files from Demo-0 through Demo-7. `data/raw/download_manifest.json` records paths, revision, source hashes and sizes. Raw and processed data are ignored by Git; only scripts, documentation, tests and modest aggregate reports are committed.

## Architecture and repository inspection

The parent `ML Files/` pipeline generates scenarios (`gen_cases.py`), simulates sensor measurements (`simulate.py`), trains behavior models (`train.py`, `cuas_model.py`) and builds demo/study outputs. Its `features.csv`, case and game-day tables, trained model and performance results are simulated. The site survey uses real OpenStreetMap geometry with estimated heights, not real labeled radar training data. The CAD, coverage viewer and simulation components remain intact. No `AGENTS.md` or pre-existing automated test suite was found when this module was added.

This module imports nothing from the simulation pipeline and does not load its pickle/model. See the [implementation plan](../../docs/superpowers/plans/2026-11-21-real-data-pipeline.md) for scope and decisions.

## Ground truth and track identity

1. Annotated workbooks: first sheet supplies observations; second sheet supplies expert camera-confirmed labels. Read the two annotation columns positionally because some class headers are blank. Verify every annotation against the matching filename/folder in official metadata. Duplicate equal annotations collapse; conflicts fail validation.
2. Curated CSVs: detect comma/semicolon separators, remove trailing empty columns. Crucially, official metadata `system_track_id` values refer to CSV **sensor `id`** values. Verify the exact sensor-ID set and labels, then require the CSV's **SystemTrackID** to match the curated filename. Multiple sensor segments in one system track are aggregated together. Never match the metadata column blindly to CSV SystemTrackID.
3. Canonical identity is `NRC:<recording_session>:<radar_id>:<system_track_id>`. Strip curated suffixes and Demo-7 folder aliases. R1/R2 are separate tracks but share a split group. Demo-1 lacks a published parent recording time, so its entire known day is conservatively one group.
4. Prefer annotated workbooks when a curated extract represents the same system track; otherwise select the lexicographically first source. Audit each suppressed representation. Conflicting labels across representations exclude all candidates. Do not concatenate repeat representations or double-count sensor segments.
5. Exclude MIXED, UNKNOWN, unlabeled, invalid-ID and entirely invalid tracks. Full raw logs are inventoried and their sensor groups recorded separately; radar predictions do not turn them into ground truth. The full-log audit includes some tracks already represented in curated data and is not an additive unique-object count.

`Human/dog` is validated against official HUMAN normalization but excluded from supervision because the raw annotation is ambiguous. A system track is not necessarily a unique physical object across recordings. Ground-truth provenance is expert annotation/curation; radar `UpdatedTrackType`, `TrackExtendedNature`, `probUav`, `probUnknow`, confidence and other classifier-derived fields are excluded by a strict feature allowlist.

## Outputs and feature definitions

`data/processed/tracks.csv` has one row per unique labeled system track. Identity, source and label columns are provenance/target fields, not model inputs. `n_observations` counts retained updates.

Ten documented measurements are used: azimuth/elevation (degrees), range and posX/Y/Z (metres), veloX/Y/Z (metres/second), and RCS (dBsm). For each: mean, population standard deviation (`ddof=0`), minimum, maximum, range, missing fraction and valid observation count. This gives 70 summaries plus observation count; the [feature dictionary](reports/feature_dictionary.csv) explains every output column.

Invalid numerical values become NaN: unparseable/nonfinite values, negative slant range, elevation outside ±90°, azimuth outside ±360°. Signed position/velocity and negative dBsm remain valid. No invented measurements, inferred labels, synthetic training rows, global scaling or imputation. A one-valid-observation standard deviation is zero; all-missing numerical summaries remain NaN. Missing fractions count invalid values too. Linear azimuth statistics require caution near wraparound.

Exact repeated CSV records (including timestamps) are removed. Excel has no timestamps, so identical numerical rows are audited but retained: a stationary track can legitimately repeat a measurement. Curated track duplicates are handled at the identity level. No assumption of independent samples is justified by the nominal 10 Hz update rate.

`reports/` contains the generated [quality report](reports/data_quality_report.md), preprocessing counts, input/exclusion/duplicate/full-log audits, column dictionary, class counts and session coverage, descriptive statistics/correlations, and readable PNG plots. The full-log audit contains identifiers and counts only, not raw radar observations. Unit tests use small validation inputs to exercise error handling; these are never written into the analysis dataset.

## Reproduce the offline comparison

Use Python 3.12 and the pinned requirements-lock.txt. From this directory activate the virtual environment with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1` in Windows PowerShell. With the environment active, run:

```sh
python -m pip install -r requirements-lock.txt
python download_data.py
python preprocess.py
python explore.py
python train.py
python -m unittest discover -s tests -v
```

Training and evaluation run together on the Phase 1 tracks. The command writes metrics and figures to reports/phase2. The presentation summary gives the protocol, measured results, explanation and limitations. The implementation uses scikit-learn for consistent fold-local preprocessing and conventional baseline estimators.

[Research results and presentation summary](reports/presentation_summary.md)
