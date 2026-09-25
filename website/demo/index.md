---
hide:
  - navigation
  - toc
---

# Browser demo

<p class="demo-eyebrow">Run on your computer</p>
<p class="demo-lead">Real EEG–fNIRS samples and the trained six-model ensemble load automatically. Your CPU predicts per-second valence and arousal in the browser. You can also run inference on your own local files.</p>

<div id="vtp-demo" class="vtp-demo" data-language="en">
<div class="demo-layout">
<form id="demo-form" class="demo-panel demo-controls">
<fieldset id="demo-settings">
<legend>Trained model and real data</legend>
<label for="demo-mode" class="sr-only">Data source</label>
<select id="demo-mode"><option value="public" selected>Real public sample · models included</option><option value="local">Use local model and data files</option></select>
<div id="demo-public-settings">
<p class="demo-note">MER-PS training/validation · test_1 · video 1 · seconds 0–29. The ensemble includes final_v3.pt and five cross-validation models. Every prediction is computed live in your browser.</p>
<p class="demo-note">The first load downloads approximately 19 MB including the runtime. <a href="#sample-source">Sample source and license →</a></p>
</div>
<div id="demo-local-settings" hidden>
<p class="demo-note">Select files prepared with the repository exporter. The model runs on your CPU using WebAssembly; no account or inference server is required.</p>
<label for="demo-model">Model file</label><input type="file" id="demo-model" accept=".json,application/json">
<label for="demo-input">Real-data feature file</label><input type="file" id="demo-input" accept=".json,application/json">
<p class="demo-note">Two local JSON files, up to 64 MB each; 1–300 consecutive seconds from one trial. <a href="#prepare-local-files">How to prepare local files →</a></p>
</div>
<h2 class="demo-subheading">Prior weights</h2>
<label class="demo-range-label" for="demo-valence"><span>Valence</span><output id="demo-valence-value">0.99</output></label>
<input id="demo-valence" type="range" min="0" max="1" step="0.01" value="0.99">
<label class="demo-range-label" for="demo-arousal"><span>Arousal</span><output id="demo-arousal-value">0.92</output></label>
<input id="demo-arousal" type="range" min="0" max="1" step="0.01" value="0.92">
<button type="button" id="demo-reset" class="demo-text-button">Restore fixed weights</button>
<p class="demo-note">Defaults: 0.99 / 0.92. Changed weights are exploratory settings.</p>
</fieldset>
<div class="demo-actions"><button id="demo-run" type="submit" class="md-button md-button--primary">Run model inference</button><button id="demo-stop" type="button" class="md-button" disabled>Stop</button></div>
<p id="demo-status" role="status" aria-live="polite">Preparing real sample data and trained models.</p>
<progress id="demo-progress" max="100" value="0" hidden aria-label="Progress"></progress>
</form>
<section class="demo-panel demo-results" aria-labelledby="demo-results-title">
<div class="demo-results-header"><h2 id="demo-results-title">Prediction trajectories</h2><span id="demo-badge" class="demo-badge">Local CPU · trained model</span></div>
<p id="demo-result-note" class="demo-note">Valence and arousal use the [1, 255] scale. Dashed lines are the prior; the solid teal line is fusion.</p>
<div class="demo-metrics"><div><span>Samples</span><strong id="demo-sample-count">—</strong></div><div><span>Browser time</span><strong id="demo-time">—</strong></div><div><span>Mean absolute correction</span><strong id="demo-correction">—</strong></div></div>
<p class="demo-note">End-to-end time includes downloads, file parsing, and model initialization.</p>
<div class="demo-legend"><span class="prior">Video–time prior</span><span class="physiology">Physiological branch</span><span class="fusion">Fixed fusion</span></div>
<p id="demo-empty" class="demo-empty">Loading real models and sample data. Predictions appear when local computation finishes.</p>
<div id="demo-plots" hidden>
<div id="demo-valence-plot" class="demo-plot"></div><div id="demo-arousal-plot" class="demo-plot"></div>
<label class="demo-range-label" for="demo-cursor"><span>Inspect a second</span><output id="demo-cursor-time">0 s</output></label>
<input id="demo-cursor" type="range" min="0" max="119" value="0" step="1">
<div id="demo-inspection" class="demo-inspection" aria-live="polite"></div>
</div>
<div class="demo-actions demo-downloads"><button id="demo-csv" type="button" class="md-button" disabled>Download CSV</button><button id="demo-json" type="button" class="md-button" disabled>Download JSON</button></div>
</section>
</div>
<details id="demo-table-details" class="demo-table-details" hidden><summary>Inspect individual predictions</summary><p class="demo-note">Showing up to 20 rows. Downloads contain every sample, floating-point components, and rounded predictions.</p><div class="demo-table-scroll"><table id="demo-table"></table></div></details>
</div>

## Sample source and license { #sample-source }

The default sample is adapted from [MER-PS training/validation data](https://huggingface.co/datasets/MER-PS/MER-PS-trainval), credited to the MER-PS dataset creators. It contains real physiological features for anonymized subject test_1, video 1, seconds 0–29, after baseline correction and contextual feature extraction. This development-set excerpt demonstrates inference; it is not independent held-out evaluation or evidence of accuracy.

The published sample and inference model use [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) for non-commercial scientific research. Retain attribution and the license link, identify modifications, and share adaptations under the same license. <a href="../assets/demo/NOTICE.txt">Full provenance notice</a> · <a href="../assets/demo/manifest.json">Asset manifest and checksums</a>

## Use your own local files { #prepare-local-files }

Run these commands in a local checkout with the data and checkpoints already available. They create private files under artifacts/browser/.

```bash
.venv/bin/pip install -r requirements-demo.txt
.venv/bin/python scripts/export_browser_demo.py model
.venv/bin/python scripts/export_browser_demo.py input \
  --data-root data/MER_PS_trainval --subject test_1 \
  --video 1 --start 0 --count 60
```

`artifacts/browser/model.vtp-model.json` + `artifacts/browser/input.vtp-input.json`

Feature preparation uses the existing Python pipeline, including baseline correction and previous/current/following-second context. The browser performs checkpoint-specific standardization, the six-model ensemble, prior lookup, fusion, and round-to-even output conversion. Raw MAT files and PyTorch ZIP bundles cannot be selected directly.

## Interpretation

This is offline prediction for new viewers of familiar videos. The page runs the trained six-model ensemble on features extracted from real EEG–fNIRS recordings. The exporter records whether it used final_v3.pt or the best_v3.pt fallback; fallback results do not reproduce the reported 27.72 MAE.

Public mode downloads the demo model, real sample, and runtime from this site, then runs inference in your browser. Local mode reads only the files you select; files and predictions are not uploaded. Closing or reloading the tab releases the computation session.

<a href="../licenses/onnxruntime.txt">ONNX Runtime license</a> · <a href="../licenses/onnxruntime-third-party.txt">Third-party notices</a> · [Browser demo source](https://github.com/rudykon/Vtp-Emotion/tree/main/website/javascripts/demo)
