# 复现

## 快速开始

```bash
git clone https://github.com/rudykon/Vtp-Emotion.git
cd Vtp-Emotion

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
source .venv/bin/activate

# 轻量仓库验证，不需要原始数据。
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

预期结果为 **15 项测试全部通过**。正式训练与评估需要 MER-PS 数据。默认依赖安装面向 CUDA 12.1 的 PyTorch 2.5.1；推荐使用 NVIDIA GPU，但 `--device auto` 可回退到 CPU，纯 CPU 环境需改用对应的 PyTorch 安装包。若下载环境经过 SOCKS 代理，`socksio` 用于补齐网络依赖；留出数据下载脚本还需要系统命令 `jq`。

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

完整目录结构、信号定义、完整性校验和数据使用边界见 [`data/DATASET.md`](https://github.com/rudykon/Vtp-Emotion/blob/main/data/DATASET.md) 与 [`docs/dataset.md`](https://github.com/rudykon/Vtp-Emotion/blob/main/docs/dataset.md)。

<details>
<summary><strong>展开补充数据诊断图</strong></summary>
<br>

<figure class="paper-figure">
<a href="../../../assets/figures/external_data_landscape.png">
    <img src="../../../assets/figures/external_data_landscape.png" alt="留出队列效价—唤醒度覆盖与视频—时间差异" width="92%">
  </a>
<figcaption>补充数据诊断｜留出队列标签覆盖及其随视频和归一化播放时间的描述性变化。</figcaption>
</figure>

</details>

## 复现与审计流程

以下公开命令覆盖显式特征重建、固定划分与五折训练、先验构建、MAE 评估、来源分解、留出队列评估、模型包导出、验证和测试。正式训练可能持续较长时间；`--test-mode` 可执行三轮训练检查，但仍需要已准备的数据。精确重建文中报告的留出估计器，还需要下文说明的全开发集检查点。

!!! warning "保留已有运行结果"

    以下命令使用默认的 `data/feature_cache/`、`checkpoints/` 与 `artifacts/` 路径，特征重建与训练可能替换同名文件。若需保留已有本地运行，请使用全新检出目录，或通过 `--cache-dir`、`--model-dir`、`--log-path`、`--output`、`--checkpoint-dir` 和 `--output-dir` 指定隔离路径。

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

训练检查点写入 `checkpoints/`；评估产物与模型包写入 `artifacts/`，其中外部队列评估写入 `artifacts/external_evaluation/`。

## 构建展示网站

网站依赖与模型训练依赖分开安装。在仓库根目录运行：

```bash
python3 -m venv .venv-site
.venv-site/bin/pip install -r requirements-docs.txt
.venv-site/bin/python scripts/build_site.py
.venv-site/bin/python -m http.server 8000 --directory site
```

构建程序将网页和选定的现有图片汇入 `build/site_docs/`，再将静态网站输出至 `site/`。`main` 分支的网站源文件更新后，GitHub Actions 自动部署。

网站仅包含选定的公开页面与图片。研究数据、模型参数、论文、方案设计修改记录及科研图片生成程序均保留在本地。
