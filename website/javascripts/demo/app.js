(() => {
  'use strict';
  const root = document.getElementById('vtp-demo');
  if (!root) return;
  const workerURL = new URL('worker.js', document.currentScript.src);
  const zh = root.dataset.language === 'zh';
  const $ = id => document.getElementById(`demo-${id}`);
  const text = zh ? {
    ready: '正在准备公开真实样本与训练好的模型。', changed: '设置已改变，请重新运行。', stopped: '已停止，计算会话已释放。',
    downloading: '正在下载并校验真实模型和 30 秒 EEG–fNIRS 样本…', reading: '正在本机读取和验证文件…', loading: '正在加载浏览器推理运行库和训练好的模型…', computing: '正在使用本机算力计算…',
    done: '真实模型推理完成；计算和预测均在本机完成。', local: '本地 CPU · 真实模型推理', explore: ' · 探索权重',
    valence: '效价', arousal: '唤醒度', priorLabel: '先验', physiology: '生理', fusion: '融合', rounded: '取整输出', time: '时间 (s)',
    localNote: '本机执行 {count} 个模型的生理集成、先验查询与固定融合。',
    fallback: '使用 best_v3.pt 回退检查点，结果不对应报告的 27.72 MAE。',
    download: '演示资源下载失败，请检查网络后重试。', manifest: '演示资源清单不匹配，请刷新页面重试。', integrity: '演示资源校验失败，请刷新后重试。', files: '请先选择本地模型文件和特征文件。', file_size: '单个文件不能超过 64 MB。', json: '文件不是有效 JSON。',
    model_format: '模型文件格式不匹配，请用仓库导出程序重新准备。', model_contract: '模型的输入、输出或标准化配置与此页面不匹配。',
    input_format: '特征文件格式不匹配，请选择导出的 .vtp-input.json 文件。', input_rows: '输入应为同一试次的 1–300 个连续秒，样本编号与时间须一致。',
    feature_shape: '特征维度错误：每秒需要 EEG 64×45 和 fNIRS 51×90。', feature_value: '特征包含无效数值。',
    prior: '模型包中的先验无效。', unknown_video: '模型包没有所选视频的先验。', predictions: '模型没有返回有效的效价与唤醒度预测。',
    weights: '先验权重必须在 0–1 之间。', runtime: '无法完成推理，请检查模型包和浏览器是否支持 WebAssembly。',
    unsupported: '当前浏览器不支持后台计算线程，请使用较新的浏览器。',
  } : {
    ready: 'Preparing real sample data and trained models.', changed: 'Settings changed. Run again to update the result.', stopped: 'Stopped. The computation session has been released.',
    downloading: 'Downloading and verifying trained models and 30 seconds of real EEG–fNIRS data…', reading: 'Reading and validating files on this computer…', loading: 'Loading the browser runtime and trained models…', computing: 'Computing on this computer…',
    done: 'Model inference complete. Computation and predictions stayed on this computer.', local: 'Local CPU · trained model', explore: ' · exploratory weights',
    valence: 'Valence', arousal: 'Arousal', priorLabel: 'Prior', physiology: 'Physiology', fusion: 'Fusion', rounded: 'Rounded output', time: 'Time (s)',
    localNote: 'The {count}-model physiological ensemble, prior lookup, and fusion ran locally.',
    fallback: 'Uses the best_v3.pt fallback, not the ensemble behind the reported 27.72 MAE.',
    download: 'Demo download failed. Check your connection and retry.', manifest: 'The demo manifest is incompatible. Refresh and retry.', integrity: 'Demo asset verification failed. Refresh and retry.', files: 'Select a local model file and a feature file first.', file_size: 'Each file must be at most 64 MB.', json: 'The file is not valid JSON.',
    model_format: 'Unsupported model file. Prepare it with the repository exporter.', model_contract: 'The model input, output, or standardization contract is incompatible.',
    input_format: 'Unsupported features. Select an exported .vtp-input.json file.', input_rows: 'Provide 1–300 consecutive seconds from one trial, with matching sample IDs and timestamps.',
    feature_shape: 'Expected EEG 64×45 and fNIRS 51×90 features per second.', feature_value: 'Features contain invalid numbers.',
    prior: 'The model contains an invalid prior.', unknown_video: 'The model has no prior for this video.', predictions: 'The model returned invalid valence–arousal predictions.',
    weights: 'Prior weights must be between 0 and 1.', runtime: 'Inference failed. Check the model package and browser WebAssembly support.',
    unsupported: 'This browser does not support background workers. Use a recent browser.',
  };
  let worker = null;
  let result = null;
  let runNumber = 0;
  const weights = () => [Number($('valence').value), Number($('arousal').value)];
  const mode = () => $('mode').value;
  function status(message, state = '') { $('status').textContent = message; $('status').dataset.state = state; }
  function setBusy(busy) {
    $('settings').disabled = busy;
    $('run').disabled = busy;
    $('stop').disabled = !busy;
    $('progress').hidden = !busy;
    root.setAttribute('aria-busy', String(busy));
  }
  function terminate() { if (worker) worker.terminate(); worker = null; runNumber++; setBusy(false); }
  function clearResult() {
    result = null;
    $('plots').hidden = true; $('empty').hidden = false; $('table-details').hidden = true;
    $('empty').textContent = zh ? '等待真实模型推理结果。' : 'Waiting for trained-model predictions.';
    $('csv').disabled = true; $('json').disabled = true;
    for (const id of ['sample-count', 'time', 'correction']) $(id).textContent = '—';
    $('badge').textContent = text.local;
    $('result-note').textContent = mode() === 'public' ? (zh ? '公开真实样本：MER-PS 训练/验证集，30 秒 EEG–fNIRS 特征。' : 'Real sample: 30 seconds of EEG–fNIRS features from MER-PS training/validation data.') : (zh ? '选择本地真实模型和数据后运行，查看逐秒预测。' : 'Load your trained model and real data to see per-second predictions.');
  }
  function changed() {
    terminate(); clearResult();
    $('public-settings').hidden = mode() !== 'public';
    $('local-settings').hidden = mode() !== 'local';
    $('valence-value').value = Number($('valence').value).toFixed(2);
    $('arousal-value').value = Number($('arousal').value).toFixed(2);
    status(text.changed);
  }
  let chartWidth = 640;
  const xPos = (i, n) => 46 + (n > 1 ? i / (n - 1) : 0.5) * (chartWidth - 66);
  const yPos = value => 190 - (value - 1) / 254 * 150;
  function plot(target) {
    const n = result.timestamps.length;
    const trace = (name, values) => {
      if (n === 1) return `<circle class="trace-${name}" cx="${xPos(0, n)}" cy="${yPos(values[0][target])}" r="3" fill="none"/>`;
      const points = values.map((pair, i) => `${xPos(i, n).toFixed(2)},${yPos(pair[target]).toFixed(2)}`).join(' ');
      return `<polyline class="trace trace-${name}" points="${points}"/>`;
    };
    const title = target === 0 ? text.valence : text.arousal;
    const ticks = [1, 64, 128, 192, 255].map(value => `<line class="grid" x1="46" x2="${chartWidth - 20}" y1="${yPos(value)}" y2="${yPos(value)}"/><text x="38" y="${yPos(value) + 4}" text-anchor="end">${value}</text>`).join('');
    const indices = [...new Set([0, Math.floor((n - 1) / 2), n - 1])];
    const times = indices.map(i => `<text x="${xPos(i, n)}" y="207" text-anchor="middle">${result.timestamps[i]}</text>`).join('');
    return `<svg viewBox="0 0 ${chartWidth} 230" role="img" aria-label="${title}: ${text.priorLabel}, ${text.physiology}, ${text.fusion}"><title>${title}</title><text class="plot-title" x="46" y="22">${title}</text>${ticks}${trace('physiology', result.physiology)}${trace('prior', result.prior)}${trace('fusion', result.floating)}<line class="cursor-line" x1="46" x2="46" y1="40" y2="190"/>${times}<text x="${(chartWidth + 26) / 2}" y="225" text-anchor="middle">${text.time}</text></svg>`;
  }
  function drawPlots() {
    if (!result) return;
    chartWidth = Math.max(280, Math.round($('valence-plot').clientWidth));
    $('valence-plot').innerHTML = plot(0); $('arousal-plot').innerHTML = plot(1);
    inspect();
  }
  function inspect() {
    if (!result) return;
    const i = Number($('cursor').value);
    $('cursor-time').value = `${result.timestamps[i]} s`;
    const x = xPos(i, result.timestamps.length);
    root.querySelectorAll('.cursor-line').forEach(line => { line.setAttribute('x1', x); line.setAttribute('x2', x); });
    $('inspection').replaceChildren();
    for (let target = 0; target < 2; target++) {
      const row = document.createElement('div');
      row.textContent = `${target === 0 ? text.valence : text.arousal}: ${text.priorLabel} ${result.prior[i][target].toFixed(2)} · ${text.physiology} ${result.physiology[i][target].toFixed(2)} · ${text.fusion} ${result.floating[i][target].toFixed(2)} → ${result.rounded[i][target]}`;
      $('inspection').append(row);
    }
  }
  function render() {
    $('empty').hidden = true; $('plots').hidden = false; $('table-details').hidden = false;
    $('csv').disabled = false; $('json').disabled = false;
    const n = result.timestamps.length;
    $('sample-count').textContent = String(n);
    $('time').textContent = `${result.totalMs.toFixed(1)} ms`;
    $('time').title = `Inference / fusion: ${result.computeMs.toFixed(2)} ms`;
    $('correction').textContent = [0, 1].map(t => (result.floating.reduce((sum, p, i) => sum + Math.abs(p[t] - result.prior[i][t]), 0) / n).toFixed(2)).join(' / ');
    $('badge').textContent = text.local + ((result.weights[0] !== 0.99 || result.weights[1] !== 0.92) ? text.explore : '');
    $('result-note').textContent = text.localNote.replace('{count}', result.modelInfo.count) + (result.modelInfo.fullCheckpoint === 'best_v3.pt' ? ' ' + text.fallback : '');
    $('cursor').max = String(n - 1); $('cursor').value = '0'; drawPlots();
    const headers = [text.time, `${text.priorLabel} V`, `${text.physiology} V`, `${text.rounded} V`, `${text.priorLabel} A`, `${text.physiology} A`, `${text.rounded} A`];
    const table = $('table'); table.replaceChildren();
    const head = table.createTHead().insertRow();
    headers.forEach(title => { const th = document.createElement('th'); th.scope = 'col'; th.textContent = title; head.append(th); });
    const body = table.createTBody();
    for (let i = 0; i < Math.min(n, 20); i++) {
      const row = body.insertRow();
      [result.timestamps[i], result.prior[i][0].toFixed(2), result.physiology[i][0].toFixed(2), result.rounded[i][0], result.prior[i][1].toFixed(2), result.physiology[i][1].toFixed(2), result.rounded[i][1]].forEach(v => { row.insertCell().textContent = String(v); });
    }
  }
  function download(kind) {
    if (!result) return;
    let payload;
    if (kind === 'json') payload = JSON.stringify({format: 'vtp-browser-result-v1', ...result}, null, 2);
    else {
      const columns = ['mode', 'backend', 'valence_prior_weight', 'arousal_prior_weight', 'sample_id', 'timestamp', 'prior_valence', 'prior_arousal', 'physiology_valence', 'physiology_arousal', 'fusion_valence_float', 'fusion_arousal_float', 'valence', 'arousal'];
      const rows = result.sample_ids.map((id, i) => [result.mode, result.backend, ...result.weights, id, result.timestamps[i], ...result.prior[i], ...result.physiology[i], ...result.floating[i], ...result.rounded[i]]);
      payload = [columns, ...rows].map(row => row.map(v => `"${String(v).replaceAll('"', '""')}"`).join(',')).join('\r\n');
    }
    const url = URL.createObjectURL(new Blob([payload], {type: kind === 'json' ? 'application/json' : 'text/csv;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = `vtp-${result.mode}-predictions.${kind}`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('form').addEventListener('submit', event => {
    event.preventDefault();
    terminate(); clearResult();
    if (!globalThis.Worker) { status(text.unsupported, 'error'); return; }
    if (mode() === 'local' && (!$('model').files.length || !$('input').files.length)) { status(text.files, 'error'); return; }
    const serial = runNumber;
    try { worker = new Worker(workerURL); } catch { status(text.unsupported, 'error'); return; }
    setBusy(true); $('progress').value = 0; status(text.computing);
    worker.onmessage = ({data}) => {
      if (serial !== runNumber) return;
      if (data.type === 'progress') { status(text[data.stage] || text.computing); $('progress').value = data.value; }
      if (data.type === 'error') { terminate(); clearResult(); status(text[data.code] || text.runtime, 'error'); }
      if (data.type === 'result') { terminate(); result = data.result; render(); status(text.done, 'success'); }
    };
    worker.onerror = () => { if (serial === runNumber) { terminate(); clearResult(); status(text.runtime, 'error'); } };
    worker.postMessage({mode: mode(), weights: weights(),
      modelFile: $('model').files[0], inputFile: $('input').files[0]});
  });
  $('stop').addEventListener('click', () => { terminate(); clearResult(); status(text.stopped); });
  for (const id of ['mode', 'model', 'input', 'valence', 'arousal']) $(id).addEventListener('input', changed);
  $('reset').addEventListener('click', () => { $('valence').value = '0.99'; $('arousal').value = '0.92'; changed(); });
  $('cursor').addEventListener('input', inspect);
  $('csv').addEventListener('click', () => download('csv'));
  $('json').addEventListener('click', () => download('json'));
  window.addEventListener('pagehide', terminate);
  window.addEventListener('resize', drawPlots);
  clearResult(); status(text.ready);
  $('form').requestSubmit();
})();
