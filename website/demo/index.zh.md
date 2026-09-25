---
hide:
  - navigation
  - toc
---

# 看见一段观影中的情绪变化

<p class="demo-eyebrow">真实观影记录 · 在你的电脑上运行</p>
<p class="demo-lead">观看一段视频时，感受怎样变化？回放一位匿名观众的真实记录，看看模型预测的愉悦程度和活跃程度如何随时间移动。</p>

<div id="vtp-demo" class="vtp-demo" data-language="zh">
<div class="demo-runtime"><p id="demo-status" role="status" aria-live="polite">正在准备真实观影记录与模型…</p><div class="demo-actions"><button id="demo-run" type="submit" form="demo-form" class="md-button">重新计算</button><button id="demo-stop" type="button" class="md-button" disabled>停止计算</button></div><progress id="demo-progress" max="100" value="0" hidden aria-label="Progress"></progress></div>
<div class="journey-context"><div class="journey-scene"><svg viewBox="0 0 200 112" role="img" aria-label="观影场景示意 · 原视频未展示"><rect x="0" y="0" width="200" height="112" rx="16" fill="#172b4d"/><rect x="82" y="14" width="99" height="65" rx="6" fill="#d8eee9"/><rect x="89" y="21" width="85" height="45" rx="3" fill="#a8d6ce"/><path d="m122 31 18 12-18 12z" fill="#0f766e"/><path d="M122 80v10m-18 1h39" stroke="#88acae" stroke-width="4" stroke-linecap="round"/><path d="M16 107V78q0-9 10-9h38q12 0 12 12v26" fill="#446386"/><path d="M27 103V69q0-19 19-19t19 19v34" fill="#6286a5"/><circle cx="46" cy="42" r="17" fill="#e6c7a8"/><path d="M29 39a17 17 0 0 1 33-2" fill="none" stroke="#80c7bb" stroke-width="5"/><circle cx="32" cy="32" r="3" fill="#fff"/><circle cx="46" cy="25" r="3" fill="#fff"/><circle cx="59" cy="31" r="3" fill="#fff"/><path d="m62 47 4 5" stroke="#bc9277" stroke-width="3" stroke-linecap="round"/></svg><small>观影场景示意 · 原视频未展示</small></div><div><p class="journey-kicker">一位观众，一段情绪旅程</p><p id="demo-record" class="journey-record">正在读取记录</p><span id="demo-badge" class="demo-badge">本地 CPU · 真实模型推理</span><div class="demo-actions journey-quickplay"><button id="demo-play-top" type="button" class="md-button md-button--primary" aria-pressed="false" disabled>播放这段旅程</button></div></div></div>
<p id="demo-empty" class="demo-empty">正在为这段真实记录计算逐秒预测…</p>
<section id="demo-experience" hidden aria-label="回放模型预测">
<div class="journey-grid">
<article class="demo-panel journey-snapshot"><p class="journey-kicker">这一秒，模型怎样预测？ <span id="demo-current-time" class="journey-timestamp">0 s</span></p><div class="journey-feeling"><svg id="demo-face" viewBox="0 0 120 120" role="img" aria-label="表情图形用于说明模型分值，不是观众的真实面部表情。"><circle class="face-disc" cx="60" cy="60" r="54"/><ellipse id="demo-eye-left" cx="42" cy="47" rx="3.2" ry="4"/><ellipse id="demo-eye-right" cx="78" cy="47" rx="3.2" ry="4"/><path id="demo-mouth" d="M38 75 Q60 75 82 75"/></svg><div><h2 id="demo-mood">等待预测</h2><p id="demo-mood-detail" class="demo-note"></p></div></div>
<div class="journey-gauge"><div class="journey-gauge-title"><strong>愉悦程度</strong><output id="demo-v-score">—</output></div><div id="demo-v-meter" class="journey-meter" role="meter" aria-label="愉悦程度" aria-valuemin="1" aria-valuemax="255" aria-valuenow="128"><span id="demo-v-dot" class="journey-meter-dot"></span></div><div class="journey-gauge-labels"><span>不愉悦</span><span>中性</span><span>愉悦</span></div></div>
<div class="journey-gauge"><div class="journey-gauge-title"><strong>活跃程度</strong><output id="demo-a-score">—</output></div><div id="demo-a-meter" class="journey-meter" role="meter" aria-label="活跃程度" aria-valuemin="1" aria-valuemax="255" aria-valuenow="128"><span id="demo-a-dot" class="journey-meter-dot"></span></div><div class="journey-gauge-labels"><span>平静</span><span>适中</span><span>活跃</span></div></div>
<p class="demo-note journey-caption">表情图形用于说明模型分值，不是观众的真实面部表情。</p></article>
<article class="demo-panel journey-map"><h2>情绪落在这里</h2><svg id="demo-map" viewBox="0 0 400 320" role="img" aria-label="愉悦程度与活跃程度构成的情绪坐标，显示真实预测轨迹"><title>愉悦程度与活跃程度构成的情绪坐标，显示真实预测轨迹</title><rect class="map-zone zone-negative" x="40" y="36" width="160" height="120" rx="10"/><rect class="map-zone zone-active" x="200" y="36" width="160" height="120" rx="10"/><rect class="map-zone zone-quiet" x="40" y="156" width="160" height="120" rx="10"/><rect class="map-zone zone-positive" x="200" y="156" width="160" height="120" rx="10"/><path class="map-axis" d="M40 156H360M200 36V276"/><text class="map-quadrant" x="120" y="66" text-anchor="middle">不愉悦 · 活跃</text><text class="map-quadrant" x="280" y="66" text-anchor="middle">愉悦 · 活跃</text><text class="map-quadrant" x="120" y="250" text-anchor="middle">不愉悦 · 平静</text><text class="map-quadrant" x="280" y="250" text-anchor="middle">愉悦 · 平静</text><text class="map-label" x="200" y="22" text-anchor="middle">活跃</text><text class="map-label" x="200" y="311" text-anchor="middle">平静</text><text class="map-label" x="40" y="295">不愉悦</text><text class="map-label" x="360" y="295" text-anchor="end">愉悦</text><polyline id="demo-map-path" class="map-trail" points=""/><polyline id="demo-map-played" class="map-played" points=""/><circle id="demo-map-start" class="map-start" cx="200" cy="156" r="4"/><circle id="demo-map-dot" class="map-current" cx="200" cy="156" r="7"/></svg><p class="demo-note">点表示当前一秒，浅色轨迹表示完整记录。</p></article>
</div>
<div class="demo-panel journey-transport"><div class="journey-transport-row"><div class="demo-actions"><button type="button" id="demo-play" class="md-button md-button--primary" aria-pressed="false">播放旅程</button><button type="button" id="demo-restart" class="md-button">回到开始</button></div><div class="journey-speed"><label for="demo-speed">回放速度</label><select id="demo-speed"><option value="1">1×</option><option value="2" selected>2×</option><option value="4">4×</option></select></div></div><label class="demo-range-label" for="demo-cursor"><span>拖动查看任意一秒</span><output id="demo-cursor-time">0 s / 29 s</output></label><input id="demo-cursor" type="range" min="0" max="29" value="0" step="1"><p class="demo-note">回放已经完成的离线预测，可调速度；不是实时采集。</p></div>
<div class="journey-moments" aria-label="回放模型预测"><button type="button" id="demo-jump-start" class="journey-moment"><span>开始时</span><strong id="demo-start-time">—</strong><span id="demo-start-note"></span><span class="journey-moment-arrow" aria-hidden="true">↗</span></button><button type="button" id="demo-jump-moment" class="journey-moment"><span>变化最明显的一秒</span><strong id="demo-moment-time">—</strong><span id="demo-moment-note"></span><span class="journey-moment-arrow" aria-hidden="true">↗</span></button><button type="button" id="demo-jump-end" class="journey-moment"><span>结束时</span><strong id="demo-end-time">—</strong><span id="demo-end-note"></span><span class="journey-moment-arrow" aria-hidden="true">↗</span></button></div><div class="journey-reading"><h2>这段记录怎么读？</h2><p id="demo-story"></p><p class="demo-note">两条刻度描述情绪的两个维度：愉悦程度从不愉悦到愉悦，活跃程度从平静到活跃。</p><p class="demo-note">文字分区和表情是连续预测的阅读辅助，不是情绪分类结论；这里回放的是记录中的观众。</p></div>
</section>
<details id="demo-options" class="demo-fold"><summary>使用自己的记录 · 调整模型参数</summary>
<form id="demo-form" class="demo-controls"><fieldset id="demo-settings"><legend>选择真实记录</legend><label for="demo-mode" class="sr-only">选择真实记录</label><select id="demo-mode"><option value="public" selected>公开观影记录 · 模型已配好</option><option value="local">使用自己的本地模型与数据</option></select><div id="demo-public-settings"><p class="demo-note">MER-PS 训练/验证集 · test_1 · 视频 1 · 第 0–29 秒。首次加载约 19 MB，含模型、特征和推理运行库。 <a href="#sample-source">样本来源与许可 →</a></p></div><div id="demo-local-settings" hidden><p class="demo-note">选择用仓库导出程序准备的模型和特征文件。文件只在浏览器中读取，不会上传。</p><label for="demo-model">模型文件</label><input type="file" id="demo-model" accept=".json,application/json"><label for="demo-input">特征文件</label><input type="file" id="demo-input" accept=".json,application/json"><p class="demo-note">同一试次的 1–300 个连续秒，单文件不超过 64 MB。 <a href="#prepare-local-files">如何准备文件 →</a></p></div><h2 class="demo-subheading">共同反应的权重</h2><label class="demo-range-label" for="demo-valence"><span>愉悦程度（效价）</span><output id="demo-valence-value">0.99</output></label><input id="demo-valence" type="range" min="0" max="1" step="0.01" value="0.99"><label class="demo-range-label" for="demo-arousal"><span>活跃程度（唤醒度）</span><output id="demo-arousal-value">0.92</output></label><input id="demo-arousal" type="range" min="0" max="1" step="0.01" value="0.92"><button type="button" id="demo-reset" class="demo-text-button">恢复论文固定权重</button><p class="demo-note">默认 0.99 / 0.92。更改后需重新计算；此时展示的是探索设置。</p></fieldset><button type="submit" class="md-button">重新计算</button></form></details>
<details id="demo-technical" class="demo-fold"><summary>深入查看：预测曲线与模型组成</summary><div class="demo-results"><h2 id="demo-results-title">共同反应、生理信息与最终预测</h2><p id="demo-result-note" class="demo-note"></p><div class="demo-metrics"><div><span>预测秒数</span><strong id="demo-sample-count">—</strong></div><div><span>计算耗时</span><strong id="demo-time">—</strong></div><div><span>相对共同反应的修正</span><strong id="demo-correction">—</strong></div></div><p class="demo-note">总耗时包含下载、文件解析和模型初始化。</p><div class="demo-legend"><span class="prior">共同反应（先验）</span><span class="physiology">生理分支</span><span class="fusion">最终预测（融合）</span></div><div id="demo-plots" hidden><div id="demo-valence-plot" class="demo-plot"></div><div id="demo-arousal-plot" class="demo-plot"></div><div id="demo-inspection" class="demo-inspection"></div></div><p class="demo-note">“接近中性 / 活跃程度适中”的显示区间为 128 ± 12，仅用于界面解读。</p><div class="demo-actions demo-downloads"><button id="demo-csv" type="button" class="md-button" disabled>下载 CSV</button><button id="demo-json" type="button" class="md-button" disabled>下载 JSON</button></div><details id="demo-table-details" class="demo-table-details" hidden><summary>查看逐秒数值</summary><p class="demo-note">展示前 20 行，下载包含全部预测。</p><div class="demo-table-scroll"><table id="demo-table"></table></div></details></div></details>
</div>

