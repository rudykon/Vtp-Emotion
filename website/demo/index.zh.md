---
hide:
  - navigation
  - toc
---

# 浏览器演示

<p class="demo-eyebrow">使用你电脑的算力运行</p>
<p class="demo-lead">页面自动加载真实 EEG–fNIRS 样本和训练好的六模型集成，在你电脑的 CPU 上预测逐秒效价与唤醒度。也可选择自己的本地文件进行推理。</p>

<div id="vtp-demo" class="vtp-demo" data-language="zh">
<div class="demo-layout">
<form id="demo-form" class="demo-panel demo-controls">
<fieldset id="demo-settings">
<legend>真实模型与数据</legend>
<label for="demo-mode" class="sr-only">数据来源</label>
<select id="demo-mode"><option value="public" selected>公开真实样本 · 自动加载模型</option><option value="local">使用自己的本地模型与数据</option></select>
<div id="demo-public-settings">
<p class="demo-note">MER-PS 训练/验证集 · test_1 · 视频 1 · 第 0–29 秒。模型包含 final_v3.pt 与五个交叉验证模型；所有预测均由浏览器现场计算。</p>
<p class="demo-note">首次加载约 19 MB（含推理运行库）。<a href="#sample-source">样本来源与许可 →</a></p>
</div>
<div id="demo-local-settings" hidden>
<p class="demo-note">选择用仓库导出程序准备的文件。模型通过 WebAssembly 在本机 CPU 上运行，无需账号或推理服务器。</p>
<label for="demo-model">模型文件</label><input type="file" id="demo-model" accept=".json,application/json">
<label for="demo-input">真实数据特征文件</label><input type="file" id="demo-input" accept=".json,application/json">
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
<div class="demo-actions"><button id="demo-run" type="submit" class="md-button md-button--primary">运行真实模型</button><button id="demo-stop" type="button" class="md-button" disabled>停止</button></div>
<p id="demo-status" role="status" aria-live="polite">正在准备公开真实样本与训练好的模型。</p>
<progress id="demo-progress" max="100" value="0" hidden aria-label="Progress"></progress>
</form>
<section class="demo-panel demo-results" aria-labelledby="demo-results-title">
<div class="demo-results-header"><h2 id="demo-results-title">预测轨迹</h2><span id="demo-badge" class="demo-badge">本地 CPU · 真实模型推理</span></div>
<p id="demo-result-note" class="demo-note">效价与唤醒度使用 [1, 255] 标度。虚线表示先验，青绿色实线表示融合结果。</p>
<div class="demo-metrics"><div><span>样本数</span><strong id="demo-sample-count">—</strong></div><div><span>浏览器耗时</span><strong id="demo-time">—</strong></div><div><span>平均绝对修正量</span><strong id="demo-correction">—</strong></div></div>
<p class="demo-note">总耗时包含资源下载、文件解析和模型初始化。</p>
<div class="demo-legend"><span class="prior">视频—时间先验</span><span class="physiology">生理分支</span><span class="fusion">固定融合</span></div>
<p id="demo-empty" class="demo-empty">正在加载真实模型与样本，预测将在本机计算完成后显示。</p>
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
