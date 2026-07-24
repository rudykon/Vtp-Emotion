# MER-PS Data Used in This Study

## Data Composition

This study uses two non-overlapping participant sets: 24 development-set participants for training and five-fold MAE evaluation, and 4 participants in a participant-disjoint held-out cohort for evaluation and source decomposition. Both data components contain synchronized EEG, fNIRS, resting-state baselines, and 1 Hz valence–arousal annotations.

| Data component | Participants | Videos | Trials | 1 Hz samples | Default local path |
| --- | ---: | ---: | ---: | ---: | --- |
| Training/validation data | 24 | 15 | 360 | 36,864 | `data/MER_PS_trainval/` |
| Participant-disjoint held-out cohort | 4 | 15 | 60 | 6,143 | `data/download/MER_PS_public_evaluation/` |

Both data components are licensed under CC BY-NC-SA 4.0 and restricted to non-commercial scientific research. Before downloading, using, or redistributing the data, verify the access conditions specified by the data provider and protect the privacy of anonymized participants.

## Study Task and Labels

MER-PS records synchronized EEG and fNIRS signals while participants watch emotion-eliciting videos. These signals support continuous valence–arousal regression. Dynamic labels are recorded at 1 Hz along two dimensions:

- `valence`: the pleasantness of the affective state;
- `arousal`: the activation level of the affective state.

Both dimensions use an integer scale of `[1, 255]`, with 128 as the neutral center.

## Signal Structure

Each participant directory contains:

```text
EEG_baselines.mat
EEG_videos.mat
fNIRS_baselines.mat
fNIRS_videos.mat
```

Dynamic annotations are stored in `annotations/`, with one MAT file per participant. EEG recordings contain 64 channels, whereas fNIRS recordings contain 6 signal types across 51 channels. Each trial also includes a 5-s resting-state segment. EEG arrays are organized as channel × time, and fNIRS arrays as signal type × channel × time.

The participant-disjoint held-out cohort directory additionally contains:

```text
sample_ids.csv
targets.csv
annotations/<subject>_label.mat
data/<subject>/
```

`sample_ids.csv` defines the sample order and the participant, video, and second-level timestamp associated with each sample. `targets.csv` stores valence and arousal row by row. The MAT annotations provide the same targets in their original trial-level organization.

## Local Download

The training/validation data repository is <https://huggingface.co/datasets/MER-PS/MER-PS-trainval>. After access has been granted, run:

```bash
bash scripts/download_data.sh
```

The participant-disjoint held-out cohort data are downloaded using a local token file. Pass the repository identifier supplied by the data provider through an environment variable:

```bash
MERPS_EXTERNAL_REPO_ID='<external-data-repository-id>' \
  bash scripts/download_external_data.sh
```

By default, the script reads `huggingface_token.json` from the project root and writes the data to `data/download/MER_PS_public_evaluation/`. The token file, download directory, and all raw data are excluded by `.gitignore`.

## Participant-Disjoint Held-Out Cohort Data Integrity Audit

Three levels of verification were performed after the local download:

- local byte counts matched the download metadata for 27/27 repository files;
- SHA-256 hashes for 16/16 large EEG/fNIRS physiological-signal files matched the remote object identifiers;
- `targets.csv` was element-wise identical to the 4 MAT annotation files, with a difference count of 0.

The evaluation script additionally verifies that:

- `sample_ids.csv` and `targets.csv` have identical ordering and contain no duplicate sample keys;
- timestamps increase continuously from 0 within each participant–video trial;
- the sample count for each trial matches the length of the corresponding MAT labels;
- all targets are finite and lie within `[1, 255]`.

Audit results are written to:

```text
artifacts/external_evaluation/data_audit.json
artifacts/external_evaluation/trial_summary.csv
```

## Role of the Data in This Project

All participants watch the same time-aligned videos. The primary task is therefore to reduce mean absolute error (MAE) for new viewers watching familiar videos. Within each outer fold, the video–time prior is constructed using only the training participants and combined with the EEG–fNIRS branch through fixed fusion. The fused predictor is used to achieve the lowest MAE, whereas the prior provides a low-cost population baseline.

The participant-disjoint held-out cohort is first used to assess whether the performance ranking persists among non-overlapping participants. After the main result has been established, paired sample-level predictions are used to analyze:

- the difference between the global label center and video identity;
- the difference between video identity and within-video temporal dynamics;
- the residual contribution of the EEG–fNIRS branch beyond a strong stimulus prior;
- the heterogeneity of this contribution across participants, videos, and normalized video time.

The protocol establishes participant disjointness only; it is not independent cross-site or cross-condition external validation and does not evaluate unseen videos. The current results therefore support conclusions about low MAE only for new viewers watching these 15 familiar videos. Downstream uses in video editing, advertisement placement, and content recommendation have also not been validated. If the research objective is extended to new content or stimulus-invariant physiological decoding, a video-held-out or participant × stimulus crossed holdout design will be required.

## Local Inference Inputs and Outputs

The model package expects the following input directory structure:

```text
sample_ids.csv
data/<participant_id>/
  EEG_baselines.mat
  EEG_videos.mat
  fNIRS_baselines.mat
  fNIRS_videos.mat
```

Inference results are written to `predictions.csv`:

```text
sample_id,valence,arousal
```

`sample_id` uniquely identifies each sample. `valence` and `arousal` are the predictions for the two continuous affective dimensions.
