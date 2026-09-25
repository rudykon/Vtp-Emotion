# Method

Video–Time Priors for EEG–fNIRS Emotion Regression on Familiar Videos.

The task is to predict a new viewer's valence and arousal for a known video at each aligned second. Both targets use the original **[1, 255]** scale.

<figure class="paper-figure">
  <a href="../../assets/figures/icassp2027/method_overview.pdf" target="_blank" rel="noopener" aria-label="Overview of the prior, physiological branch, and fixed fusion (PDF)">
    <img src="../../assets/figures/icassp2027/method_overview.png" alt="Overview of the prior, physiological branch, and fixed fusion" loading="lazy">
  </a>
  <figcaption>Two parallel branches separate shared stimulus response from viewer-specific prediction. Click for the full-size PDF.</figcaption>
</figure>
## Video–time prior

For each video, second, and target, take the median of available training participants' labels. Smooth the trajectory with a **radius-three moving average**, truncated at the video's boundaries.

```text
raw_prior(video, second) = median(training_participants' labels)
prior(video, second)     = within_video_moving_average(raw_prior, radius=3)
```

Internal evaluation rebuilds the prior using only each fold's training participants. External-cohort evaluation uses all 24 development participants. Once constructed, lookup requires video identity and time, without physiological acquisition from the new viewer.

## Physiological branch

Signals are centered using the corresponding five-second resting baseline. EEG is resampled to 200 Hz; features include relative log power and differential entropy in six bands spanning 1–45 Hz, plus Hjorth activity, mobility, and complexity.

For each fNIRS channel, six inputs—HbO, HbR, HbT, and absorbance at 780, 805, and 830 nm—are summarized by mean, standard deviation, slope, skewness, and kurtosis.

| Component | Configuration |
| --- | --- |
| Temporal context | Previous, current, and following second; edge padding |
| EEG input | 64 channels × 45 features |
| fNIRS input | 51 channels × 90 features |
| Graph encoders | Learned adjacency; identity, first-order, and second-order supports |
| Cross-modal attention | Bidirectional, four heads; 32-dimensional channel embeddings in the fold models |
| Regression | Mean/max pooling, multilayer regressor, sigmoid output |
| Fold training | MSE + 0.01 × contrastive alignment; dropout 0.7; AdamW; early stopping on validation MSE |

Feature-standardization statistics come from the relevant training participants. Targets are scaled to `[0, 1]` for learning and predictions transformed back to `[1, 255]`.

## Fixed fusion

```text
prediction = [0.99, 0.92] * video_time_prior
           + [0.01, 0.08] * eeg_fnirs_prediction
# Target order: [valence, arousal]
```

The weights remain unchanged on the external cohort. Resting-output calibration is disabled in this configuration.

## Information boundary

The prior excludes held-out participants' labels. The physiological branch uses the new viewer's signals. The following-second context makes prediction **offline**; there is no temporal-lag compensation for the fNIRS haemodynamic delay.

Checkpoint and weight selection were not fully nested. The experiments evaluate one physiological architecture and do not isolate EEG, fNIRS, graph, or attention contributions. Their outcomes neither establish nor rule out independent affective information in either modality.

[See how the components compare →](../research/evidence.md)
