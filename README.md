<p align="center">
  <strong>English</strong> · <a href="README_zh.md">中文</a>
</p>

<p align="center">
  <img src="docs/brand-mark.svg" width="520" alt="Project brand mark">
</p>

<h1 align="center">Vtp-Emotion</h1>

<p align="center">
  <strong>Video–Time Priors for EEG–fNIRS Emotion Regression on Familiar Videos</strong><br>
  Separating shared stimulus responses from viewer-specific physiological correction.
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-%E2%89%A53.10-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 or newer"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-4C78A8?style=flat-square" alt="Apache License 2.0"></a>
  <a href="https://huggingface.co/datasets/MER-PS/MER-PS-trainval"><img src="https://img.shields.io/badge/Data-MER--PS-FFD21E?style=flat-square&logo=huggingface&logoColor=black" alt="MER-PS data on Hugging Face"></a>
</p>

<p align="center">
  <a href="https://rudykon.github.io/Vtp-Emotion/">Project website</a> ·
  <a href="https://rudykon.github.io/Vtp-Emotion/demo/">Browser demo</a> ·
  <a href="#project-overview">Overview</a> ·
  <a href="#method">Method</a> ·
  <a href="#results">Results</a> ·
  <a href="#analysis">Analysis</a> ·
  <a href="#getting-started">Quick Start</a> ·
  <a href="#reproduction">Reproduction</a>
</p>

> [!IMPORTANT]
> **Main finding:** the video–time prior supplies most of the MAE reduction relative to the EEG–fNIRS branch. Fixed fusion adds a small, heterogeneous improvement. Evaluation concerns new viewers of the same videos seen during training; the physiological branch uses future context and supports offline prediction.

<a id="project-overview"></a>
## Overview

Do a new viewer's EEG and fNIRS signals improve continuous emotion regression beyond the response shared across viewers of the same stimulus? Vtp-Emotion examines this question on MER-PS 2026, predicting valence and arousal at **1 Hz on the original [1, 255] scale**.

Because video identity and aligned playback time are known at inference, earlier viewers' labels can supply a shared affect trajectory. We compare this **video–time prior**, a graph-based **EEG–fNIRS branch**, and their **fixed-weight fusion**. Global-constant and video-identity baselines further separate the contributions associated with label level, video identity, and within-video time.

| Component | Inputs at inference | Role |
| --- | --- | --- |
| Video–time prior | Known video identity and aligned second | Shared response estimated from training participants' labels; no new-viewer physiology required |
| EEG–fNIRS branch | New viewer's physiological signals, resting baseline, and temporal context | Viewer-specific prediction from graph encoders and bidirectional cross-modal attention |
| Fixed fusion | Prior and physiological prediction | Prior weights of 0.99 for valence and 0.92 for arousal |

Held-out participants' labels are excluded from prior construction, feature standardization, model training, and prediction. Checkpoint and fusion-weight selection were **not fully nested**, as discussed under [scope and limitations](#scope).

<a id="method"></a>
## Method

<p align="center">
  <a href="docs/figures/icassp2027/method_overview.pdf">
    <img src="docs/figures/icassp2027/method_overview.png" alt="Known video and time feed a training-label prior; new-viewer EEG and fNIRS feed graph encoders and cross-modal attention; fixed fusion combines both predictions" width="100%">
  </a>
</p>
<p align="center"><em>Figure 1 | Familiar-video regression with a fold-wise label prior and an offline EEG–fNIRS branch. Output curves are schematic. Click any paper figure for its PDF.</em></p>

1. **Build the prior.** For each video, second, and target, take the median label over the available training participants, then apply a radius-three moving average within the video boundary. Internal evaluation rebuilds this prior within each training fold; external-cohort evaluation uses all 24 development participants.
2. **Extract physiological features.** Center signals using the corresponding five-second resting baseline and resample EEG to 200 Hz. EEG features combine six-band relative log power, differential entropy, and Hjorth statistics. fNIRS features summarize HbO, HbR, HbT, and absorbance at 780, 805, and 830 nm using mean, standard deviation, slope, skewness, and kurtosis. Concatenating `t−1`, `t`, and `t+1` produces EEG tensors of `64 × 45` and fNIRS tensors of `51 × 90`, with edge padding at trial boundaries.
3. **Predict and fuse.** Learned-adjacency graph encoders with 32-dimensional channel embeddings and four-head bidirectional cross-modal attention feed a regressor. The fold models train with MSE plus `0.01 ×` contrastive alignment loss, dropout `0.7`, AdamW, and early stopping on validation MSE. Predictions are returned to the original label scale and fused as follows:

