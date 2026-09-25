# Reproduce

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

See [`data/DATASET.md`](https://github.com/rudykon/Vtp-Emotion/blob/main/data/DATASET.md) and [`docs/dataset.md`](https://github.com/rudykon/Vtp-Emotion/blob/main/docs/dataset.md) for the full directory structure, signal definitions, integrity checks, and data-use boundaries.

<details>
<summary><strong>Open the supplementary data diagnostic</strong></summary>
<br>

<figure class="paper-figure">
<a href="../../assets/figures/external_data_landscape.png">
    <img src="../../assets/figures/external_data_landscape.png" alt="Held-out-cohort valence–arousal coverage and video–time variation" width="92%">
  </a>
<figcaption>Supplementary diagnostic | Held-out-cohort label coverage and descriptive variation across videos and normalized playback time.</figcaption>
</figure>

</details>

## Reproduction and audit workflow

The public commands below cover explicit feature reconstruction, fixed-split and five-fold training, prior construction, MAE evaluation, source decomposition, held-out evaluation, model-bundle export, validation, and tests. Full training can take substantial time. The `--test-mode` option runs a three-epoch training check but still requires prepared data. Exact recreation of the reported held-out estimator additionally requires the full-development checkpoint described below.

!!! warning "Preserve existing runs"

    These commands use the default `data/feature_cache/`, `checkpoints/`, and `artifacts/` paths. Feature reconstruction and training can replace files with the same names. Use a clean checkout or pass isolated paths through `--cache-dir`, `--model-dir`, `--log-path`, `--output`, `--checkpoint-dir`, and `--output-dir` when preserving existing local runs matters.

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

## Build this website

Website dependencies are separate from model-training dependencies. From the repository root:

```bash
python3 -m venv .venv-site
.venv-site/bin/pip install -r requirements-docs.txt
.venv-site/bin/python scripts/build_site.py
.venv-site/bin/python -m http.server 8000 --directory site
```

The builder assembles the pages and selected existing figures in `build/site_docs/`, then writes the static site to `site/`. The GitHub Actions workflow publishes the site when its source changes on `main`.

Only the selected public pages and figures enter the website. Research data, model weights, manuscripts, design/revision records, and scientific-figure generation programs remain local.
