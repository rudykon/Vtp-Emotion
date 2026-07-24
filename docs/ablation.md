# Source Ablation in a Participant-Disjoint Held-Out Evaluation

## Experimental Objective

This experiment provides an interpretive analysis after fixed fusion achieved the lowest mean absolute error (MAE). It compares five implemented prediction variants: the global constant, video identity prior, video–time prior, current EEG–fNIRS branch prediction, and fixed fusion. The primary objective remains to reduce MAE for new viewers watching familiar videos. This ablation characterizes the observed error differences and whether the fixed-fusion gain is stable.

## Evaluation Protocol

- The participant-disjoint held-out cohort included 4 participants with no overlap with the 24 development participants.
- The data comprised 60 trials and 6,143 one-second samples covering the same 15 videos.
- The pipeline loaded `targets.csv` before prediction for integrity checks. It verified the required columns, unique sample identifiers, finite in-range values, row order against `sample_ids.csv`, contiguous trial timestamps, trial lengths, and exact agreement with the MAT annotations.
- The valence and arousal target values were used for integrity auditing and subsequent local scoring. They were not used to construct the development-set priors, fit or select checkpoints, or generate predictions.
- Before scoring, every prediction variant was rounded to the nearest integer with `numpy.rint`, clipped to the original label scale `[1, 255]`, and evaluated on identical sample keys with the same metric implementations.
- The primary metric was overall mean absolute error (MAE), jointly aggregated over valence and arousal. We also report valence MAE, arousal MAE, and overall mean squared error (MSE). Lower values are better for all error metrics.
- Stratified analyses were aggregated by participant, video, and ten normalized video-time bins. Adjacent one-second samples were not treated as independent replicates in inferential tests.

This protocol is participant-disjoint within the familiar-video setting. It does not constitute independent cross-site or cross-condition external validation, and it does not evaluate unseen videos.

## Ablation Variants

| Prediction strategy | Available information | Analytical role |
| --- | --- | --- |
| Global constant | The two-dimensional median of all development labels | Measures the label-center baseline without video, time, or the current EEG–fNIRS branch prediction |
| Video identity prior | For each video, the median over valid time points of its stored development-set video–time prior; missing videos fall back to the global constant | Describes time-invariant differences among the implemented video-level predictions |
| Video–time prior | The cross-participant median at each second-level coordinate of each video, smoothed within videos | Measures time-aligned shared affective trajectories |
| Current EEG–fNIRS branch prediction | Mean prediction from the six development-set EEG–fNIRS checkpoints | Describes the predictive performance of the currently implemented EEG–fNIRS branch |
| Fixed fusion | Video–time prior and current EEG–fNIRS branch prediction with weights `[0.99, 0.92]` | Describes the aggregate change obtained by combining the two implemented predictions |

## Lowest-MAE Results

| Prediction strategy | Overall MAE ↓ | Valence MAE ↓ | Arousal MAE ↓ | Overall MSE ↓ |
| --- | ---: | ---: | ---: | ---: |
| Global constant | 44.3296 | 47.4622 | 41.1971 | 2861.1141 |
| Video identity prior | 33.3627 | 32.5567 | 34.1686 | 1933.0132 |
| Video–time prior | 28.0410 | 25.3436 | 30.7384 | 1484.6883 |
| Current EEG–fNIRS branch prediction | 42.7486 | 45.2852 | 40.2119 | 2729.3677 |
| Fixed fusion | **27.7246** | **25.1970** | **30.2522** | **1440.5642** |

Fixed fusion achieved the lowest overall MAE of `27.7246`, whereas the video–time prior alone achieved `28.0410`. This result first confirms the MAE of the final predictor and also shows that the low-cost prior already approaches the performance of fixed fusion.

## Quantitative Source Analysis after Achieving the Lowest MAE