```text
prediction = [0.99, 0.92] * video_time_prior
           + [0.01, 0.08] * eeg_fnirs_prediction
# Target order: [valence, arousal].
```

The same weights are retained for the external cohort. Resting-output calibration is disabled. The use of `t+1` physiological features makes this an **offline estimator**.

<a id="results"></a>
## Results

All values are **sample-pooled MAE on [1, 255]**, with lower values better. Bold marks the lowest value among the evaluated variants within each protocol.

**Internal evaluation — five participant-held-out folds, 24 participants, 15 videos, 360 trials, 36,864 one-second samples.**

| Variant | Overall | Valence | Arousal |
| --- | ---: | ---: | ---: |
| EEG–fNIRS branch | 47.35 | 51.35 | 43.35 |
| Video–time prior | 29.06 | 26.67 | 31.46 |
| **Fixed fusion** | **29.01** | **26.66** | **31.37** |

**External cohort — 4 additional participants excluded from training, the same 15 videos, 60 trials, 6,143 one-second samples.**

| Variant | Overall | Valence | Arousal |
| --- | ---: | ---: | ---: |
| Global constant | 44.33 | 47.46 | 41.20 |
| Video identity | 33.36 | 32.56 | 34.17 |
| EEG–fNIRS branch | 42.75 | 45.29 | 40.21 |
| Video–time prior | 28.04 | 25.34 | 30.74 |
| **Fixed fusion** | **27.72** | **25.20** | **30.25** |

The global constant is the coordinate-wise median of all development labels. The video-identity baseline uses the temporal median of each video's smoothed prior.

| Protocol detail | Internal evaluation | External cohort |
| --- | --- | --- |
| Physiological prediction | Each participant's matching held-out fold model | Average of five fold models and one all-development checkpoint |
| Prior and feature standardization | Corresponding training participants only | Prior from all 24 development participants; each checkpoint retains its own training standardization |
| Scoring | Pooled out-of-fold floating-point predictions | Each variant rounded with `numpy.rint`, then clipped to `[1, 255]` |

**29.01 and 27.72 are not a direct cross-cohort improvement estimate:** the participants, ensemble construction, and rounding differ. The external cohort establishes participant disjointness within the familiar-video setting; it does not establish cross-site or unseen-video generalization.

<a id="analysis"></a>
## What explains the error reduction?

On the external cohort, moving from the global constant to video identity reduces overall MAE by **10.97 points**; adding playback time reduces it by another **5.32 points**. Fixed fusion adds **0.32 points** of improvement over the video–time prior. Internally, its increment is only **0.05 points**.

Relative to the reduction from EEG–fNIRS alone to fusion, the prior accounts for **99.73% internally** and **97.89% externally**, computed before display rounding. These are descriptive ratios of error reduction, not a causal decomposition of information in the signals.

<p align="center">
  <a href="docs/figures/icassp2027/external_source_decomposition.pdf">
    <img src="docs/figures/icassp2027/external_source_decomposition.png" alt="External-cohort overall MAE, paired fusion gains for all four participants and fifteen videos, and errors across ten normalized playback-time bins" width="100%">
  </a>
</p>
<p align="center"><em>Figure 2 | Source contributions and heterogeneous fusion gains. Positive prior-minus-fusion MAE favors fusion; circles mark gains and crosses mark losses.</em></p>

| External-cohort comparison: fusion vs. prior | Observation |
| --- | --- |
| Participants | Lower MAE for 3 of 4 |
| Videos | Lower MAE for 9 of 15; largest gain +1.31 (V7), largest loss −0.30 (V11) |
| Participant–video trials | Lower MAE in 38 of 60; higher in 22 |
| Normalized playback time | Higher MAE in the first 3 bins; lower in the remaining 7 |
| Video × time cells | Lower MAE in 76 of 150 cells, equal in 7, higher in 67 |

