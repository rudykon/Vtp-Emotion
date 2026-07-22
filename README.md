# 来源显式 EEG--fNIRS 连续情感回归

本项目服务于一项基于同步 EEG 与 fNIRS 记录的连续效价—唤醒度回归研究。核心科学问题是：在所有被试观看相同且时间对齐的视频时，被试留出的预测准确性究竟反映了个体生理证据，还是主要来自跨被试共享的视频—时间情感轨迹。

## 主要发现

五折被试留出分析在完全相同的样本上分离了三种信息来源：

| 信息来源 | 总体 MAE |
| --- | ---: |
| 生理分支 | 47.3509 |
| 折内视频—时间先验 | 29.0633 |
| 固定融合 | 29.0146 |

从生理分支到固定融合的总误差降幅中，约 99.7% 已由视频—时间先验实现。这一结果揭示了重复刺激条件下的来源混淆，但不能据此认为 EEG 或 fNIRS 普遍缺乏情感信息。

在 4 名独立留出被试上完成的外部盲测进一步拆分了视频身份和视频内时间动态：

| 消融变体 | 总体 MAE |
| --- | ---: |
| 全局常数 | 44.3296 |
| 视频身份先验 | 33.3627 |
| 视频—时间先验 | 28.0410 |
| 生理分支 | 42.7486 |
| 固定融合 | **27.7246** |

视频身份带来第一层主要改善，加入时间坐标后总体 MAE 又降低 5.3217；固定融合在视频—时间先验基础上继续降低 0.3165，并在效价、唤醒度和 MSE 上保持一致方向。完整协议与结果见 [`docs/ablation.md`](docs/ablation.md)。

## 项目结构

- `paper/`：英文论文、中文对照稿、参考文献和来源分解图。
- `src/merps/`：特征提取、标签先验、生理模型、可选校准工具和推理代码。
- `scripts/`：模型训练、被试留出评估、数据下载、模型包导出和本地验证脚本。
- `tests/`：模型包配置与校准工具的单元测试。
- `docs/`：中文研究方法、数据说明与消融实验记录。
- `data/`：本地训练/验证数据和生成的特征缓存。
- `checkpoints/`：生理模型检查点和全数据标签先验。
- `artifacts/`：生成的模型包及其配置清单。

## 环境配置

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
```

## 复现来源分解分析

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate.py --blend-checkpoints
```

该分析采用折内构建的中位数视频—时间先验，时间平滑半径为 3，固定先验权重为 `[0.99, 0.92]`，不使用静息输出校准。

## 导出并验证模型包

```bash
.venv/bin/python scripts/export_model_bundle.py
.venv/bin/python scripts/validate_model_bundle.py \
  artifacts/model_bundle_source_explicit.zip \
  --subject test_1 --video 1 --count 8
```

模型包提供本地 `predict(input_dir, output_dir)` 推理函数，并生成 `predictions.csv`。该模型包用于完整数据训练后的推理复现；论文中的科学结论来自五折被试留出分析，而不是该全数据模型包。

## 构建论文

```bash
cd paper
../.venv/bin/python figures/make_figures.py
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error main_zh.tex
```

生成结果包括英文论文 `paper/main.pdf`、中文论文 `paper/main_zh.pdf`，以及 PDF/SVG 格式的来源分解图。

## 数据与共享边界

本地数据集、特征缓存、模型检查点、生成的模型包和账户凭据均不纳入版本控制。共享项目前，应核对数据集许可证，并单独确认模型检查点是否允许重新分发。论文源文件、源代码、小型汇总表和复现说明可作为项目的主要共享内容。
