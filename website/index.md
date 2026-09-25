---
hide:
  - toc
---

<section class="project-hero">
  <div class="project-wordmark">
    <img src="assets/brand/wordmark.svg" alt="Vtp-Emotion" width="460" height="94">
  </div>
  <h1>Vtp-Emotion</h1>
  <p class="project-subtitle">Predict emotion for new viewers of familiar videos</p>
  <p class="project-lead">A video–time prior captures the shared affect trajectory. EEG and fNIRS add a small, viewer-specific correction. Explore continuous valence–arousal regression and where its accuracy comes from.</p>
  <div class="project-actions">
    <a class="md-button md-button--primary" href="https://github.com/rudykon/Vtp-Emotion" target="_blank" rel="noopener">View on GitHub</a>
    <a class="md-button" href="guide/method/">Method</a>
    <a class="md-button" href="research/evidence/">Results</a>
    <a class="md-button" href="reference/reproduction/">Reproduce</a>
  </div>
</section>

## Research setting and method

<div class="setting-layout">
<figure class="paper-figure">
  <a href="assets/figures/icassp2027/method_overview.pdf" target="_blank" rel="noopener" aria-label="Video–time prior and EEG–fNIRS fixed fusion (PDF)">
    <img src="assets/figures/icassp2027/method_overview.png" alt="Video–time prior and EEG–fNIRS fixed fusion" loading="lazy">
  </a>
  <figcaption>A shared video–time trajectory and new-viewer physiology feed fixed fusion. Output curves are schematic.</figcaption>
</figure>
  <div>
    <p>When training and evaluation share the same videos, known video identity and playback time provide a strong baseline. Vtp-Emotion separates this shared response from the correction supplied by physiological signals.</p>
    <ul class="fact-list">
      <li><strong>15 familiar videos</strong><span>New viewers; known video and aligned time</span></li>
      <li><strong>1 Hz × 2</strong><span>Valence and arousal on the [1, 255] scale</span></li>
      <li><strong>EEG + fNIRS</strong><span>Graph encoders and cross-modal attention</span></li>
      <li><strong>0.99 / 0.92</strong><span>Fixed prior weights for valence / arousal</span></li>
      <li><strong>Offline prediction</strong><span>Physiology includes the following second</span></li>
    </ul>
  </div>
</div>

## Main findings

| Question | Reported result |
| --- | --- |
| New viewers, five folds | Fusion MAE **29.01**; video–time prior **29.06**; EEG–fNIRS **47.35**. |
| Four additional viewers | Fusion MAE **27.72**; video–time prior **28.04**; EEG–fNIRS **42.75**. |
| Where does accuracy come from? | The prior accounts for **99.73% internally** and **97.89% externally** of the MAE reduction from EEG–fNIRS alone to fusion. |
| Does physiology help everyone? | Fusion lowers MAE for **3 of 4 participants** and **9 of 15 videos** in the external cohort. |

[Read the evaluation protocols and full results →](research/evidence.md)

## Scope

<div class="scope-box">
  <ul>
    <li>Evaluation concerns new viewers of the same 15 videos seen during training.</li>
    <li>Future physiological context makes the current estimator offline.</li>
    <li>Checkpoint and weight selection were not fully nested; gains are descriptive.</li>
    <li>Unseen-video and cross-site transfer have not been evaluated.</li>
  </ul>
</div>