Time conditioning also helps unevenly. In the first normalized bin, video identity and the video–time prior yield MAEs of **45.53** and **13.40**. Video identity is better in each of the final five bins: the prior's pooled **11.89-point reduction** in the first half outweighs its **1.33-point increase** in the second half.

<p align="center">
  <a href="docs/figures/icassp2027/external_diagnostics.pdf">
    <img src="docs/figures/icassp2027/external_diagnostics.png" alt="Fixed-fusion prediction densities for valence and arousal and prior/fusion MAE heatmaps over fifteen videos and ten time bins" width="100%">
  </a>
</p>
<p align="center"><em>Figure 3 | Diagnostics using all 6,143 external samples. Prediction densities share a log-count scale; heatmaps share a 0–65 MAE scale.</em></p>

Prediction ranges are compressed, and the prior and fusion share **9 of their 10 highest-error cells**. Much of the prior's error structure remains after fusion.

<details>
<summary><strong>Post hoc weight sensitivity</strong></summary>

A diagnostic sweep over prior weights from 0 to 1 in steps of 0.01 finds internal target-wise minima at `[0.99, 0.92]`. At these weights, fusion improves on the prior in only 3 of 5 folds. This sweep does not reproduce the original selection procedure. External-cohort minima shift to `[0.83, 0.82]` (MAE 26.91), but use held-out outcomes and are diagnostic only. All main results retain the original fixed weights `[0.99, 0.92]`.

</details>

These analyses are descriptive. With only four external participant clusters, correlated seconds are not treated as independent replicates for significance testing.

<a id="getting-started"></a>
## Quick start

```bash
git clone https://github.com/rudykon/Vtp-Emotion.git
cd Vtp-Emotion

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
source .venv/bin/activate

# Lightweight repository validation; raw data are not required.
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The expected validation result is **15 passing tests**. Full training and evaluation require the MER-PS data. The default requirements install PyTorch 2.5.1 for CUDA 12.1; an NVIDIA GPU is recommended, while `--device auto` can fall back to CPU. Use the appropriate PyTorch wheel for a CPU-only environment. If downloads pass through a SOCKS proxy, `socksio` supplies the network dependency; the held-out download script also requires the system command `jq`.

<a id="data"></a>
## Data preparation

| Data component | Scale | Repository | Default local path |
| --- | ---: | --- | --- |
| Training/validation | 24 participants · 360 trials · 36,864 samples | [MER-PS train/validation](https://huggingface.co/datasets/MER-PS/MER-PS-trainval) | `data/MER_PS_trainval/` |
| Participant-disjoint held-out | 4 participants · 60 trials · 6,143 samples | [Held-out evaluation data](https://huggingface.co/datasets/MER-PS/MER-PS-public-leaderboard-evaluation-data) | `data/download/MER_PS_public_evaluation/` |

The training/validation repository is access-controlled. Request access on its Hugging Face page, authenticate after activating the virtual environment, and then download the approved archive:

```bash
hf auth login
bash scripts/download_data.sh
```

The script downloads and integrity-checks the ZIP archive but does not extract it. It saves the file as `data/download/MER_PS_trainval.zip`. Inspect the top-level entry, then extract and rename that directory without creating an extra nesting level:

```bash
unzip -Z1 data/download/MER_PS_trainval.zip | head

MERPS_ARCHIVE='data/download/MER_PS_trainval.zip'
MERPS_TOP_DIR="$(unzip -Z1 "$MERPS_ARCHIVE" | sed -n '1{s:/$::;p;q}')"
test -n "$MERPS_TOP_DIR"
test ! -e data/MER_PS_trainval
unzip -q "$MERPS_ARCHIVE" -d data/download
mv "data/download/$MERPS_TOP_DIR" data/MER_PS_trainval
```

Download the participant-disjoint held-out data with the local `huggingface_token.json` file:

```bash
MERPS_EXTERNAL_REPO_ID='MER-PS/MER-PS-public-leaderboard-evaluation-data' \
  bash scripts/download_external_data.sh
