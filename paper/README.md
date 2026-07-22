# 连续情感回归论文源文件说明

本目录包含英文论文、中文对照稿、参考文献、论文图件及可追溯图件源数据。

## 科学范围

本文研究基于 EEG 与 fNIRS 的连续效价—唤醒度回归，首要目标是降低新观众观看熟悉、时间对齐影片时的平均绝对误差（MAE）。低误差群体情绪曲线可望用于预测已知影片的大致反应，为视频剪辑、广告投放或内容推荐提供群体基线，并为新观众预测提供粗略初始化；论文不把这些潜在用途写成已经完成的下游验证。

论文主要讨论：

- 仅使用训练被试、在每个交叉验证折内构建低成本视频—时间先验；
- 使用图结构与跨模态特征建立 EEG--fNIRS 生理分支；
- 通过固定融合获得当前评估中的最低 MAE；
- 在 4 名外部独立观看者上验证最低 MAE；
- 在主结果之后，比较全局常数、视频身份、视频—时间动态、生理和固定融合；
- 使用逐样本成对残差分析被试、视频和归一化视频时间上的异质性；
- 把结论限定于熟悉视频上的新观看者预测，不外推到未见刺激。

五折分析中，固定融合取得最低总体 MAE 29.0146，视频—时间先验和生理分支分别为 29.0633 和 47.3509。外部评估中，固定融合再次取得最低 MAE 27.7246；视频—时间先验、视频身份先验、生理分支和全局常数分别为 28.0410、33.3627、42.7486 和 44.3296。

在确认最低 MAE 后，论文再分析性能来源。融合的总体增量较小且具有异质性，只在 4 名被试中的 3 名和 15 个视频中的 9 个上改善。该分析说明视频—时间先验是强而低成本的群体基线，生理信号提供较小、总体有利但不均匀的修正；它不是论文最终目的本身。

## 图件论证结构

`source_dominance` 是单栏 MAE 对比与事后来源分析图：先展示固定融合取得最低 MAE，再说明视频—时间先验几乎解释了从生理分支到融合的全部误差降幅。

`external_source_decomposition` 是双栏外部 MAE 与事后分析主图，其四个面板依次展示：

1. 五种来源变体的总体 MAE；
2. 4 名被试上视频—时间先验与固定融合的配对变化；
3. 15 个视频上的融合增益与损失；
4. 十个归一化视频时间区间上的误差曲线。

`external_data_landscape` 是数据景观图，展示效价—唤醒度标签密度，以及视频×归一化时间上的平均效价和唤醒度。该图用于数据审计与补充展示，不承担主因果或显著性结论。

全部图件均由 Python/matplotlib 生成。SVG 和 PDF 保留可编辑文字；本地还导出 PNG 预览与 600 dpi、LZW 压缩 TIFF。秒级样本仅用于描述性汇总，不进行伪重复显著性检验。

## 生成图件

```bash
../.venv/bin/python figures/make_figures.py
../.venv/bin/python figures/make_external_figures.py
```

外部图件脚本默认读取 `../artifacts/external_evaluation/` 中的评估产物，以及本目录中的 `source_data_external_*.csv`。

## 编译论文

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error main_zh.tex
```

检查输出 PDF：

```bash
pdfinfo main.pdf
pdfinfo main_zh.pdf
```

## 源文件结构

- `main.tex` 与 `body.tex`：英文论文。
- `main_zh.tex` 与 `body_zh.tex`：中文对照稿。
- `references.bib`：参考文献和数据集记录。
- `figures/make_figures.py`：五折来源图生成脚本。
- `figures/make_external_figures.py`：外部来源分解与数据景观图生成脚本。
- `figures/source_data_components.csv`：五折来源汇总指标。
- `figures/source_data_external_overall.csv`：外部五种来源的总体指标。
- `figures/source_data_external_subject.csv`：被试分层指标。
- `figures/source_data_external_video.csv`：视频分层指标。
- `figures/source_data_external_time.csv`：归一化时间分层指标。
- `figures/source_data_external_trials.csv`：试验级标签摘要。
- `figures/source_data_external_samples.csv`：数据景观图所需的逐样本标签与元数据。
- `figures/source_dominance.{pdf,svg}`：五折来源分解图。
- `figures/external_source_decomposition.{pdf,svg}`：外部来源分解主图。
- `figures/external_data_landscape.{pdf,svg}`：外部标签覆盖与视频—时间数据景观图。

准备匿名审稿材料时，只包含 TeX、参考文献和正文实际引用的图件；编译日志、本地路径、原始数据、缓存和账户信息均应排除。
