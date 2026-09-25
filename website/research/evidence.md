# Results

## Prediction accuracy

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

## What explains the error reduction?

On the external cohort, moving from the global constant to video identity reduces overall MAE by **10.97 points**; adding playback time reduces it by another **5.32 points**. Fixed fusion adds **0.32 points** of improvement over the video–time prior. Internally, its increment is only **0.05 points**.

Relative to the reduction from EEG–fNIRS alone to fusion, the prior accounts for **99.73% internally** and **97.89% externally**, computed before display rounding. These are descriptive ratios of error reduction, not a causal decomposition of information in the signals.

<figure class="paper-figure">
<a href="../../assets/figures/icassp2027/external_source_decomposition.pdf">
    <img src="../../assets/figures/icassp2027/external_source_decomposition.png" alt="External-cohort overall MAE, paired fusion gains for all four participants and fifteen videos, and errors across ten normalized playback-time bins" width="100%">
  </a>
<figcaption>Figure 2 | Source contributions and heterogeneous fusion gains. Positive prior-minus-fusion MAE favors fusion; circles mark gains and crosses mark losses.</figcaption>
</figure>

| External-cohort comparison: fusion vs. prior | Observation |
| --- | --- |
| Participants | Lower MAE for 3 of 4 |
| Videos | Lower MAE for 9 of 15; largest gain +1.31 (V7), largest loss −0.30 (V11) |
| Participant–video trials | Lower MAE in 38 of 60; higher in 22 |
| Normalized playback time | Higher MAE in the first 3 bins; lower in the remaining 7 |
| Video × time cells | Lower MAE in 76 of 150 cells, equal in 7, higher in 67 |

Time conditioning also helps unevenly. In the first normalized bin, video identity and the video–time prior yield MAEs of **45.53** and **13.40**. Video identity is better in each of the final five bins: the prior's pooled **11.89-point reduction** in the first half outweighs its **1.33-point increase** in the second half.

<figure class="paper-figure">
<a href="../../assets/figures/icassp2027/external_diagnostics.pdf">
    <img src="../../assets/figures/icassp2027/external_diagnostics.png" alt="Fixed-fusion prediction densities for valence and arousal and prior/fusion MAE heatmaps over fifteen videos and ten time bins" width="100%">
  </a>
<figcaption>Figure 3 | Diagnostics using all 6,143 external samples. Prediction densities share a log-count scale; heatmaps share a 0–65 MAE scale.</figcaption>
</figure>

Prediction ranges are compressed, and the prior and fusion share **9 of their 10 highest-error cells**. Much of the prior's error structure remains after fusion.

<details markdown="1">
<summary><strong>Post hoc weight sensitivity</strong></summary>

A diagnostic sweep over prior weights from 0 to 1 in steps of 0.01 finds internal target-wise minima at `[0.99, 0.92]`. At these weights, fusion improves on the prior in only 3 of 5 folds. This sweep does not reproduce the original selection procedure. External-cohort minima shift to `[0.83, 0.82]` (MAE 26.91), but use held-out outcomes and are diagnostic only. All main results retain the original fixed weights `[0.99, 0.92]`.

</details>

These analyses are descriptive. With only four external participant clusters, correlated seconds are not treated as independent replicates for significance testing.
