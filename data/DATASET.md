# Local MER-PS Research Data

This directory contains documentation for local data only. Raw data, download caches, feature arrays, and account tokens are excluded from version control.

## Directory Conventions

```text
data/
├── MER_PS_trainval/                         # 24 participants in the development set
├── feature_cache/                           # Cached training features
└── download/
    ├── MER_PS_trainval.zip                  # Training/validation archive
    └── MER_PS_public_evaluation/            # 4 participants in the participant-disjoint held-out cohort
```

Training, five-fold mean absolute error (MAE) evaluation, and feature extraction use `data/MER_PS_trainval/` by default. Participant-disjoint held-out evaluation and source decomposition use `data/download/MER_PS_public_evaluation/` by default.

## Downloading the Training/Validation Data

Training/validation data repository: <https://huggingface.co/datasets/MER-PS/MER-PS-trainval>

Access approval is required for this dataset. After access has been granted to your account, run:

```bash
bash scripts/download_data.sh
```

The archive is saved as:

```text
data/download/MER_PS_trainval.zip
```

Before extraction, the archive can be checked with:

```bash
unzip -tq data/download/MER_PS_trainval.zip
```

After extraction, ensure that the data root is named `data/MER_PS_trainval/`.

## Downloading the Participant-Disjoint Held-Out Cohort Data

The download script reads `huggingface_token.json` from the project root. Its JSON field is `huggingface_token`. The token file is ignored by Git and must not be written to source code, logs, or version control.

Pass the repository identifier supplied by the data provider as an environment variable:

```bash
MERPS_EXTERNAL_REPO_ID='<external-data-repository-id>' \
  bash scripts/download_external_data.sh
```

The destination directory can also be specified explicitly:

```bash
MERPS_EXTERNAL_REPO_ID='<external-data-repository-id>' \
  bash scripts/download_external_data.sh \
  '<external-data-repository-id>' \
  data/download/MER_PS_public_evaluation
```

The download script uses the Hugging Face CLI and its parallel-transfer extension. The relevant Python dependencies are listed in `requirements.txt`.

## Scale and Structure of the Participant-Disjoint Held-Out Cohort Data

| Property | Value |
| --- | ---: |
| Participants | 4 |
| Videos | 15 |
| Trials | 60 |
| 1 Hz samples | 6,143 |
| Large EEG/fNIRS files | 16 |
| Annotation MAT files | 4 |

The participant-disjoint held-out cohort data root contains:

```text
sample_ids.csv
targets.csv
annotations/
data/
fNIRS_coordinates.csv
fNIRS_reservations.csv
Targeted_emotions.txt
```

Each `data/<subject>/` directory contains EEG and fNIRS trial recordings with their corresponding resting-state baselines.

## Integrity Checks and Local Evaluation

The current local copy has passed the following checks:

- byte-count verification for 27/27 files;
- SHA-256 verification for 16/16 large physiological-signal files;
- element-wise consistency between the CSV targets and MAT annotations;
- uniqueness, ordering, and temporal-continuity checks for 6,143 sample keys.

Rerun the data audit, participant-disjoint held-out MAE evaluation, and source decomposition with:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data
```

The script writes the data audit, overall metrics, metrics stratified by participant, video, and time, and paired sample-level predictions to `artifacts/external_evaluation/`. This directory can be regenerated from the code and is therefore not uploaded to the repository.

The protocol establishes participant disjointness only. It is not independent cross-site or cross-condition external validation, and it does not evaluate unseen videos.

## Data-Use Boundaries

The local documentation records both data components as licensed under CC BY-NC-SA 4.0 and restricted to non-commercial scientific research. Before using or redistributing the data, verify the access conditions specified by the data provider. See [`../docs/dataset.md`](../docs/dataset.md) for the detailed task structure, signal definitions, and role of each data component in the evaluation.
