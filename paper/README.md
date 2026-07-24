# 连续情感回归论文源文件说明

本目录包含英文论文、中文对照稿、参考文献、论文图件及可追溯图件源数据。

## 科学范围

本文研究基于 EEG 与 fNIRS 的连续效价—唤醒度回归，首要目标是降低新观众观看熟悉且时间对齐的视频时的平均绝对误差（MAE）。低误差群体情绪曲线可用于预测熟悉视频的大致反应，为视频剪辑、广告投放或内容推荐提供群体基线，并为新观众预测提供粗略初始化。论文聚焦这一预测前提，并在“讨论与局限”中统一说明尚未验证的下游用途。

论文主要讨论：

- 仅使用训练参与者、在每个交叉验证折内构建低成本视频—时间先验；
- 使用图结构与跨模态特征建立 EEG--fNIRS 分支；
- 通过固定融合获得当前评估中的最低 MAE；
- 在 4 名外部独立参与者上验证最低 MAE；
- 通过全局常数、视频身份、视频内时间、EEG--fNIRS 和固定融合进行来源分解；
- 使用成对残差分析参与者、视频和归一化视频时间上的异质性；
- 把结论限定于熟悉视频上的新观众预测，不外推到未见刺激。

五折分析中，固定融合取得最低总体 MAE 29.01，视频—时间先验和 EEG--fNIRS 分支分别为 29.06 和 47.35。外部评估中，固定融合再次取得最低 MAE 27.72，视频—时间先验为 28.04。两组评估都表明，先验已经解释大部分降误差作用，生理信号提供较小的残差修正。

在确认最低 MAE 后，论文再分析性能来源。融合的总体增量较小且具有异质性，只在 4 名参与者中的 3 名和 15 个视频中的 9 个上改善。该分析说明视频—时间先验是强而低成本的群体基线，生理信号提供较小、总体有利但不均匀的修正；它不是论文最终目的本身。

## 图件论证结构

`method_overview` 是正文 Figure 1，以三个面板概括熟悉视频情感回归场景、折内视频—时间先验与 EEG--fNIRS 分支，以及偏重先验的固定融合。该图明确区分训练标签衍生的共享轨迹和新观众提供的生理信号，并强调留出标签不参与先验构建。

`external_data_landscape` 暂不插入正文，但图件、源数据和生成流程继续保留，可用于数据诊断或后续补充材料。该图展示外部效价—唤醒度标签覆盖，以及各视频在归一化时间区间中的样本加权平均效价和唤醒度；其中的重复观测不参与预测器构建，也不承担因果、统计显著性或未见视频泛化结论。

`source_dominance` 是正文 Figure 2（2×1 单栏内部 MAE 对比图）：沿用全文统一配色，以及 Figure 4 的横向柱图和增量棒棒糖图结构，展示固定融合取得最低 MAE，并说明视频—时间先验几乎解释了从 EEG--fNIRS 分支到融合的全部误差降幅。

`external_prediction_quality` 是正文 Figure 3（双栏外部预测质量图），以并列六边形密度图展示固定融合在效价和唤醒度上的预测值—真实值关系、理想预测对角线与对应 MAE。该图用于诊断预测范围、密度分布和向总体均值收缩等校准现象，不把秒级观测视为独立重复，也不据此开展显著性检验。

`external_source_decomposition` 是正文 Figure 4（双栏外部 MAE 与残差分析主图），采用全文统一配色，其四个面板依次展示：

1. 五种来源变体的总体 MAE；
2. 4 名参与者上按幅度排序的配对融合增量；
3. 15 个视频上按幅度排序的融合增益与损失；
4. 十个归一化视频时间区间上的误差曲线。

`external_video_time_mae` 是正文 Figure 5（双栏视频×归一化时间 MAE 热力图），并列展示视频—时间先验与固定融合在 15 个视频、十个归一化时间区间上的单元 MAE。两个面板共用固定的 0--65 色标，下端深蓝表示较低误差，上端橙红表示较高误差。Figure 4d 给出跨视频汇总后的一维时间趋势，Figure 5 则恢复视频与时间的二维结构，用于定位共享误差热点及融合改善或退化发生的位置；该图同样只作描述性诊断。

四张正文数据与结果图件（Figures 2–5）均由 Python/matplotlib 生成，其 SVG 和 PDF 保留可编辑文字；本地还导出 PNG 预览与 600 dpi、LZW 压缩 TIFF。方法概览图（Figure 1）使用带嵌入字体与矢量文字的 PDF 文件。秒级样本仅用于描述性汇总，不进行伪重复显著性检验。

## 论文行文结构

中英文稿采用一致的七段论证结构：Introduction/引言、Related Work/相关工作、Method/方法、Experimental Setup/实验设置、Results and Analysis/结果与分析、Discussion and Limitations/讨论与局限，以及 Conclusion/结论。引言提出三个研究问题，结果部分逐一回答：视频—时间先验与融合能达到怎样的 MAE、主要降幅来自哪些信息源，以及剩余增益如何随参与者、视频和视频内时间变化。

## 生成图件

```bash
../.venv/bin/python figures/make_figures.py
../.venv/bin/python figures/make_external_figures.py
```

外部图件脚本读取 `../artifacts/external_evaluation/` 中的本地评估产物，以及本目录中的汇总 `source_data_external_*.csv`。Figures 3 和 5 所需的逐样本真实值与预测值来自本地 `paired_predictions.csv`，脚本可据此刷新被 `.gitignore` 排除的本地缓存；受限队列的逐样本标签不纳入版本控制。重新克隆仓库后，如需重画这两幅图，必须先按数据许可恢复本地评估产物。

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
- `figures/make_external_figures.py`：外部数据景观、预测质量、来源分解与视频×时间 MAE 图生成脚本。
- `figures/source_data_components.csv`：五折来源汇总指标。
- `figures/source_data_external_overall.csv`：外部五种来源的总体指标。
- `figures/source_data_external_subject.csv`：参与者分层指标。
- `figures/source_data_external_video.csv`：视频分层指标。
- `figures/source_data_external_time.csv`：归一化时间分层指标。
- `figures/source_data_external_trials.csv`：本地试验级标签摘要；受数据访问边界约束，不纳入版本控制。
- `figures/source_data_external_samples.csv`：本地数据景观图逐样本标签与元数据；不纳入版本控制。
- `figures/source_data_external_predictions.csv`：Figures 3 和 5 的本地逐样本真实值、预测值及视频—时间元数据；由 `artifacts/external_evaluation/paired_predictions.csv` 生成，不纳入版本控制。
- `figures/method_overview.pdf`：Figure 1，熟悉视频情感回归方法概览图。
- `figures/external_data_landscape.{pdf,svg}`：暂不插入正文，保留为外部标签覆盖与视频—时间数据景观图。
- `figures/source_dominance.{pdf,svg}`：Figure 2，五折来源分解图。
- `figures/external_prediction_quality.{pdf,svg}`：Figure 3，固定融合的外部预测值—真实值密度图。
- `figures/external_source_decomposition.{pdf,svg}`：Figure 4，外部来源分解主图。
- `figures/external_video_time_mae.{pdf,svg}`：Figure 5，视频×归一化时间 MAE 热力图。

准备匿名审稿材料时，只包含 TeX、参考文献和正文实际引用的图件；编译日志、本地路径、原始数据、缓存和账户信息均应排除。
