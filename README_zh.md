<p align="center">
  <a href="README.md">English</a> · <strong>中文</strong>
</p>

<p align="center">
  <img src="docs/brand-mark.svg" width="520" alt="MER Affect 品牌标识">
</p>

<h1 align="center">低 MAE EEG–fNIRS 连续情感回归</h1>

<p align="center">
  <strong>面向熟悉视频新观众的效价—唤醒度曲线预测</strong><br>
  一套将低成本视频—时间群体先验与 EEG–fNIRS 预测结合的可复现 Python 流程。
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-%E2%89%A53.10-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 或更高版本"></a>
  <a href="#results"><img src="https://img.shields.io/badge/Objective-MAE%20%E2%86%93-F28E2B?style=flat-square" alt="首要目标：降低 MAE"></a>
  <a href="#getting-started"><img src="https://img.shields.io/badge/Tests-15%2F15%20passing-2CA02C?style=flat-square" alt="15 项测试全部通过"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-4C78A8?style=flat-square" alt="Apache License 2.0"></a>
  <a href="https://huggingface.co/datasets/MER-PS/MER-PS-trainval"><img src="https://img.shields.io/badge/Data-Hugging%20Face-FFD21E?style=flat-square&logo=huggingface&logoColor=black" alt="Hugging Face 数据"></a>
</p>

<p align="center">
  <a href="#project-overview">项目概览</a> ·
  <a href="#results">主要结果</a> ·
  <a href="#analysis">结果分析</a> ·
  <a href="#getting-started">快速开始</a> ·
  <a href="#data">数据准备</a> ·
  <a href="#reproduction">复现与审计</a> ·
  <a href="#open-source-license">开源许可</a>
</p>

> [!IMPORTANT]
> **首要目标：**降低平均绝对误差（MAE）。生理分支、视频身份先验和视频—时间先验之间的对比，放在主结果之后，用于解释 MAE 降幅来自哪里。

<a id="project-overview"></a>
## 项目概览

本项目预测新观众观看熟悉且时间对齐的视频时，每秒连续效价与唤醒度。视频身份和播放时间在推理阶段天然可用，因此协议匹配的视频—时间先验能够以很低成本提供强群体反应基线：五折评估在各训练折内拟合先验，留出评估则在完整开发队列上拟合先验。固定融合再将其与 EEG–fNIRS 分支结合，并在两种协议下均取得最低总体 MAE。

| 研究目标 | 已实现方法 | 评估边界 |
| --- | --- | --- |
| 降低新观众观看已知视频时的 MAE | 协议匹配的视频—时间先验 + EEG–fNIRS 分支 + 固定融合 | 在相同 15 个熟悉视频上进行参与者不重叠评估 |
| 提供可用的群体反应基线 | 推理时使用视频身份和视频内时间 | 不属于跨站点、跨条件或未见视频验证 |
| 解释误差降低的来源 | 按参与者、视频和归一化时间进行来源分解 | 生理信号对比属于主结果之后的解释性分析 |

潜在用途包括预测观众的大致情绪曲线，为视频剪辑、广告投放或内容推荐提供群体反应基线，以及为新观众的情绪预测提供粗略初始化；这些目前是应用动机，尚未验证具体下游效果。

<p align="center">
  <a href="docs/figures/method_overview.pdf">
    <img src="docs/figures/method_overview.png" alt="视频—时间先验与 EEG–fNIRS 固定融合方法概览" width="92%">
  </a>
</p>
<p align="center"><em>图 1｜视频—时间群体先验与 EEG–fNIRS 预测通过固定融合共同用于降低 MAE。</em></p>

<a id="results"></a>
## MAE 主结果

| 评估协议 | 队列规模 | EEG–fNIRS 分支 | 视频—时间先验 | 固定融合 |
| --- | --- | ---: | ---: | ---: |
| 五折参与者留出 | 24 名参与者 · 15 个视频 · 36,864 个样本 | 47.35 | 29.06 | **29.01** |
| 参与者不重叠留出 | 4 名新观众 · 60 次试验 · 6,143 个样本 | 42.75 | 28.04 | **27.72** |

