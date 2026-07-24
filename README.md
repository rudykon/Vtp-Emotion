# 面向熟悉视频新观众的低 MAE EEG--fNIRS 连续情感回归

本项目研究同步 EEG 与 fNIRS 条件下的连续效价—唤醒度回归，最终目的明确：降低新观众观看熟悉且时间对齐的视频时的平均绝对误差（MAE）。在这一场景中，训练参与者形成的群体情绪曲线具有直接用途：

- 预测观众观看某部熟悉视频时的大致情绪曲线；
- 为视频剪辑、广告投放或内容推荐提供群体反应基线；
- 为新观众的情绪预测提供粗略初始化。

这些用途目前是应用动机，项目尚未验证具体剪辑、广告或推荐效果。视频身份和播放时间在推理时易于获得，因此折内视频—时间先验本身就是一种简单、低成本且有效的降 MAE 方法。项目使用固定融合把该先验与 EEG--fNIRS 分支结合，以取得最低总体 MAE。整体方法见图 1。

<p align="center">
  <a href="docs/figures/method_overview.png">
    <img src="docs/figures/method_overview.png" alt="视频—时间先验与 EEG--fNIRS 固定融合的方法概览" width="100%">
  </a>
</p>
<p align="center"><em>图 1｜面向熟悉视频新观众的低 MAE 连续情感回归框架。</em></p>

## MAE 主结果

五折参与者留出评估覆盖 24 名参与者、15 个熟悉视频和 36,864 个秒级样本：

| 预测策略 | 总体 MAE |
| --- | ---: |
| EEG--fNIRS 分支 | 47.35 |
| 折内视频—时间先验 | 29.06 |
| **固定融合** | **29.01** |

固定融合取得最低 MAE；低成本视频—时间先验单独使用时仅高 0.05，并相对 EEG--fNIRS 分支降低 18.29。内部来源分解见图 2。

<p align="center">
  <a href="docs/figures/source_dominance.png">
    <img src="docs/figures/source_dominance.png" alt="内部参与者留出评估的 MAE 与来源分解" width="55%">
  </a>
</p>
<p align="center"><em>图 2｜内部参与者留出 MAE：视频—时间先验解释了主要误差降幅，固定融合取得最低值。</em></p>

外部参与者独立评估包含 4 名新观众、60 次试验和 6,143 个秒级样本：

| 预测策略 | 总体 MAE |
| --- | ---: |
| 全局常数 | 44.33 |
| 视频身份先验 | 33.36 |
| 视频—时间先验 | 28.04 |
| EEG--fNIRS 分支 | 42.75 |
| **固定融合** | **27.72** |

固定融合再次取得最低 MAE，并在视频—时间先验基础上继续降低 0.32。由此，项目的主要结论是：对于熟悉视频的新观众，视频—时间先验提供强而低成本的群体预测基线，生理信号在此基础上提供较小的最终修正。外部预测质量见图 3。

<p align="center">
  <a href="docs/figures/external_prediction_quality.png">
    <img src="docs/figures/external_prediction_quality.png" alt="外部固定融合预测值与真实值的六边形密度图" width="100%">
  </a>
</p>
<p align="center"><em>图 3｜外部固定融合的预测值—真实值关系；两维预测均存在向量表中部收缩的现象。</em></p>

## 取得低 MAE 后的分析

仅看生理信号、仅看视频身份、仅看视频与时间，以及固定融合之间的对比，被定位为主结果之后的解释性分析。该分析表明：

- 从 EEG--fNIRS 分支到固定融合的内部总降幅中，约 99.7% 已由折内视频—时间先验实现；
- 外部评估中，视频身份先将总体 MAE 降低 10.97，加入时间坐标后又降低 5.32；
- 融合增量并不均匀，只在 4 名参与者中的 3 名和 15 个视频中的 9 个上改善；
- 时间先验的优势具有阶段性，第一个归一化时间区间中视频身份与视频—时间先验的 MAE 分别为 45.53 和 13.40，而最后五个区间中视频身份先验略优。

这些对比用于解释最低 MAE 的来源与适用边界，不取代降低 MAE 这一首要目标。当前结论仅适用于新观众观看熟悉视频，不证明向未见视频迁移。外部来源分解与视频×时间误差结构分别见图 4 和图 5；详细方法与结果见 [`docs/method.md`](docs/method.md) 和 [`docs/ablation.md`](docs/ablation.md)。

