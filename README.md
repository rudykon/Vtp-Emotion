**English** | [中文](README_zh.md)

# Low-MAE EEG–fNIRS Continuous Affect Regression for New Viewers of Familiar Videos

This project studies continuous valence–arousal regression from synchronized EEG and fNIRS signals. Its primary objective is explicit: reduce the mean absolute error (MAE) when predicting the affective responses of new viewers watching familiar, temporally aligned videos. In this setting, population-level affect trajectories learned from training participants have several direct uses:

- estimating the approximate affect trajectory of viewers watching a known video;
- providing a population-response baseline for video editing, advertising, or content recommendation;
- providing a coarse initialization for affect prediction in a new viewer.

These uses are application motivations; the project has not yet validated downstream effects on editing, advertising, or recommendation. Video identity and playback time are readily available at inference, making a fold-wise video–time prior a simple, low-cost, and effective way to reduce MAE. Fixed fusion combines this prior with the EEG–fNIRS branch to obtain the lowest overall MAE. Figure 1 summarizes the framework.

<p align="center">
  <a href="docs/figures/method_overview.pdf">
    <img src="docs/figures/method_overview.png" alt="Overview of the video–time prior and EEG–fNIRS fixed-fusion framework" width="100%">
  </a>
</p>
<p align="center"><em>Figure 1 | Low-MAE continuous affect regression for new viewers of familiar videos.</em></p>

## Primary MAE results

Five-fold participant-held-out evaluation covered 24 participants, 15 familiar videos, and 36,864 one-second samples:

| Prediction source | Overall MAE |
| --- | ---: |
| EEG–fNIRS branch | 47.35 |
| Fold-wise video–time prior | 29.06 |
| **Fixed fusion** | **29.01** |

Fixed fusion achieved the lowest MAE. The low-cost video–time prior alone was only 0.05 points higher and reduced MAE by 18.29 points relative to the EEG–fNIRS branch. Figure 2 shows the internal source decomposition.

<p align="center">
  <a href="docs/figures/source_dominance.png">
    <img src="docs/figures/source_dominance.png" alt="Internal participant-held-out MAE and source decomposition" width="55%">
  </a>
</p>
<p align="center"><em>Figure 2 | Internal participant-held-out MAE. The video–time prior accounts for most of the error reduction, while fixed fusion achieves the lowest value.</em></p>

The participant-disjoint held-out evaluation included 4 new viewers, 60 trials, and 6,143 one-second samples:

| Prediction source | Overall MAE |
| --- | ---: |
| Global constant | 44.33 |
| Video identity prior | 33.36 |
| Video–time prior | 28.04 |
| EEG–fNIRS branch | 42.75 |
| **Fixed fusion** | **27.72** |

Fixed fusion again achieved the lowest MAE and improved on the video–time prior by a further 0.32 points. The central finding is therefore that, for new viewers of familiar videos, the video–time prior provides a strong and inexpensive population baseline. Under fixed fusion, the current EEG–fNIRS branch prediction is associated with a smaller descriptive adjustment. This protocol establishes participant disjointness only. It is not independent cross-site or cross-condition external validation, and it does not evaluate unseen videos.

Figure 3 shows prediction quality in the participant-disjoint held-out cohort.

<p align="center">
  <a href="docs/figures/external_prediction_quality.png">
    <img src="docs/figures/external_prediction_quality.png" alt="Hexbin densities of fixed-fusion predictions versus observed targets in the held-out cohort" width="100%">
  </a>
</p>
<p align="center"><em>Figure 3 | Fixed-fusion predictions versus observed targets in the participant-disjoint held-out cohort. Predictions in both dimensions contract toward the middle of the scale.</em></p>

## Analysis after achieving low MAE

Comparisons among the EEG–fNIRS branch, video identity prior, video–time prior, and fixed fusion are treated as explanatory analyses after establishing the primary MAE result. They show that:

- the fold-wise video–time prior accounts for approximately 99.7% of the internal MAE reduction from the EEG–fNIRS branch to fixed fusion;
- in the held-out evaluation, video identity is associated with a 10.97-point reduction in overall MAE, and adding within-video time is associated with a further descriptive reduction of 5.32 points;
- fusion gains are heterogeneous, improving performance for 3 of 4 participants and 9 of 15 videos;
- the advantage of the temporal prior is phase dependent: in the first normalized time bin, the video identity and video–time priors achieve MAEs of 45.53 and 13.40, respectively, whereas the video identity prior is slightly better in each of the final five bins.

These comparisons explain the source and limits of the lowest MAE rather than replacing MAE reduction as the primary objective. The current conclusion applies only to new viewers watching familiar videos and does not establish transfer to unseen videos. Figures 4 and 5 show the held-out-cohort source decomposition and video-by-time error structure. Detailed methods and results are available in [`docs/method.md`](docs/method.md) and [`docs/ablation.md`](docs/ablation.md).

