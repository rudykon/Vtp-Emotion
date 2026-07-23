# 连续情感回归论文源文件说明

本目录包含英文论文、中文对照稿、参考文献、论文图件及可追溯图件源数据。

## 科学范围

本文研究基于 EEG 与 fNIRS 的连续效价—唤醒度回归，首要目标是降低新观众观看熟悉、时间对齐影片时的平均绝对误差（MAE）。低误差群体情绪曲线可用于预测已知视频的大致反应，为视频剪辑、广告投放或内容推荐提供群体基线，并为新观众预测提供粗略初始化。论文聚焦这一预测前提，并在“讨论与局限”中统一说明尚未验证的下游用途。

论文主要讨论：

- 仅使用训练参与者、在每个交叉验证折内构建低成本视频—时间先验；
- 使用图结构与跨模态特征建立 EEG--fNIRS 分支；
- 通过固定融合获得当前评估中的最低 MAE；
- 在 4 名外部独立参与者上验证最低 MAE；
- 通过全局常数、视频身份、视频—时间动态、EEG--fNIRS 和固定融合进行来源分解；
- 使用成对残差分析参与者、视频和归一化视频时间上的异质性；
- 把结论限定于熟悉视频上的新观众预测，不外推到未见刺激。

五折分析中，固定融合取得最低总体 MAE 29.01，视频—时间先验和 EEG--fNIRS 分支分别为 29.06 和 47.35。外部评估中，固定融合再次取得最低 MAE 27.72，视频—时间先验为 28.04。两组评估都表明，先验已经解释大部分降误差作用，生理信号提供较小的残差修正。

在确认最低 MAE 后，论文再分析性能来源。融合的总体增量较小且具有异质性，只在 4 名参与者中的 3 名和 15 个视频中的 9 个上改善。该分析说明视频—时间先验是强而低成本的群体基线，生理信号提供较小、总体有利但不均匀的修正；它不是论文最终目的本身。

## 图件论证结构

`external_data_landscape` 是正文 Figure 1，展示外部效价—唤醒度标签覆盖，以及各视频在归一化时间区间中的样本加权平均效价和唤醒度。该图用于交代外部评估域及其描述性差异；其中的重复观测不参与预测器构建，也不承担因果、统计显著性或未见视频泛化结论。

`source_dominance` 是正文 Figure 2（单栏内部 MAE 对比图）：展示固定融合取得最低 MAE，并说明视频—时间先验几乎解释了从 EEG--fNIRS 分支到融合的全部误差降幅。

`external_source_decomposition` 是正文 Figure 3（双栏外部 MAE 与残差分析主图），其四个面板依次展示：

1. 五种来源变体的总体 MAE；
2. 4 名参与者上按幅度排序的配对融合增量；
3. 15 个视频上按幅度排序的融合增益与损失；
4. 十个归一化视频时间区间上的误差曲线。

全部图件均由 Python/matplotlib 生成。SVG 和 PDF 保留可编辑文字；本地还导出 PNG 预览与 600 dpi、LZW 压缩 TIFF。秒级样本仅用于描述性汇总，不进行伪重复显著性检验。

## 论文行文结构

中英文稿采用一致的七段论证结构：Introduction/引言、Related Work/相关工作、Method/方法、Experimental Setup/实验设置、Results and Analysis/结果与分析、Discussion and Limitations/讨论与局限，以及 Conclusion/结论。引言提出三个研究问题，结果部分逐一回答：视频—时间先验与融合能达到怎样的 MAE、主要降幅来自哪些信息源，以及剩余增益如何随参与者、视频和视频内时间变化。

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
- `figures/source_data_external_subject.csv`：参与者分层指标。
- `figures/source_data_external_video.csv`：视频分层指标。
- `figures/source_data_external_time.csv`：归一化时间分层指标。
- `figures/source_data_external_trials.csv`：试验级标签摘要。
- `figures/source_data_external_samples.csv`：数据景观图所需的逐样本标签与元数据。
- `figures/source_dominance.{pdf,svg}`：五折来源分解图。
- `figures/external_source_decomposition.{pdf,svg}`：外部来源分解主图。
- `figures/external_data_landscape.{pdf,svg}`：外部标签覆盖与视频—时间数据景观图。

准备匿名审稿材料时，只包含 TeX、参考文献和正文实际引用的图件；编译日志、本地路径、原始数据、缓存和账户信息均应排除。
