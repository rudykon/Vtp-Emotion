# Low-MAE Continuous Affect Regression for New Viewers of Familiar Videos

## Research Objective

The 24 development-set participants watched the same 15 temporally aligned videos. This work first addresses a prediction problem: how to reduce the overall mean absolute error (MAE) for new viewers watching these familiar videos. Low-error group affect trajectories could support approximate response prediction for familiar videos. They could also provide group baselines for video editing, advertising placement, or content recommendation, and offer a coarse initialization for new-viewer predictions. These downstream applications have not been directly validated in this project.

The central claim is that a within-fold video–time prior provides a simple, low-cost, and effective way to reduce MAE. This claim concerns predictions for new viewers of familiar, temporally aligned videos. Fixed fusion achieves the lowest MAE on top of this prior. Comparisons among the EEG–fNIRS branch, video identity prior, video–time prior, and fixed fusion are presented after the main result to explain the sources of performance.

## Components of the MAE-Oriented Predictor

### Within-Fold Video–Time Prior

Within each outer fold, labels from the training participants available at each video and second-level time point are aggregated by their median. This coordinate-wise median defines an unsmoothed group affect trajectory. The trajectory is then smoothed within the same video by taking the mean over an edge-truncated temporal window with a radius of 3, spanning up to seven time points. Labels from the held-out participants do not contribute to their corresponding priors.

```text
raw_prior(video, time) = median_available_training_participants(label)
prior(video, time) = mean_edge_truncated_radius_3(raw_prior(video, *))
```

This design directly uses the video identity and timestamp available at inference while preventing leakage from held-out participant labels. Once constructed, the prior requires only a table lookup. It does not require EEG or fNIRS acquisition from new viewers, so the additional input and computational costs are low.

### EEG–fNIRS Branch

EEG and fNIRS signals are first centered using the five-second resting segment from the corresponding trial. For each one-second EEG window, the pipeline extracts relative log power and differential entropy in six frequency bands, together with Hjorth activity, mobility, and complexity. After concatenating the previous, current, and following one-second contexts, each EEG channel contains 45 features.

For each fNIRS channel and each of its six signal types, the pipeline computes the mean, standard deviation, slope, skewness, and kurtosis. After concatenating three seconds of context, each channel contains 90 features. Separate graph encoders model the two modalities, which exchange information through bidirectional cross-modal attention before entering the regression head. Five checkpoints trained with participant-grouped splits generate out-of-fold EEG–fNIRS branch predictions.

### Fixed Fusion

The final predictor uses the following fixed fusion:

```text
prediction = [0.99, 0.92] * video_time_prior
           + [0.01, 0.08] * eeg_fnirs_prediction
```

The two dimensions correspond to valence and arousal, respectively. The current evaluation does not use resting-output calibration, and its shrinkage vector is `[0.0, 0.0]`. Fixed fusion is the final predictor with the lowest MAE in this project. Because the weights were not reselected through documented nested validation, the small incremental gain over the prior is interpreted descriptively only.

## Five-Fold Participant-Held-Out Protocol

All development-set participants are partitioned into five folds. Each outer fold executes the following steps:

1. Reconstruct the video–time prior using only the training participants.
2. Estimate the EEG–fNIRS feature normalization parameters using only the training participants.
3. Predict the held-out participants using the EEG–fNIRS checkpoint associated with that fold.
4. Compare the EEG–fNIRS branch, video–time prior, and fixed fusion on exactly the same sample keys.

Predictions and ground-truth labels from all five folds are concatenated before metric computation. Sample-aggregated mean absolute error (MAE) is then calculated. This protocol evaluates affect prediction for new viewers of familiar videos. It does not evaluate transfer to unseen stimuli.

| Prediction strategy | Overall MAE | Valence MAE | Arousal MAE |
| --- | ---: | ---: | ---: |
| EEG–fNIRS branch | 47.3509 | 51.3475 | 43.3543 |
| Video–time prior | 29.0633 | 26.6681 | 31.4585 |
| Fixed fusion | 29.0146 | 26.6642 | 31.3651 |

Fixed fusion achieves the lowest overall MAE of 29.0146. This represents a reduction of 18.3363 relative to the EEG–fNIRS branch and a further reduction of 0.0487 relative to the video–time prior. The low-cost video–time prior alone achieves an MAE of 29.0633, reducing the error by 18.2876 relative to the EEG–fNIRS branch.

After confirming the lowest MAE, the component comparison further shows that the video–time prior already accounts for approximately 99.7% of the total error reduction from the EEG–fNIRS branch to fixed fusion. In this protocol, the prior alone therefore realizes most of the observed MAE reduction without requiring physiological acquisition from new viewers at inference. Adding the current EEG–fNIRS branch prediction under fixed fusion is associated with a smaller descriptive adjustment.