**协议细节。**五折结果使用 5 个折外生理模型、分别在各训练折内拟合的视频—时间先验，并直接按浮点预测计分。留出结果使用 6 模型生理集成（1 个全开发集模型加 5 个折模型）、在完整开发队列上拟合的视频—时间先验，并在计分前通过 `numpy.rint` 四舍五入后裁剪至 `[1, 255]`。因此，两行结果只能在各自协议内解释：**29.01 与 27.72 不能被视为同一估计器跨队列的直接提升。**

固定融合在两种评估中均取得最低 MAE。内部评估中，视频—时间先验仅比固定融合高 0.05，并相对 EEG–fNIRS 分支降低 18.29；参与者不重叠留出评估中，固定融合在视频—时间先验基础上继续降低 0.32。

<p align="center">
  <a href="docs/figures/source_dominance.png">
    <img src="docs/figures/source_dominance.png" alt="内部参与者留出 MAE 与来源分解" width="52%">
  </a>
</p>
<p align="center"><em>图 2｜内部参与者留出 MAE：视频—时间先验解释主要误差降幅，固定融合达到最低值。</em></p>

<details>
<summary><strong>查看留出队列完整来源分解</strong></summary>

| 预测来源 | 总体 MAE |
| --- | ---: |
| 全局常数 | 44.33 |
| 视频身份先验 | 33.36 |
| 视频—时间先验 | 28.04 |
| EEG–fNIRS 分支 | 42.75 |
| **固定融合** | **27.72** |

</details>

<p align="center">
  <a href="docs/figures/external_prediction_quality.png">
    <img src="docs/figures/external_prediction_quality.png" alt="参与者不重叠留出队列的固定融合预测值与真实值" width="92%">
  </a>
</p>
<p align="center"><em>图 3｜固定融合预测值与真实值的关系；两维预测均存在量表中部收缩的现象。</em></p>

> [!NOTE]
> 该协议只确立参与者互不重叠，不属于跨站点或跨条件的独立外部验证，也不评估未见视频。

<a id="analysis"></a>
## 取得低 MAE 后的分析

以下对比用于解释最低 MAE 的来源与适用边界，不取代降低 MAE 这一首要目标。

- 从 EEG–fNIRS 分支到固定融合的内部总降幅中，约 **99.7%** 已由折内视频—时间先验实现。
- 留出评估中，视频身份对应 **10.97** 的总体 MAE 降幅，视频内时间对应额外 **5.32** 的描述性降幅。
- 融合增量具有异质性，只在 **4 名参与者中的 3 名**和 **15 个视频中的 9 个**上改善。
- 时间先验优势具有阶段性：第一个归一化时间区间中，视频身份与视频—时间先验的 MAE 分别为 **45.53** 和 **13.40**；最后五个区间中视频身份先验略优。

详细方法和分析见 [`docs/method.md`](docs/method.md) 与 [`docs/ablation.md`](docs/ablation.md)。

<details>
<summary><strong>展开更多留出队列分析图</strong></summary>
<br>

<p align="center">
  <a href="docs/figures/external_source_decomposition.png">
    <img src="docs/figures/external_source_decomposition.png" alt="留出队列 MAE 来源分解及参与者、视频和时间异质性" width="95%">
  </a>
</p>
<p align="center"><em>图 4｜总体改善同时包含参与者、视频与播放时间层面的局部增益和损失。</em></p>

<p align="center">
  <a href="docs/figures/external_video_time_mae.png">
    <img src="docs/figures/external_video_time_mae.png" alt="视频—时间先验与固定融合的视频×归一化时间 MAE 热力图" width="95%">
  </a>
</p>
<p align="center"><em>图 5｜固定融合的小幅总体增益并非均匀存在于所有视频×时间单元。</em></p>

</details>

<a id="getting-started"></a>
## 快速开始