```

Token files, raw data, and download directories are excluded by `.gitignore`. The held-out script requires the Hugging Face CLI and `jq`, reads the token locally, and does not write it to downloaded files, logs, or version control. Archive inspection and extraction additionally require `unzip`. Verify the current terms on each dataset repository before use or redistribution.

See [`data/DATASET.md`](data/DATASET.md) and [`docs/dataset.md`](docs/dataset.md) for the full directory structure, signal definitions, integrity checks, and data-use boundaries.

<details>
<summary><strong>Open the supplementary data diagnostic</strong></summary>
<br>

<p align="center">
  <a href="docs/figures/external_data_landscape.png">
    <img src="docs/figures/external_data_landscape.png" alt="Held-out-cohort valence–arousal coverage and video–time variation" width="92%">
  </a>
</p>
<p align="center"><em>Supplementary diagnostic | Held-out-cohort label coverage and descriptive variation across videos and normalized playback time.</em></p>

</details>

<a id="reproduction"></a>
## Reproduction and audit workflow

The public commands below cover explicit feature reconstruction, fixed-split and five-fold training, prior construction, MAE evaluation, source decomposition, held-out evaluation, model-bundle export, validation, and tests. Full training can take substantial time. The `--test-mode` option runs a three-epoch training check but still requires prepared data. Exact recreation of the reported held-out estimator additionally requires the full-development checkpoint described below.

> [!CAUTION]
> These commands use the default `data/feature_cache/`, `checkpoints/`, and `artifacts/` paths. Feature reconstruction and training can replace files with the same names. Use a clean checkout or pass isolated paths through `--cache-dir`, `--model-dir`, `--log-path`, `--output`, `--checkpoint-dir`, and `--output-dir` when preserving existing local runs matters.

```bash
# 0. Rebuild features from the raw MAT files and check that they load, then stop
PYTHONPATH=src .venv/bin/python scripts/train_split.py \
  --prepare-only --no-cache --device auto

# 1. Train on a fixed 20/4 participant split
PYTHONPATH=src .venv/bin/python scripts/train_split.py --device auto

# 2. Train five participant-held-out folds
PYTHONPATH=src .venv/bin/python scripts/train_cv.py \
  --device auto --metrics-json artifacts/cv_metrics.json

# 3. Build the video–time prior required by held-out evaluation and bundle export
PYTHONPATH=src .venv/bin/python -m merps.prior

# 4. Evaluate five-fold MAE and decompose prediction sources
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate.py \
  --blend-checkpoints \
  --output-json artifacts/source_evaluation.json \
  --source-data-csv artifacts/source_data_components.csv

# 5. Evaluate the held-out cohort; final_v3.pt is preferred, best_v3.pt is the fallback
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data

# 6. Export and validate the local model bundle
.venv/bin/python scripts/export_model_bundle.py
.venv/bin/python scripts/validate_model_bundle.py \
  artifacts/model_bundle_source_explicit.zip \
  --subject test_1 --video 1 --count 8

# 7. Run unit tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

The reported held-out MAE of **27.72** used `checkpoints/final_v3.pt` as the full-development member of the six-model physiological ensemble. The repository does not currently provide a command that recreates this checkpoint, and trained checkpoints are not version controlled. In a clean checkout, held-out evaluation and bundle export therefore fall back to the fixed-split `checkpoints/best_v3.pt`; this public fallback path remains fully runnable, but its held-out metrics should not be expected to reproduce **27.72** exactly.

Training writes checkpoints under `checkpoints/`; evaluation outputs and model bundles are written under `artifacts/`, with external-cohort evaluation under `artifacts/external_evaluation/`.

<a id="repository"></a>
## Repository map

