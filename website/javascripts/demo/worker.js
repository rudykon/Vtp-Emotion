/* All file parsing and inference happen in this disposable background worker. */
'use strict';
importScripts('core.js');
const core = self.VtpDemoCore;
const runtimeBase = new URL('../vendor/onnxruntime/', self.location.href).href;
const progress = (stage, value) => postMessage({type: 'progress', stage, value});
async function readJSON(file, limit) {
  if (!(file instanceof Blob) || !file.size) core.fail('files');
  if (file.size > limit * 1024 * 1024) core.fail('file_size');
  try { return JSON.parse(await file.text()); } catch { core.fail('json'); }
}
self.onmessage = async ({data}) => {
  let session;
  const start = performance.now();
  try {
    let result, modelInfo = null, computeMs;
    if (data.mode === 'synthetic') {
      progress('computing', 35);
      const computeStart = performance.now();
      result = core.synthetic(data.settings);
      Object.assign(result, core.fuse(result.prior, result.physiology, data.weights));
      computeMs = performance.now() - computeStart;
    } else if (data.mode === 'local') {
      progress('reading', 10);
      const model = core.validateModel(await readJSON(data.modelFile, 64));
      const input = await readJSON(data.inputFile, 64);
      const features = core.validateInput(input);
      const prior = core.lookupPrior(model, input);
      progress('loading', 25);
      importScripts(runtimeBase + 'ort.wasm.min.js');
      ort.env.wasm.wasmPaths = runtimeBase;
      // GitHub Pages has no cross-origin-isolation headers. Run one WASM thread
      // inside this worker; the page stays responsive and can terminate it.
      ort.env.wasm.numThreads = 1;
      ort.env.wasm.proxy = false;
      let decoded;
      try { decoded = atob(model.physiology_onnx_base64); } catch { core.fail('model_format'); }
      const bytes = Uint8Array.from(decoded, ch => ch.charCodeAt(0));
      session = await ort.InferenceSession.create(bytes, {executionProviders: ['wasm'], graphOptimizationLevel: 'all'});
      if (session.inputNames.length !== 2 || !session.inputNames.includes('eeg') || !session.inputNames.includes('fnirs') ||
          session.outputNames.length !== 1 || session.outputNames[0] !== 'physiology') core.fail('model_contract');
      const physiology = [];
      const computeStart = performance.now();
      for (let offset = 0; offset < features.count; offset += 16) {
        const n = Math.min(16, features.count - offset);
        const output = await session.run({
          eeg: new ort.Tensor('float32', features.eeg.slice(offset * 2880, (offset + n) * 2880), [n, 64, 45]),
          fnirs: new ort.Tensor('float32', features.fnirs.slice(offset * 4590, (offset + n) * 4590), [n, 51, 90]),
        });
        const prediction = output.physiology;
        if (prediction.type !== 'float32' || prediction.dims.length !== 2 || prediction.dims[0] !== n || prediction.dims[1] !== 2) core.fail('predictions');
        for (let j = 0; j < n; j++) physiology.push([prediction.data[j * 2], prediction.data[j * 2 + 1]]);
        prediction.dispose();
        progress('computing', 40 + 55 * (offset + n) / features.count);
      }
      result = {prior, physiology, timestamps: input.timestamps, sample_ids: input.sample_ids};
      Object.assign(result, core.fuse(prior, physiology, data.weights));
      computeMs = performance.now() - computeStart;
      modelInfo = {count: model.model_count, fullCheckpoint: model.full_checkpoint};
      await session.release();
      session = null;
    } else core.fail('mode');
    postMessage({type: 'result', result: {...result, mode: data.mode, weights: data.weights,
      backend: data.mode === 'local' ? 'onnxruntime-web-1.22.0 / wasm-cpu' : 'synthetic / javascript',
      modelInfo, computeMs, totalMs: performance.now() - start}});
  } catch (error) {
    if (session) { try { await session.release(); } catch {} }
    postMessage({type: 'error', code: error.code || 'runtime', detail: String(error.message || error).slice(0, 240)});
  }
};