```bash
git clone https://github.com/rudykon/MER2026track4-EEG-fNIRS-Affect-Regression.git
cd MER2026track4-EEG-fNIRS-Affect-Regression

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
source .venv/bin/activate

# 轻量仓库验证，不需要原始数据。
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

预期结果为 **15 项测试全部通过**。正式训练与评估需要 MER-PS 数据。默认依赖安装面向 CUDA 12.1 的 PyTorch 2.5.1；推荐使用 NVIDIA GPU，但 `--device auto` 可回退到 CPU，纯 CPU 环境需改用对应的 PyTorch 安装包。若下载环境经过 SOCKS 代理，`socksio` 用于补齐网络依赖；留出数据下载脚本还需要系统命令 `jq`。

<a id="data"></a>
## 数据准备

| 数据组成 | 规模 | 数据仓库 | 默认本地路径 |
| --- | ---: | --- | --- |
| 训练/验证数据 | 24 名参与者 · 360 次试验 · 36,864 个样本 | [MER-PS 训练/验证数据](https://huggingface.co/datasets/MER-PS/MER-PS-trainval) | `data/MER_PS_trainval/` |
| 参与者不重叠留出数据 | 4 名参与者 · 60 次试验 · 6,143 个样本 | [留出评估数据](https://huggingface.co/datasets/MER-PS/MER-PS-public-leaderboard-evaluation-data) | `data/download/MER_PS_public_evaluation/` |

训练/验证数据仓库需要访问许可。请先在 Hugging Face 页面申请访问，在激活虚拟环境后完成认证，再下载压缩包：

```bash
hf auth login
bash scripts/download_data.sh
```

脚本只下载并执行 ZIP 完整性检查，不负责解压；压缩包保存为 `data/download/MER_PS_trainval.zip`。先查看顶层目录，再解压并重命名，避免形成重复嵌套：

```bash
unzip -Z1 data/download/MER_PS_trainval.zip | head

MERPS_ARCHIVE='data/download/MER_PS_trainval.zip'
MERPS_TOP_DIR="$(unzip -Z1 "$MERPS_ARCHIVE" | sed -n '1{s:/$::;p;q}')"
test -n "$MERPS_TOP_DIR"
test ! -e data/MER_PS_trainval
unzip -q "$MERPS_ARCHIVE" -d data/download
mv "data/download/$MERPS_TOP_DIR" data/MER_PS_trainval
```

使用本地 `huggingface_token.json` 下载参与者不重叠留出数据：

```bash
MERPS_EXTERNAL_REPO_ID='MER-PS/MER-PS-public-leaderboard-evaluation-data' \
  bash scripts/download_external_data.sh
```

令牌文件、原始数据和下载目录均由 `.gitignore` 排除。留出数据脚本依赖 Hugging Face CLI 与 `jq`，只在本地读取令牌，不会把令牌写入下载文件、日志或版本控制；查看和解压训练压缩包还需要 `unzip`。使用或重新分发前，请核对各数据仓库当前条款。

完整目录结构、信号定义、完整性校验和数据使用边界见 [`data/DATASET.md`](data/DATASET.md) 与 [`docs/dataset.md`](docs/dataset.md)。

<details>
<summary><strong>展开补充数据诊断图</strong></summary>
<br>

<p align="center">
  <a href="docs/figures/external_data_landscape.png">
    <img src="docs/figures/external_data_landscape.png" alt="留出队列效价—唤醒度覆盖与视频—时间差异" width="92%">
  </a>
</p>
<p align="center"><em>补充数据诊断｜留出队列标签覆盖及其随视频和归一化播放时间的描述性变化。</em></p>

</details>

<a id="reproduction"></a>
## 复现与审计流程

以下公开命令覆盖显式特征重建、固定划分与五折训练、先验构建、MAE 评估、来源分解、留出队列评估、模型包导出、验证和测试。正式训练可能持续较长时间；`--test-mode` 可执行三轮训练检查，但仍需要已准备的数据。精确重建文中报告的留出估计器，还需要下文说明的全开发集检查点。

> [!CAUTION]
> 以下命令使用默认的 `data/feature_cache/`、`checkpoints/` 与 `artifacts/` 路径，特征重建与训练可能替换同名文件。若需保留已有本地运行，请使用全新检出目录，或通过 `--cache-dir`、`--model-dir`、`--log-path`、`--output`、`--checkpoint-dir` 和 `--output-dir` 指定隔离路径。

```bash
# 0. 从原始 MAT 文件强制重建特征并检查可读取性，然后停止
PYTHONPATH=src .venv/bin/python scripts/train_split.py \
  --prepare-only --no-cache --device auto

