# 研究所用 MER-PS 数据

## 数据组成

本研究使用两个互不重叠的参与者集合：24 名开发集参与者用于训练与五折 MAE 评估，4 名外部参与者用于独立验证及来源分解。两部分数据都包含同步 EEG、fNIRS、静息基线和 1 Hz 效价—唤醒度标注。

| 数据部分 | 参与者数 | 视频数 | 试验数 | 秒级样本数 | 默认本地路径 |
| --- | ---: | ---: | ---: | ---: | --- |
| 训练/验证数据 | 24 | 15 | 360 | 36,864 | `data/MER_PS_trainval/` |
| 外部评估数据 | 4 | 15 | 60 | 6,143 | `data/download/MER_PS_public_evaluation/` |

两部分数据均采用 CC BY-NC-SA 4.0 许可证，仅用于非商业科研。下载、使用或重新分发前，应再次核对数据提供方的访问条件，并保护匿名参与者隐私。

## 研究任务与标签

MER-PS 记录参与者观看情绪诱发视频时的同步 EEG 与 fNIRS 信号，用于连续效价—唤醒度回归。动态标签以 1 Hz 记录两个维度：

- `valence`：效价，表示情感的愉悦程度；
- `arousal`：唤醒度，表示情感的激活程度。

两个维度均采用 `[1, 255]` 的整数尺度，中性中心为 128。

## 信号结构

每个参与者目录包含：

```text
EEG_baselines.mat
EEG_videos.mat
fNIRS_baselines.mat
fNIRS_videos.mat
```

动态标注位于 `annotations/`，每名参与者对应一个 MAT 文件。EEG 记录包含 64 个通道，fNIRS 在 51 个通道上包含 6 类信号；每次试验另有 5 秒静息片段。EEG 数组按“通道 × 时间”组织，fNIRS 数组按“信号类型 × 通道 × 时间”组织。

外部评估目录还包含：

```text
sample_ids.csv
targets.csv
annotations/<subject>_label.mat
data/<subject>/
```

`sample_ids.csv` 定义样本顺序与参与者、视频、秒级时间戳；`targets.csv` 以逐行形式保存效价与唤醒度；MAT 标注提供同一目标的原始试验级组织。

## 本地下载

训练/验证数据仓库为：<https://huggingface.co/datasets/MER-PS/MER-PS-trainval>。获得访问权限后运行：

```bash
bash scripts/download_data.sh
```

外部评估数据通过本地令牌文件下载。将数据提供方给出的仓库标识放入环境变量：

```bash
MERPS_EXTERNAL_REPO_ID='<外部数据仓库标识>' \
  bash scripts/download_external_data.sh
```

脚本默认读取项目根目录中的 `huggingface_token.json`，并把数据写入 `data/download/MER_PS_public_evaluation/`。令牌文件、下载目录和所有原始数据均已由 `.gitignore` 排除。

## 外部数据完整性审计

本地下载完成后已执行三层校验：

- 27/27 个仓库文件的本地字节数与下载元数据一致；
- 16/16 个大型 EEG/fNIRS 生理文件的 SHA-256 与远端对象标识一致；
- `targets.csv` 与 4 个 MAT 标注文件逐值一致，差异计数为 0。

评估脚本还验证：

- `sample_ids.csv` 与 `targets.csv` 顺序完全一致且无重复样本键；
- 每个参与者—视频试验的时间戳从 0 连续递增；
- 每个试验的样本数与对应 MAT 标签长度一致；
- 所有目标均为有限值并位于 `[1, 255]`。

审计结果写入：

```text
artifacts/external_evaluation/data_audit.json
artifacts/external_evaluation/trial_summary.csv
```

## 数据在论文中的作用

所有参与者观看相同且时间对齐的视频，因此论文把首要任务定义为降低“新观众观看熟悉视频”时的 MAE。每个外层折内只使用训练参与者构建视频—时间先验，并将其与 EEG--fNIRS 分支固定融合；融合预测器用于取得最低 MAE，先验则提供低成本群体基线。

外部数据首先用于验证最低 MAE 是否在新的参与者群体上复现；确认主结果后，再利用逐样本成对预测分析：

- 全局标签中心与视频身份的差异；
- 视频身份与视频内时间动态的差异；
- EEG--fNIRS 分支在强刺激先验之上的残差增量；
- 增量在参与者、视频和归一化视频时间上的异质性。

当前协议支持关于“新观众观看这 15 个熟悉视频”的低 MAE 结论，但不能证明模型能够泛化到未见视频。视频剪辑、广告投放和内容推荐等用途也尚未经过下游验证。若研究目标扩展到新内容或刺激无关的生理解码，应进一步采用视频留出或参与者×刺激交叉留出设计。

## 本地推理输入与输出

模型包输入目录采用：

```text
sample_ids.csv
data/<participant_id>/
  EEG_baselines.mat
  EEG_videos.mat
  fNIRS_baselines.mat
  fNIRS_videos.mat
```

推理结果写入 `predictions.csv`：

```text
sample_id,valence,arousal
```

`sample_id` 唯一标识样本，`valence` 和 `arousal` 分别对应两个连续情感维度的预测。