1. Relative to the video–time prior, fixed fusion further reduced overall MAE by `0.3165`, valence and arousal MAE by `0.1467` and `0.4862`, respectively, and overall MSE by `44.1240`. This value was calculated from the full-precision, unrounded MAE values before display rounding. The aggregate direction was consistent, although stratified results showed that not every recording benefited.
2. Moving from the global constant to the video identity prior reduced overall MAE by `10.9670`, a relative reduction of `24.74%`. This result indicates clear mean affective differences across videos.
3. Moving from the video identity prior to the video–time prior further reduced overall MAE by `5.3217`, a relative reduction of `15.95%`. Valence and arousal MAE decreased by `7.2131` and `3.4302`, respectively. Under this implemented decomposition, allowing within-video time variation was associated with an additional descriptive error reduction.
4. The current EEG–fNIRS branch prediction achieved an overall MAE of `42.7486`, outperforming the global constant but underperforming the video–time prior. This comparison documents the predictive gap of the current branch but does not identify its cause.
5. The total reduction in overall MAE from the current EEG–fNIRS branch prediction to fixed fusion was `15.0240`. The video–time prior already accounted for `14.7076`, or `97.89%`, of this reduction. Most of the observed MAE difference was associated with the time-resolved group trajectory. Adding the current EEG–fNIRS branch prediction under fixed fusion was associated with a smaller descriptive adjustment.

## Participant and Video Heterogeneity

Paired residuals were calculated on the same samples for the video–time prior and fixed fusion. We define the "fusion increment" as `prior MAE - fusion MAE`, such that a positive value indicates better performance from fixed fusion.

- Participant level: 3/4 participants improved. The worst outcome was a deterioration of `0.0622`, and the best was an improvement of `0.6938`.
- Video level: 9/15 videos improved. The worst outcome was a deterioration of `0.2971`, and the best was an improvement of `1.3105`.
- The sample-aggregated improvement of `0.3165`, calculated from the full-precision unrounded MAEs, therefore cannot be interpreted as fixed fusion being consistently effective for every participant or video.

## Within-Video Time Heterogeneity

Each trial was mapped according to its duration into ten equal-width normalized time bins. The implemented video identity prior assigns each video the median over valid time points of its stored video–time prior. The video–time prior instead allows predictions to vary over time within the same video.

- In the first time bin, the video identity prior had an MAE of `45.53`, whereas the video–time prior achieved only `13.40`, yielding the largest advantage from the time coordinate.
- This advantage then decreased progressively. In the final five bins, the video identity prior instead performed slightly better.
- The overall temporal gain of `5.3217` was therefore concentrated in specific video stages rather than distributed uniformly throughout each video.

## Analytical Value and Project Positioning

This ablation does not replace the primary objective of reducing MAE. After establishing the main result, it describes how the observed reductions are distributed across the implemented prediction variants. The source decomposition contrasts a time-invariant video identity prior with the time-varying video–time prior. Allowing time variation corresponded to an additional, stage-specific descriptive error reduction. Although the current EEG–fNIRS branch prediction was less accurate than the video–time prior, fixed fusion improved the aggregate metrics while retaining both gains and losses across participants and videos.

The current results support a bounded conclusion: for new viewers watching familiar videos, the video–time prior is a simple, low-cost, and strong baseline. Adding the current EEG–fNIRS branch prediction under fixed fusion was associated with a smaller and heterogeneous descriptive adjustment. This participant-disjoint evaluation does not constitute independent cross-site or cross-condition external validation, and it does not evaluate unseen videos. It neither establishes nor negates the independent affective information in EEG or fNIRS. Generalization to new videos requires a participant × stimulus crossed holdout experiment.

## Limitations

- The held-out cohort contains only 4 participant clusters. Participant, video, and time stratification can describe heterogeneity but cannot support stable significance conclusions.
- The fixed-fusion weights were not reselected through a documented nested-validation procedure. The fusion increment of `0.3165`, calculated from full-precision unrounded MAEs, is therefore interpreted descriptively only.
- The current EEG–fNIRS branch prediction uses an ensemble of six development-set checkpoints. The current experiment cannot distinguish the individual contributions of EEG, fNIRS, graph structure, and cross-modal attention.
- All held-out participants still watched videos that appeared during development. The results cannot be generalized to unseen stimuli.
- Only one participant-disjoint held-out cohort is currently available. The source ranking requires confirmation with more data and participant × stimulus crossed designs.

## Reproduction

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data
```

The main outputs include:

- `artifacts/external_evaluation/metrics.json`: overall metrics for the five variants;
- `artifacts/external_evaluation/metrics_by_subject.csv`, `metrics_by_video.csv`, and `metrics_by_time_bin.csv`: stratified results;
- `artifacts/external_evaluation/paired_predictions.csv`: sample-level targets, predictions, and sample metadata;
- `artifacts/external_source_data/source_data_external_*.csv`: compact, traceable source data for analysis.
