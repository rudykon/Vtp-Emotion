---
hide:
  - navigation
  - toc
---

# Browser demo

<p class="demo-eyebrow">Run on your computer</p>
<p class="demo-lead">Explore fixed fusion with a synthetic example, or load private model and feature files for EEG–fNIRS inference. Computation runs in your browser; selected files are not uploaded.</p>

<div id="vtp-demo" class="vtp-demo" data-language="en">
<div class="demo-layout">
<form id="demo-form" class="demo-panel demo-controls">
<fieldset id="demo-settings">
<legend>Input source</legend>
<label for="demo-mode" class="sr-only">Input source</label>
<select id="demo-mode"><option value="synthetic">Synthetic example</option><option value="local">Local model inference</option></select>
<div id="demo-example-settings">
<p class="demo-note">Illustration only: the trajectories and physiological-branch outputs are generated here. This example does not run a trained neural network or reproduce reported results.</p>
<label for="demo-scenario">Example trajectory</label>
<select id="demo-scenario"><option value="wave">Smooth changes</option><option value="shift">Gradual transition</option><option value="pulse">Short affective event</option></select>
<div class="demo-control-pair"><div><label for="demo-count">Duration</label><select id="demo-count"><option value="60">60 s</option><option value="120" selected>120 s</option><option value="240">240 s</option></select></div><div><label for="demo-seed">Scenario seed</label><input id="demo-seed" type="number" min="0" max="4294967295" step="1" value="2026" required></div></div>
</div>
<div id="demo-local-settings" hidden>
<p class="demo-note">Select files prepared with the repository exporter. The model runs on your CPU using WebAssembly; no account or inference server is required.</p>
<label for="demo-model">Model file</label><input type="file" id="demo-model" accept=".json,application/json">
<label for="demo-input">Feature file</label><input type="file" id="demo-input" accept=".json,application/json">
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
<div class="demo-actions"><button id="demo-run" type="submit" class="md-button md-button--primary">Run locally</button><button id="demo-stop" type="button" class="md-button" disabled>Stop</button></div>
<p id="demo-status" role="status" aria-live="polite">Ready. Choose an input source and run.</p>
<progress id="demo-progress" max="100" value="0" hidden aria-label="Progress"></progress>
</form>
<section class="demo-panel demo-results" aria-labelledby="demo-results-title">
<div class="demo-results-header"><h2 id="demo-results-title">Prediction trajectories</h2><span id="demo-badge" class="demo-badge">Synthetic example</span></div>
<p id="demo-result-note" class="demo-note">Valence and arousal use the [1, 255] scale. Dashed lines are the prior; the solid teal line is fusion.</p>
<div class="demo-metrics"><div><span>Samples</span><strong id="demo-sample-count">—</strong></div><div><span>Browser time</span><strong id="demo-time">—</strong></div><div><span>Mean absolute correction</span><strong id="demo-correction">—</strong></div></div>
<p class="demo-note">End-to-end time includes file parsing and model initialization.</p>
<div class="demo-legend"><span class="prior">Video–time prior</span><span class="physiology">Physiological branch</span><span class="fusion">Fixed fusion</span></div>
<p id="demo-empty" class="demo-empty">Run an example or load your local files to see predictions.</p>
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

## Prepare local files { #prepare-local-files }

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

This is offline prediction for new viewers of familiar videos. A local checkpoint package is required for trained-model inference. The public example is synthetic and is not an accuracy benchmark. The exporter records whether it used final_v3.pt or the best_v3.pt fallback; fallback results do not reproduce the reported 27.72 MAE.

Files are read in this tab and processed locally. Closing or refreshing the page releases the session. Only the inference runtime is downloaded; model parameters are not hosted by this website.

<a href="../licenses/onnxruntime.txt">ONNX Runtime license</a> · <a href="../licenses/onnxruntime-third-party.txt">Third-party notices</a> · [Browser demo source](https://github.com/rudykon/Vtp-Emotion/tree/main/website/javascripts/demo)