## 样本来源与许可 { #sample-source }

默认样本取自 [MER-PS 训练/验证数据](https://huggingface.co/datasets/MER-PS/MER-PS-trainval)，署名归 MER-PS 数据集创建者。它包含匿名编号 test_1 在视频 1 中第 0–29 秒的真实生理特征，经过基线校正和上下文特征提取。该片段来自模型开发数据，用于展示真实推理流程，不作为独立留出评估或准确率证明。

公开样本和推理模型采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)，供非商业科研使用。保留署名与许可链接，注明修改，并以相同许可共享衍生内容。<a href="../../assets/demo/NOTICE.txt">完整来源说明</a> · <a href="../../assets/demo/manifest.json">资源清单与校验值</a>

## 使用自己的本地文件 { #prepare-local-files }

在已有数据和检查点的本地仓库执行以下命令。文件输出到 artifacts/browser/，仅保留在本地。

```bash
.venv/bin/pip install -r requirements-demo.txt
.venv/bin/python scripts/export_browser_demo.py model
.venv/bin/python scripts/export_browser_demo.py input \
  --data-root data/MER_PS_trainval --subject test_1 \
  --video 1 --start 0 --count 60
```

`artifacts/browser/model.vtp-model.json` + `artifacts/browser/input.vtp-input.json`

特征准备沿用现有 Python 流程，包括基线校正及前一秒、当前秒、后一秒上下文。浏览器完成各检查点对应的标准化、六模型集成、先验查询、融合及向偶数取整。不能直接选择原始 MAT 文件或 PyTorch ZIP 模型包。

## 结果解释

这是面向熟悉视频新观众的离线预测。页面运行从训练检查点导出的真实六模型集成，输入为真实 EEG–fNIRS 记录提取的特征。导出程序记录使用的是 final_v3.pt 还是 best_v3.pt 回退检查点；回退结果不等同于报告的 27.72 MAE。

公开模式从本站下载演示模型、真实样本和推理运行库，再在浏览器内执行推理。本地模式只读取你选择的文件，文件和预测不会上传。关闭或刷新页面后释放计算会话。

<a href="../../licenses/onnxruntime.txt">ONNX Runtime 许可证</a> · <a href="../../licenses/onnxruntime-third-party.txt">Third-party notices</a> · [浏览器演示源码](https://github.com/rudykon/Vtp-Emotion/tree/main/website/javascripts/demo)
