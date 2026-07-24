# 本地 MER-PS 研究数据

本目录只保存本地数据说明。原始数据、下载缓存、特征数组和账户令牌均不纳入版本控制。

## 目录约定

```text
data/
├── MER_PS_trainval/                         # 24 名开发集参与者
├── feature_cache/                           # 训练特征缓存
└── download/
    ├── MER_PS_trainval.zip                  # 训练/验证压缩包
    └── MER_PS_public_evaluation/            # 4 名外部评估参与者
```

训练、五折 MAE 评估和特征提取默认使用 `data/MER_PS_trainval/`。外部独立评估与来源分解默认使用 `data/download/MER_PS_public_evaluation/`。

## 下载训练/验证数据

训练/验证数据仓库：<https://huggingface.co/datasets/MER-PS/MER-PS-trainval>

该数据需要申请访问权限。账户获准访问后运行：

```bash
bash scripts/download_data.sh
```

压缩包保存为：

```text
data/download/MER_PS_trainval.zip
```

解压前可检查：

```bash
unzip -tq data/download/MER_PS_trainval.zip
```

解压后应确保数据根目录命名为 `data/MER_PS_trainval/`。

## 下载外部评估数据

项目根目录中的 `huggingface_token.json` 由下载脚本读取，其 JSON 字段为 `huggingface_token`。令牌文件已被忽略，不得写入代码、日志或版本控制。

将数据提供方给出的仓库标识作为环境变量传入：

```bash
MERPS_EXTERNAL_REPO_ID='<外部数据仓库标识>' \
  bash scripts/download_external_data.sh
```

也可显式指定目标目录：

```bash
MERPS_EXTERNAL_REPO_ID='<外部数据仓库标识>' \
  bash scripts/download_external_data.sh \
  '<外部数据仓库标识>' \
  data/download/MER_PS_public_evaluation
```

下载脚本使用 Hugging Face CLI 与并行传输扩展。相关 Python 依赖已列入 `requirements.txt`。

## 外部数据规模与结构

| 属性 | 数值 |
| --- | ---: |
| 参与者数量 | 4 |
| 视频数量 | 15 |
| 试验数量 | 60 |
| 1 Hz 样本数量 | 6,143 |
| EEG/fNIRS 大型文件 | 16 |
| 标注 MAT 文件 | 4 |

外部数据根目录包含：

```text
sample_ids.csv
targets.csv
annotations/
data/
fNIRS_coordinates.csv
fNIRS_reservations.csv
Targeted_emotions.txt
```

每个 `data/<subject>/` 目录包含 EEG、fNIRS 试验记录和对应静息基线。

## 完整性与本地评分

当前本地副本已通过：

- 27/27 个文件字节数校验；
- 16/16 个大型生理文件 SHA-256 校验；
- CSV 目标与 MAT 标注逐值一致性校验；
- 6,143 个样本键的唯一性、顺序和时间连续性校验。

重新运行数据审计、外部 MAE 评估与来源分解：

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python scripts/evaluate_external.py \
  --source-data-dir artifacts/external_source_data
```

脚本把数据审计、总体指标、参与者/视频/时间分层指标和逐样本成对预测写入 `artifacts/external_evaluation/`。该目录可由代码重新生成，因此不上传仓库。

## 数据使用边界

两部分数据的本地说明均记录为 CC BY-NC-SA 4.0，仅用于非商业科学研究。使用或重新分发前，应再次核对数据提供方的访问条件。详细任务结构、信号定义和项目中的评估作用见 [`../docs/dataset.md`](../docs/dataset.md)。