<p align="center">
  <a href="docs/figures/external_source_decomposition.png">
    <img src="docs/figures/external_source_decomposition.png" alt="Held-out-cohort MAE source decomposition and heterogeneity across participants, videos, and time" width="100%">
  </a>
</p>
<p align="center"><em>Figure 4 | Held-out-cohort MAE source decomposition. The aggregate improvement contains local gains and losses across participants, videos, and playback time.</em></p>

<p align="center">
  <a href="docs/figures/external_video_time_mae.png">
    <img src="docs/figures/external_video_time_mae.png" alt="Video-by-normalized-time MAE heatmaps for the video–time prior and fixed fusion" width="100%">
  </a>
</p>
<p align="center"><em>Figure 5 | Held-out-cohort video-by-normalized-time MAE. The small aggregate fusion gain is not uniform across grid cells.</em></p>

## Repository structure

- `src/merps/`: feature extraction, the video–time prior, physiological modeling, calibration utilities, and inference code.
- `scripts/`: training, participant-held-out evaluation, held-out cohort evaluation, data download, model-bundle export, and local validation scripts.
- `tests/`: unit tests for source construction, metrics, calibration, and model-bundle configuration.
- `docs/`: English documentation for the method, data, and post-result ablation analyses.
- `data/`: local research data, held-out evaluation data, and feature caches; none are version controlled.
- `checkpoints/`: local physiological-model checkpoints and video–time priors; not version controlled.
- `artifacts/`: training logs, evaluation outputs, model bundles, and end-to-end audit outputs; not version controlled.

## Environment setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
```

Python is used for training, evaluation, model-bundle export, and inference. If downloads pass through a SOCKS proxy, `socksio` in `requirements.txt` supplies the required network dependency.

## Data preparation

The training and validation data are expected at:

```text
data/MER_PS_trainval/
```

The participant-disjoint held-out evaluation data are expected at:

```text
data/download/MER_PS_public_evaluation/
```

After setting the repository identifier supplied by the data provider, download the held-out data with the local `huggingface_token.json` file:

```bash
MERPS_EXTERNAL_REPO_ID='<external-dataset-repository-id>' \
  bash scripts/download_external_data.sh
```

Token files are excluded by `.gitignore`. The script reads the token but does not write it to the download directory, logs, or version control. See [`data/DATASET.md`](data/DATASET.md) and [`docs/dataset.md`](docs/dataset.md) for the full data structure and validation results. The supplementary diagnostic below summarizes label coverage and video–time variation in the held-out cohort.

<p align="center">
  <a href="docs/figures/external_data_landscape.png">
    <img src="docs/figures/external_data_landscape.png" alt="Diagnostic view of held-out-cohort label coverage and video–time variation" width="100%">
  </a>
</p>
<p align="center"><em>Supplementary diagnostic | Held-out-cohort valence–arousal coverage and descriptive variation across videos and normalized playback time.</em></p>

## End-to-end workflow

The commands below cover feature preparation, fixed-split training, five-fold training, MAE evaluation and source decomposition, held-out cohort evaluation, model-bundle export, and end-to-end inference. Full training uses a GPU and can take substantial time. Add `--test-mode` to the fixed-split command for a lightweight code-path check.

```bash
# 1. Train on a fixed 20/4 participant split
PYTHONPATH=src .venv/bin/python scripts/train_split.py --device auto

# 2. Train five participant-held-out folds
PYTHONPATH=src .venv/bin/python scripts/train_cv.py \
  --device auto --metrics-json artifacts/cv_metrics.json

# 3. Evaluate five-fold MAE and decompose prediction sources
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate.py \
  --blend-checkpoints \
  --output-json artifacts/source_evaluation.json \
  --source-data-csv artifacts/source_data_components.csv

# 4. Evaluate the participant-disjoint held-out cohort and export grouped source data
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data

# 5. Export and validate the local model bundle
.venv/bin/python scripts/export_model_bundle.py
.venv/bin/python scripts/validate_model_bundle.py \
  artifacts/model_bundle_source_explicit.zip \
  --subject test_1 --video 1 --count 8

# 6. Run unit tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The complete workflow has been run locally, including reconstruction of an approximately 1.1 GB feature cache from the raw MAT files, fixed-split and five-fold training, MAE evaluation and source decomposition, held-out cohort evaluation, model-bundle export, and end-to-end inference. Complete run outputs are stored in the ignored directory `artifacts/full_pipeline_run/` and do not overwrite the formal checkpoints.

## Data and sharing boundaries

The repository contains only source code and essential reproducibility documentation. Local data, feature caches, model checkpoints, generated model bundles, evaluation outputs, and account credentials are excluded from version control. Verify the data license before sharing, and separately confirm whether model checkpoints may be redistributed.