<p align="center">
  <a href="docs/figures/external_source_decomposition.png">
    <img src="docs/figures/external_source_decomposition.png" alt="外部 MAE 来源分解与参与者、视频、时间异质性" width="100%">
  </a>
</p>
<p align="center"><em>图 4｜外部 MAE 来源分解：总体改善同时包含参与者、视频和时间层面的局部增益与损失。</em></p>

<p align="center">
  <a href="docs/figures/external_video_time_mae.png">
    <img src="docs/figures/external_video_time_mae.png" alt="视频—时间先验与固定融合的视频与归一化时间 MAE 热力图" width="100%">
  </a>
</p>
<p align="center"><em>图 5｜外部视频×归一化时间 MAE：固定融合的小幅总体增益并非在所有网格单元中一致出现。</em></p>

## 项目结构

- `src/merps/`：特征提取、视频—时间先验、生理模型、校准工具和推理代码。
- `scripts/`：训练、参与者留出评估、外部评估、数据下载、模型包导出和本地验证脚本。
- `tests/`：来源构建、指标、校准和模型包配置的单元测试。
- `docs/`：中文方法、数据与取得低 MAE 后的消融分析说明。
- `data/`：本地研究数据、外部评估数据和特征缓存；均不纳入版本控制。
- `checkpoints/`：本地生理模型检查点与视频—时间先验；不纳入版本控制。
- `artifacts/`：训练日志、评估结果、模型包和完整流程审计；不纳入版本控制。

## 环境配置

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
```

项目使用 Python 完成训练、评估、模型包导出与推理。若下载环境经过 SOCKS 代理，`requirements.txt` 中的 `socksio` 用于补齐网络依赖。

## 数据准备

训练/验证数据默认位于：

```text
data/MER_PS_trainval/
```

外部参与者独立评估数据默认位于：

```text
data/download/MER_PS_public_evaluation/
```

设置数据提供方给出的仓库标识后，可使用本地 `huggingface_token.json` 下载外部数据：

```bash
MERPS_EXTERNAL_REPO_ID='<外部数据仓库标识>' \
  bash scripts/download_external_data.sh
```

令牌文件已由 `.gitignore` 排除。脚本只读取令牌，不会把令牌写入下载目录、日志或版本控制。完整数据结构与校验结果见 [`data/DATASET.md`](data/DATASET.md) 和 [`docs/dataset.md`](docs/dataset.md)。外部标签覆盖与视频—时间分布见下方补充数据诊断图。

<p align="center">
  <a href="docs/figures/external_data_landscape.png">
    <img src="docs/figures/external_data_landscape.png" alt="外部标签覆盖与视频时间分布诊断图" width="100%">
  </a>
</p>
<p align="center"><em>补充数据诊断图｜外部效价—唤醒度覆盖及其随视频和归一化播放时间的描述性变化。</em></p>

## 从训练到后处理的完整流程

以下命令覆盖特征准备、固定划分训练、五折训练、MAE 评估与来源分解、外部评估、模型包导出和端到端推理。正式训练会使用 GPU 并持续较长时间；如仅检查训练代码，可在固定划分命令中加入 `--test-mode`。

```bash
# 1. 固定 20/4 参与者划分训练
PYTHONPATH=src .venv/bin/python scripts/train_split.py --device auto

# 2. 五折参与者留出训练
PYTHONPATH=src .venv/bin/python scripts/train_cv.py \
  --device auto --metrics-json artifacts/cv_metrics.json

# 3. 五折 MAE 评估与来源分解
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate.py \
  --blend-checkpoints \
  --output-json artifacts/source_evaluation.json \
  --source-data-csv artifacts/source_data_components.csv

# 4. 外部参与者独立评估与分层源数据
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data

# 5. 导出并验证本地模型包
.venv/bin/python scripts/export_model_bundle.py
.venv/bin/python scripts/validate_model_bundle.py \
  artifacts/model_bundle_source_explicit.zip \
  --subject test_1 --video 1 --count 8

# 6. 单元测试
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

本项目已在本地实际跑通上述完整链路，包括从原始 MAT 文件重建约 1.1 GB 特征缓存、固定划分训练、五折训练、MAE 评估与来源分解、外部评估、模型包导出和端到端推理。完整运行产物保存在忽略目录 `artifacts/full_pipeline_run/`，不会覆盖正式检查点。

## 数据与共享边界

仓库仅提交源代码与必要的复现文档。本地数据、特征缓存、模型检查点、生成的模型包、评估产物和账户凭据均不纳入版本控制；共享前应核对数据许可证，并单独确认模型检查点是否允许重新分发。
