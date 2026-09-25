---
hide:
  - navigation
  - toc
---

# 浏览器演示

<p class="demo-eyebrow">使用你电脑的算力运行</p>
<p class="demo-lead">直接体验合成数据下的固定融合，或选择本地模型与特征文件进行 EEG–fNIRS 推理。计算在浏览器内执行，所选文件不会上传。</p>

<div id="vtp-demo" class="vtp-demo" data-language="zh">
<div class="demo-layout">
<form id="demo-form" class="demo-panel demo-controls">
<fieldset id="demo-settings">
<legend>输入来源</legend>
<label for="demo-mode" class="sr-only">输入来源</label>
<select id="demo-mode"><option value="synthetic">合成数据演示</option><option value="local">本地模型推理</option></select>
<div id="demo-example-settings">
<p class="demo-note">仅用于理解方法：轨迹与生理分支输出在本机生成。此示例不运行训练后的神经网络，也不复现论文结果。</p>
<label for="demo-scenario">示例轨迹</label>
<select id="demo-scenario"><option value="wave">平缓变化</option><option value="shift">渐进转变</option><option value="pulse">短暂情感事件</option></select>
<div class="demo-control-pair"><div><label for="demo-count">时长</label><select id="demo-count"><option value="60">60 s</option><option value="120" selected>120 s</option><option value="240">240 s</option></select></div><div><label for="demo-seed">场景种子</label><input id="demo-seed" type="number" min="0" max="4294967295" step="1" value="2026" required></div></div>
</div>
<div id="demo-local-settings" hidden>
<p class="demo-note">选择用仓库导出程序准备的文件。模型通过 WebAssembly 在本机 CPU 上运行，无需账号或推理服务器。</p>
<label for="demo-model">模型文件</label><input type="file" id="demo-model" accept=".json,application/json">
<label for="demo-input">特征文件</label><input type="file" id="demo-input" accept=".json,application/json">
<p class="demo-note">选择两个本地 JSON 文件，单文件不超过 64 MB；输入为同一试次的 1–300 个连续秒。 <a href="#prepare-local-files">如何准备本地文件 →</a></p>
</div>
<h2 class="demo-subheading">先验权重</h2>
<label class="demo-range-label" for="demo-valence"><span>效价</span><output id="demo-valence-value">0.99</output></label>
<input id="demo-valence" type="range" min="0" max="1" step="0.01" value="0.99">
<label class="demo-range-label" for="demo-arousal"><span>唤醒度</span><output id="demo-arousal-value">0.92</output></label>
<input id="demo-arousal" type="range" min="0" max="1" step="0.01" value="0.92">
<button type="button" id="demo-reset" class="demo-text-button">恢复固定权重</button>
<p class="demo-note">默认值为 0.99 / 0.92。修改后的权重仅用于探索。</p>
</fieldset>
<div class="demo-actions"><button id="demo-run" type="submit" class="md-button md-button--primary">在本机运行</button><button id="demo-stop" type="button" class="md-button" disabled>停止</button></div>
<p id="demo-status" role="status" aria-live="polite">已就绪。选择输入来源后运行。</p>
<progress id="demo-progress" max="100" value="0" hidden aria-label="Progress"></progress>
</form>
<section class="demo-panel demo-results" aria-labelledby="demo-results-title">
<div class="demo-results-header"><h2 id="demo-results-title">预测轨迹</h2><span id="demo-badge" class="demo-badge">合成数据演示</span></div>
<p id="demo-result-note" class="demo-note">效价与唤醒度使用 [1, 255] 标度。虚线表示先验，青绿色实线表示融合结果。</p>
<div class="demo-metrics"><div><span>样本数</span><strong id="demo-sample-count">—</strong></div><div><span>浏览器耗时</span><strong id="demo-time">—</strong></div><div><span>平均绝对修正量</span><strong id="demo-correction">—</strong></div></div>
<p class="demo-note">总耗时包含文件解析和模型初始化。</p>
<div class="demo-legend"><span class="prior">视频—时间先验</span><span class="physiology">生理分支</span><span class="fusion">固定融合</span></div>
<p id="demo-empty" class="demo-empty">运行示例或选择本地文件，即可查看预测。</p>
<div id="demo-plots" hidden>
<div id="demo-valence-plot" class="demo-plot"></div><div id="demo-arousal-plot" class="demo-plot"></div>
<label class="demo-range-label" for="demo-cursor"><span>查看某一秒</span><output id="demo-cursor-time">0 s</output></label>
<input id="demo-cursor" type="range" min="0" max="119" value="0" step="1">
<div id="demo-inspection" class="demo-inspection" aria-live="polite"></div>
</div>
<div class="demo-actions demo-downloads"><button id="demo-csv" type="button" class="md-button" disabled>下载 CSV</button><button id="demo-json" type="button" class="md-button" disabled>下载 JSON</button></div>
</section>
</div>
<details id="demo-table-details" class="demo-table-details" hidden><summary>查看逐秒预测</summary><p class="demo-note">最多展示前 20 行；下载结果包含全部样本、浮点分量与取整预测。</p><div class="demo-table-scroll"><table id="demo-table"></table></div></details>
</div>

## 准备本地文件 { #prepare-local-files }

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

这是面向熟悉视频新观众的离线预测。使用训练后的模型需要本地模型文件。公开示例使用合成数据，不用于准确率评估。导出程序记录使用的是 final_v3.pt 还是 best_v3.pt 回退检查点；回退结果不等同于报告的 27.72 MAE。

文件只在当前标签页读取和处理，关闭或刷新页面后释放会话。网站仅下载推理运行库，不提供模型参数下载。

<a href="../../licenses/onnxruntime.txt">ONNX Runtime 许可证</a> · <a href="../../licenses/onnxruntime-third-party.txt">Third-party notices</a> · [浏览器演示源码](https://github.com/rudykon/Vtp-Emotion/tree/main/website/javascripts/demo)