## Participant-Disjoint Held-Out Cohort Evaluation

The separate evaluation data form a participant-disjoint held-out cohort containing 4 participants who do not overlap with the development set, 60 trials, and 6,143 second-level targets. The evaluation script loads targets for integrity checks and scoring, but target values are not passed to prior construction, checkpoint training, feature extraction, or prediction. After sample-order integrity checks, predictions are rounded to the nearest integer, clipped to `[1, 255]`, and scored with local targets on matching `sample_id` values. This setting evaluates transfer to non-overlapping participants within the familiar-video setting. It does not constitute independent cross-site or cross-condition external validation.

After establishing the lowest MAE, five prediction strategies are used for analysis:

1. Global constant: the two-dimensional median of all development-set labels.
2. Video identity prior: the temporal median of each video's smoothed development-set video–time trajectory, repeated across timestamps.
3. Video–time prior: a smoothed within-video trajectory of second-level medians constructed from all development-set participants.
4. EEG–fNIRS branch: a six-model ensemble comprising one full-development-set checkpoint and five participant-fold checkpoints.
5. Fixed fusion: the video–time prior and EEG–fNIRS branch fused using prior weights `[0.99, 0.92]`.

| Prediction strategy | Overall MAE | Valence MAE | Arousal MAE | Overall MSE |
| --- | ---: | ---: | ---: | ---: |
| Global constant | 44.3296 | 47.4622 | 41.1971 | 2861.1141 |
| Video identity prior | 33.3627 | 32.5567 | 34.1686 | 1933.0132 |
| Video–time prior | 28.0410 | 25.3436 | 30.7384 | 1484.6883 |
| EEG–fNIRS branch | 42.7486 | 45.2852 | 40.2119 | 2729.3677 |
| Fixed fusion | **27.7246** | **25.1970** | **30.2522** | **1440.5642** |

Fixed fusion again achieves the lowest overall MAE at 27.7246. The video–time prior alone reaches 28.0410, only 0.3165 higher when the difference is computed from unrounded metric values. The held-out cohort evaluation then uses paired sample-level predictions to examine this increment and its sources by participant, video, and ten normalized video-time bins:

- Fixed fusion improves performance for 3 of the 4 participants, with changes ranging from a deterioration of 0.0622 to an improvement of 0.6938.
- Fixed fusion improves performance for 9 of the 15 videos, with changes ranging from a deterioration of 0.2971 to an improvement of 1.3105.
- In the first normalized time bin, the video identity prior has an MAE of 45.53, whereas the video–time prior has an MAE of 13.40.
- In each of the final five time bins, the video identity prior has a slightly lower MAE than the video–time prior.

These stratified results show that neither the overall fusion increment nor the temporal increment is uniform. Because there are only 4 participant clusters, no significance test based on pseudoreplicated second-level samples is performed.

## MAE Conclusions and Boundaries of Source Analysis

The main result is that fixed fusion achieves the lowest MAE under both the five-fold participant-held-out protocol and the participant-disjoint held-out cohort evaluation. The video–time prior alone is already a strong, low-cost predictor. The subsequent source analysis shows that most of the reduction arises from the group affect trajectory indexed by video and time. The current EEG–fNIRS branch prediction is associated with a small and heterogeneous complementary correction in fixed fusion.

This result does not demonstrate that EEG or fNIRS lacks affective information, nor can it be extrapolated to unseen videos. The project has also not directly validated downstream effects on video editing, advertising placement, or content recommendation. Broader claims about generalization or the independent contribution of physiological information require future experiments. These experiments should report stimulus-only baselines, adopt participant × stimulus crossed holdout designs, and retain paired residuals for every component. They should also estimate uncertainty while respecting the participant and video clustering structure.

## Reproduction Commands

Run the five-fold MAE evaluation and source decomposition:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate.py --blend-checkpoints
```

Run the evaluation on the participant-disjoint held-out cohort and write compact analysis source data to the local run-artifact directory:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data
```

Evaluation artifacts are written to `artifacts/external_evaluation/`. They include the data audit, overall metrics, participant-, video-, and time-stratified metrics, and paired sample-level predictions. Compact analysis source data are written to `artifacts/external_source_data/`. Both directories can be regenerated from code and are excluded from version control.

The model package is retained only as an inference and reproducibility artifact after training on the complete dataset. The project's lowest-MAE conclusion comes from the five-fold and participant-disjoint held-out cohort evaluations. Conclusions about sources and heterogeneity come from the subsequent component comparisons and local paired evaluation of the held-out cohort.
