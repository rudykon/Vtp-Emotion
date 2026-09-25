/* Pure numerical and input-validation helpers; no network or storage access. */
(() => {
  'use strict';
  const VERSION = 'merps-context-r1-baseline-v1';
  const MAX_SAMPLES = 300;
  const f32 = Math.fround;
  const fail = (code) => { const error = new Error(code); error.code = code; throw error; };
  const finite = (x) => typeof x === 'number' && Number.isFinite(x);
  const pair = (x) => Array.isArray(x) && x.length === 2 && x.every(finite);
  const clip = (x) => Math.min(255, Math.max(1, x));
  function validateWeights(weights) {
    if (!pair(weights) || weights.some(x => x < 0 || x > 1)) fail('weights');
    return weights.map(f32);
  }
  function roundEven(x) {
    const lo = Math.floor(x);
    return x - lo === 0.5 ? lo + (Math.abs(lo) % 2) : Math.round(x);
  }
  function fuse(prior, physiology, weights) {
    const w = validateWeights(weights);
    if (!Array.isArray(prior) || !Array.isArray(physiology) || prior.length !== physiology.length || !prior.length) fail('predictions');
    const floating = prior.map((p, i) => {
      if (!pair(p) || !pair(physiology[i]) || [...p, ...physiology[i]].some(v => v < 1 || v > 255)) fail('predictions');
      return p.map((v, t) => f32(f32(w[t] * f32(v)) + f32(f32(1 - w[t]) * f32(physiology[i][t]))));
    });
    return {floating, rounded: floating.map(p => p.map(v => clip(roundEven(v))))};
  }
  function validateModel(model) {
    if (!model || model.format !== 'vtp-browser-model-v1' || model.feature_version !== VERSION) fail('model_format');
    if (JSON.stringify(model.input_shapes?.eeg) !== '[64,45]' || JSON.stringify(model.input_shapes?.fnirs) !== '[51,90]' ||
        JSON.stringify(model.label_scale) !== '[1,255]' || JSON.stringify(model.resting_bias_shrink) !== '[0,0]') fail('model_contract');
    if (!Number.isInteger(model.model_count) || model.model_count < 1 || model.model_count > 8 ||
        typeof model.full_checkpoint !== 'string' || !['final_v3.pt', 'best_v3.pt'].includes(model.full_checkpoint)) fail('model_contract');
    if (typeof model.physiology_onnx_base64 !== 'string' || !model.physiology_onnx_base64.length || model.physiology_onnx_base64.length > 48 * 1024 * 1024) fail('model_format');
    if (!model.prior || typeof model.prior !== 'object' || Array.isArray(model.prior)) fail('prior');
    for (const [key, trajectory] of Object.entries(model.prior)) {
      if (!/^(?:[1-9]|1[0-5])$/.test(key) || !Array.isArray(trajectory) || !trajectory.length || trajectory.length > 10000 ||
          !trajectory.every(p => pair(p) && p.every(v => v >= 1 && v <= 255))) fail('prior');
    }
    if (!Object.keys(model.prior).length) fail('prior');
    validateWeights(model.default_weights);
    return model;
  }
  function flattenFeatures(values, count, nodes, features) {
    if (!Array.isArray(values) || values.length !== count) fail('feature_shape');
    const out = new Float32Array(count * nodes * features);
    let offset = 0;
    for (const sample of values) {
      if (!Array.isArray(sample) || sample.length !== nodes) fail('feature_shape');
      for (const channel of sample) {
        if (!Array.isArray(channel) || channel.length !== features) fail('feature_shape');
        for (const value of channel) {
          if (!finite(value) || !Number.isFinite(f32(value))) fail('feature_value');
          out[offset++] = value;
        }
      }
    }
    return out;
  }
  function validateInput(input) {
    if (!input || input.format !== 'vtp-browser-input-v1' || input.feature_version !== VERSION) fail('input_format');
    const n = input.sample_ids?.length;
    if (!Array.isArray(input.sample_ids) || !Number.isInteger(n) || n < 1 || n > MAX_SAMPLES ||
        !Array.isArray(input.timestamps) || input.timestamps.length !== n || !Number.isInteger(input.video) || input.video < 1 || input.video > 15) fail('input_rows');
    let subject;
    input.sample_ids.forEach((id, index) => {
      const match = typeof id === 'string' && id.match(/^([A-Za-z0-9][A-Za-z0-9_-]*)_V(\d+)_T(\d+)$/);
      const time = input.timestamps[index];
      if (!match || !Number.isSafeInteger(time) || time < 0 || Number(match[2]) !== input.video || Number(match[3]) !== time ||
          (index && (match[1] !== subject || time !== input.timestamps[index - 1] + 1))) fail('input_rows');
      subject = match[1];
    });
    return {count: n, eeg: flattenFeatures(input.eeg, n, 64, 45), fnirs: flattenFeatures(input.fnirs, n, 51, 90)};
  }
  function lookupPrior(model, input) {
    const trajectory = model.prior[String(input.video)];
    if (!trajectory) fail('unknown_video');
    return input.timestamps.map(t => trajectory[Math.min(t, trajectory.length - 1)].map(f32));
  }
  function synthetic({count = 120, seed = 2026, scenario = 'wave'}) {
    if (!Number.isInteger(count) || count < 30 || count > 240 || !Number.isInteger(seed) || seed < 0 || seed > 4294967295 ||
        !['wave', 'shift', 'pulse'].includes(scenario)) fail('example_settings');
    let state = seed >>> 0;
    const random = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296; };
    const noise = () => random() + random() + random() + random() - 2;
    const base = Array.from({length: count}, (_, t) => {
      const x = t / Math.max(1, count - 1);
      const pulse = Math.exp(-(((x - 0.55) / 0.14) ** 2));
      return scenario === 'shift' ? [95 + 60 / (1 + Math.exp(-(x - 0.48) * 18)), 90 + 80 / (1 + Math.exp(-(x - 0.55) * 18))] :
        scenario === 'pulse' ? [145 - 55 * pulse, 75 + 110 * pulse] :
        [128 + 46 * Math.sin(2 * Math.PI * x), 125 + 43 * Math.cos(3 * Math.PI * x)];
    });
    const participants = Array.from({length: 12}, () => {
      const bias = [noise() * 12, noise() * 12];
      return base.map(p => p.map((v, target) => f32(clip(v + bias[target] + noise() * 15))));
    });
    const median = base.map((_, i) => [0, 1].map(target => {
      const values = participants.map(p => p[i][target]).sort((a, b) => a - b);
      return f32((values[5] + values[6]) / 2);
    }));
    const prior = median.map((_, i) => [0, 1].map(target => {
      const window = median.slice(Math.max(0, i - 3), Math.min(count, i + 4));
      return f32(window.reduce((sum, row) => sum + row[target], 0) / window.length);
    }));
    // These are simulated branch outputs, not trained-network predictions.
    const physiology = base.map((p, i) => p.map((v, target) => f32(clip(v + 28 * Math.sin(i / 8 + target) + noise() * 26))));
    return {prior, physiology, timestamps: Array.from({length: count}, (_, i) => i),
      sample_ids: Array.from({length: count}, (_, i) => `synthetic_V01_T${String(i).padStart(3, '0')}`)};
  }
  const api = {VERSION, MAX_SAMPLES, fail, roundEven, fuse, validateModel, validateInput, lookupPrior, synthetic};
  globalThis.VtpDemoCore = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