# 1. 固定 20/4 参与者划分训练
PYTHONPATH=src .venv/bin/python scripts/train_split.py --device auto

# 2. 五折参与者留出训练
PYTHONPATH=src .venv/bin/python scripts/train_cv.py \
  --device auto --metrics-json artifacts/cv_metrics.json

# 3. 构建留出评估和模型包导出所需的视频—时间先验
PYTHONPATH=src .venv/bin/python -m merps.prior

# 4. 五折 MAE 评估与来源分解
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate.py \
  --blend-checkpoints \
  --output-json artifacts/source_evaluation.json \
  --source-data-csv artifacts/source_data_components.csv

# 5. 留出队列评估：优先使用 final_v3.pt，否则回退到 best_v3.pt
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data

# 6. 导出并验证本地模型包
.venv/bin/python scripts/export_model_bundle.py
.venv/bin/python scripts/validate_model_bundle.py \
  artifacts/model_bundle_source_explicit.zip \
  --subject test_1 --video 1 --count 8

# 7. 单元测试
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

文中报告的留出 MAE **27.72** 使用 `checkpoints/final_v3.pt` 作为六模型生理集成中的全开发集模型。本仓库目前没有提供重建该检查点的训练命令，训练后检查点也不纳入版本控制。因此，在干净仓库中，留出评估与模型包导出会回退到固定划分生成的 `checkpoints/best_v3.pt`；这条公开回退路径可以完整运行，但其留出指标不应被期望精确复现 **27.72**。

现有流程已在本地完整跑通，包括约 1.1 GB 特征缓存重建、固定划分与五折训练、MAE 评估、来源分解、留出评估、模型包导出和端到端推理。此前隔离审计的产物保存在被忽略的 `artifacts/full_pipeline_run/`。上方命令则使用各脚本的默认路径：训练检查点写入 `checkpoints/`，一般评估与模型包写入 `artifacts/`，留出评估写入 `artifacts/external_evaluation/`。

<a id="repository"></a>
## 项目结构

| 路径 | 作用 |
| --- | --- |
| `src/merps/` | 特征提取、视频—时间先验、生理模型、校准和推理 |
| `scripts/` | 数据下载、训练、评估、来源分解和模型包工具 |
| `tests/` | 指标、校准、来源构建和模型包配置单元测试 |
| `docs/` | 方法、数据集和主结果之后的分析文档 |
| `data/` | 跟踪本地数据说明；原始数据、下载文件和特征缓存均被忽略 |
| `checkpoints/` | 本地生理模型检查点与先验；不纳入版本控制 |
| `artifacts/` | 日志、评估产物、图件和模型包；不纳入版本控制 |

<a id="scope"></a>
## 适用范围与共享边界

- 当前结论只适用于新观众观看相同的 15 个熟悉视频。
- 本研究不证明向未见视频、新站点或新实验条件迁移。
- 视频剪辑、广告投放和内容推荐等下游效果尚未验证。
- 本地数据、特征缓存、检查点、生成模型包、评估产物和账户凭据均不纳入版本控制。
- 数据集、模型检查点、生成产物和第三方组件在重新分发前需分别核对其条款。

<a id="open-source-license"></a>
## 开源许可证

本仓库完整提供了本项目评估的全部算法源码实现。除另有说明外，仓库中由项目作者编写的源代码采用 [Apache License 2.0](LICENSE) 开源；数据集、模型检查点、生成产物和第三方依赖仍分别适用其自身条款。