| Path | Purpose |
| --- | --- |
| `src/merps/` | Feature extraction, video–time prior, physiological model, calibration, and inference |
| `scripts/` | Data download, training, evaluation, source decomposition, and model-bundle tools |
| `tests/` | Unit tests for metrics, calibration, source construction, and bundle configuration |
| `docs/` | Additional method, dataset, and analysis documentation |
| `docs/figures/icassp2027/` | Method and result figures, with PNG previews and PDF versions |
| `data/` | Tracked local-data instructions; raw data, downloads, and feature caches are ignored |
| `checkpoints/` | Local physiological checkpoints and priors; not version controlled |
| `artifacts/` | Logs, evaluation outputs, figures, and model bundles; not version controlled |

<a id="scope"></a>
## Scope and limitations

- **Familiar videos only.** The same 15 videos occur in training and evaluation. Unseen-video, cross-site, and cross-condition transfer have not been evaluated.
- **Offline physiology.** Features include `t+1`; no temporal lag compensates for the fNIRS haemodynamic delay.
- **Selection limits.** Checkpoint and weight selection were not fully nested. Fully nested participant splits are needed to estimate the small fusion increment more reliably.
- **One physiological architecture.** EEG-only, fNIRS-only, graph, and attention contributions were not isolated. The results neither establish nor rule out independent affective information in either modality.
- **Descriptive comparisons.** Four external participants provide limited evidence about population-level variation; second-level observations are correlated.
- **Unmeasured deployment benefits.** The prior needs earlier viewers' labels but avoids new physiological acquisition. Latency, energy savings, and downstream application benefits were not measured.

This repository publishes source code, dataset descriptions, method and usage documentation, and selected figure assets. The approved browser-demo export in `website/assets/demo/` is the sole exception for model weights and data: it contains the inference ensemble and a 30-second real feature excerpt under CC BY-NC-SA 4.0. Other raw and processed data, training checkpoints, design/revision records, manuscripts, and paper-figure generation programs remain local and are excluded from version control. Credentials, feature caches, and local run artifacts are also excluded. Dataset and third-party terms apply separately.


## Browser demo

[Open the browser demo](https://rudykon.github.io/Vtp-Emotion/demo/). Computation runs on the visitor's CPU in a background worker. The page automatically downloads a trained six-model ensemble and 30 seconds of real EEG–fNIRS features, then computes predictions locally. No account, manual file selection, or inference server is required. Replay the viewing journey with an illustrated emotion snapshot, pleasantness and activation scales, an emotion map, and automatically selected moments. The explanatory text is derived from the real predictions; numerical curves and model settings remain available in expandable panels. You can also select your own local model and feature files; those files are not uploaded.

The included sample comes from [MER-PS training/validation data](https://huggingface.co/datasets/MER-PS/MER-PS-trainval), subject `test_1`, video 1, seconds 0–29. It demonstrates execution on real recordings and is not held-out accuracy evaluation. Public model and sample assets use [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/); see the [provenance notice](website/assets/demo/NOTICE.txt) and [checksummed manifest](website/assets/demo/manifest.json).

To use your own files, prepare private exports after installing the repository's regular dependencies and obtaining the data and checkpoints:

```bash
.venv/bin/pip install -r requirements-demo.txt
.venv/bin/python scripts/export_browser_demo.py model
.venv/bin/python scripts/export_browser_demo.py input \
  --data-root data/MER_PS_trainval --subject test_1 --video 1 --count 60
```

Choose **Use local model and data files**, then select `artifacts/browser/model.vtp-model.json` and `artifacts/browser/input.vtp-input.json` on the demo page. MAT preprocessing runs locally in Python; browser inference uses ONNX Runtime Web with checkpoint-specific standardization, the six-model ensemble, prior lookup, fixed fusion, and round-to-even output conversion. The `best_v3.pt` fallback caveat above still applies. Additional local exports remain excluded from publication.

The website build downloads an integrity-checked ONNX Runtime Web 1.22.0 runtime and serves it with the static pages. Run browser numerical and input-validation tests with `node --test tests/test_browser_demo.cjs` (Node.js 22).

<a id="open-source-license"></a>
## License

Complete source implementations of all algorithms evaluated in this project are provided in this repository. Unless otherwise noted, repository-authored source code is licensed under the [Apache License 2.0](LICENSE). Datasets, model checkpoints, generated artifacts, and third-party dependencies remain subject to their own terms.
