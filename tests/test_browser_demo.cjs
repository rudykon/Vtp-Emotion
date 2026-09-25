'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../website/javascripts/demo/core.js');
const input = () => ({format: 'vtp-browser-input-v1', feature_version: core.VERSION,
  video: 1, timestamps: [0, 1], sample_ids: ['test_1_V01_T000', 'test_1_V01_T001'],
  eeg: Array.from({length: 2}, () => Array.from({length: 64}, () => Array(45).fill(0))),
  fnirs: Array.from({length: 2}, () => Array.from({length: 51}, () => Array(90).fill(0))),
});
const model = () => ({format: 'vtp-browser-model-v1', feature_version: core.VERSION,
  input_shapes: {fnirs: [51, 90], eeg: [64, 45]}, label_scale: [1, 255], resting_bias_shrink: [0, 0],
  model_count: 6, full_checkpoint: 'final_v3.pt', physiology_onnx_base64: 'AA==',
  default_weights: [0.99, 0.92], prior: {'1': [[100, 120], [130, 160]]},
});
const throwsCode = (fn, code) => assert.throws(fn, error => error.code === code);

test('rounding follows NumPy ties-to-even, including half-integer boundaries', () => {
  assert.deepEqual([1.5, 2.5, 3.5, 254.5, -1.5, -2.5].map(core.roundEven), [2, 2, 4, 254, -2, -2]);
});
test('fusion agrees with float32 reference and exact branch endpoints', () => {
  const result = core.fuse([[200.1, 35.2]], [[20.3, 239.7]], [0.99, 0.92]);
  assert.deepEqual(result.floating, [[198.30201721191406, 51.55999755859375]]);
  assert.deepEqual(result.rounded, [[198, 52]]);
  assert.deepEqual(core.fuse([[1, 255]], [[100, 200]], [1, 0]).rounded, [[1, 200]]);
  throwsCode(() => core.fuse([[100, 100]], [[NaN, 100]], [0.99, 0.92]), 'predictions');
  throwsCode(() => core.fuse([[100, 100]], null, [0.99, 0.92]), 'predictions');
  throwsCode(() => core.fuse([[100, 100]], [[100, 100]], [1.01, 0]), 'weights');
});
test('input contract rejects misaligned rows, malformed features, and non-finite values', () => {
  assert.equal(core.validateInput(input()).eeg.length, 2 * 64 * 45);
  let invalid = input(); invalid.timestamps[1] = 8;
  throwsCode(() => core.validateInput(invalid), 'input_rows');
  invalid = input(); invalid.sample_ids[1] = 'test_2_V01_T001';
  throwsCode(() => core.validateInput(invalid), 'input_rows');
  invalid = input(); invalid.eeg[0].pop();
  throwsCode(() => core.validateInput(invalid), 'feature_shape');
  invalid = input(); invalid.fnirs[0][0][0] = Infinity;
  throwsCode(() => core.validateInput(invalid), 'feature_value');
  invalid = input(); invalid.fnirs[0][0][0] = 1e100;
  throwsCode(() => core.validateInput(invalid), 'feature_value');
  invalid = input(); invalid.feature_version = 'other';
  throwsCode(() => core.validateInput(invalid), 'input_format');
});
test('model contract accepts reordered JSON keys and rejects calibration or prior mismatches', () => {
  assert.equal(core.validateModel(model()).model_count, 6);
  let invalid = model(); invalid.resting_bias_shrink = [0.1, 0];
  throwsCode(() => core.validateModel(invalid), 'model_contract');
  invalid = model(); invalid.prior['1'][0][0] = 300;
  throwsCode(() => core.validateModel(invalid), 'prior');
  invalid = model(); invalid.input_shapes.eeg = [64, 44];
  throwsCode(() => core.validateModel(invalid), 'model_contract');
});
test('prior lookup clamps the final second and rejects an unknown video', () => {
  assert.deepEqual(core.lookupPrior(model(), {video: 1, timestamps: [0, 1, 2]}), [[100, 120], [130, 160], [130, 160]]);
  throwsCode(() => core.lookupPrior(model(), {video: 15, timestamps: [0]}), 'unknown_video');
});
test('published demo assets match the feature contract, provenance, and integrity manifest', () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const {createHash} = require('node:crypto');
  const directory = path.join(__dirname, '../website/assets/demo');
  const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'manifest.json'), 'utf8'));
  const assets = {};
  for (const key of ['model', 'input']) {
    const entry = manifest.assets[key];
    const bytes = fs.readFileSync(path.join(directory, entry.file));
    assert.equal(bytes.length, entry.bytes);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), entry.sha256);
    assets[key] = JSON.parse(bytes);
  }
  const model = core.validateModel(assets.model);
  const features = core.validateInput(assets.input);
  assert.equal(model.model_count, 6);
  assert.equal(model.full_checkpoint, 'final_v3.pt');
  assert.equal(features.count, manifest.source.sample_count);
  assert.equal(features.count, 30);
  assert.equal(core.lookupPrior(model, assets.input).length, features.count);
  assert.deepEqual(assets.input.source, manifest.source);
  assert.equal(assets.input.source.license, 'CC-BY-NC-SA-4.0');
  assert.equal(assets.input.source.split, 'training/validation');
});

const journey = require('../website/javascripts/demo/journey.js');
test('journey maps score endpoints and the documented neutral display band without changing scores', () => {
  assert.deepEqual([journey.snapshot([1, 1]).x, journey.snapshot([1, 1]).y], [0, 1]);
  assert.deepEqual([journey.snapshot([255, 255]).x, journey.snapshot([255, 255]).y], [1, 0]);
  assert.equal(journey.snapshot([128, 128]).x, 0.5);
  assert.equal(journey.snapshot([116, 140]).valence, 0);
  assert.equal(journey.snapshot([116, 140]).arousal, 0);
  assert.equal(journey.snapshot([115, 141]).valence, -1);
  assert.equal(journey.snapshot([115, 141]).arousal, 1);
  assert.throws(() => journey.snapshot([128, Infinity]));
});
test('journey highlights the largest two-dimensional step and handles short or flat recordings', () => {
  const pairs = [[128, 128], [140, 140], [141, 100], [160, 110]];
  const original = structuredClone(pairs);
  const summary = journey.summarize(pairs);
  assert.equal(summary.moment, 2);
  assert.deepEqual(summary.delta, [32, -18]);
  assert.deepEqual(pairs, original);
  assert.deepEqual(journey.summarize([[128, 128]]), {moment: 0, maxStep: 0, delta: [0, 0]});
  assert.deepEqual(journey.summarize([[130, 130], [130, 130]]), {moment: 0, maxStep: 0, delta: [0, 0]});
});
