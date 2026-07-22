# 匿名 ACM 双栏论文

本目录包含作为正式版本的英文论文，以及便于阅读和核对的中文对照稿。

## 科学范围

本文研究重复刺激协议下基于 EEG 与 fNIRS 的连续效价—唤醒度回归。核心问题是：被试留出预测反映的究竟是个体生理证据，还是观看者之间共享的刺激锁定情感轨迹。

论文主要讨论：

- 仅使用训练被试、在每个交叉验证折内构建的视频—时间先验；
- 使用图结构与跨模态特征的 EEG--fNIRS 生理比较分支；
- 在完全相同的留出样本上，对生理信息、刺激结构和固定融合进行来源显式比较；
- 区分熟悉视频上的新观看者预测与向未见刺激迁移。

生理分支的总体 MAE 为 47.3509，视频—时间先验为 29.0633，固定融合为 29.0146。论文仅对较小的融合增量作描述性解释，不据此主张模型能够泛化到未见刺激。

## 生成图件

```bash
../.venv/bin/python figures/make_figures.py
```

脚本读取 `figures/source_data_components.csv`，重新生成单栏矢量图 `figures/source_dominance.pdf` 和 `figures/source_dominance.svg`。

## 编译论文

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error main_zh.tex
```

使用以下命令检查输出 PDF 的页面信息：

```bash
pdfinfo main.pdf
pdfinfo main_zh.pdf
```

## 源文件结构

- `main.tex` 与 `body.tex`：英文论文。
- `main_zh.tex` 与 `body_zh.tex`：中文对照稿。
- `references.bib`：参考文献和数据集记录。
- `figures/source_data_components.csv`：信息来源的汇总指标。
- `figures/source_dominance.pdf` 与 `.svg`：论文图件。
- `figures/make_figures.py`：仅使用 Python 的图件生成脚本。

准备双盲审稿材料时，仅应包含 TeX 源文件、`references.bib` 和正文实际引用的图件；应排除编译日志、本地路径、工作用源数据、缓存和账户信息。
