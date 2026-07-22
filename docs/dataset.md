# 研究所用 MER-PS 数据

## 数据仓库与本地路径

- 数据集仓库：<https://huggingface.co/datasets/MER-PS/MER-PS-trainval>
- 本地解压路径：`data/MER_PS_trainval/`
- 生成的特征缓存：`data/feature_cache/`

数据集采用 CC BY-NC-SA 4.0 许可证，并需要通过数据仓库申请访问权限。下载、使用或重新分发数据前，应遵守仓库中给出的访问条件和许可证要求。

## 研究任务

MER-PS 包含被试观看情绪诱发视频时同步采集的 EEG 与 fNIRS 信号，用于连续效价—唤醒度回归。动态标签以 1 Hz 频率记录两个连续情感维度：

- `valence`：效价，表示情感的愉悦程度；
- `arousal`：唤醒度，表示情感的激活程度。

两个维度均采用 `[1, 255]` 的原始标签范围，中性中心为 128。

## 数据结构

本地训练/验证数据包含 24 个匿名被试标识（`test_1` 至 `test_24`）。每名被试均观看相同的 15 个视频。

| 数据属性 | 数值 |
| --- | ---: |
| 被试数量 | 24 |
| 每名被试的视频数量 | 15 |
| 试验数量 | 360 |
| 1 Hz 动态标签数量 | 36,864 |
| EEG 通道数 | 64 |
| fNIRS 通道数 | 51 |
| fNIRS 信号类型数 | 6 |
| 静息片段长度 | 5 秒 |

每个被试目录包含以下信号文件：

```text
EEG_baselines.mat
EEG_videos.mat
fNIRS_baselines.mat
fNIRS_videos.mat
```

动态标注位于 `annotations/` 目录，每名被试对应一个 MAT 文件。EEG 数组的组织形式为“通道 × 时间”，fNIRS 数组的组织形式为“信号类型 × 通道 × 时间”。

## 数据在论文中的作用

所有被试观看相同且时间对齐的视频，因此被试划分不会移除视频标识和时间戳。该结构可能使模型仅凭刺激坐标便获得较强的群体情感预测。论文据此在每个外层折内仅使用训练被试构建视频—时间先验，并在完全相同的留出样本上比较该先验与 EEG--fNIRS 生理分支。

当前数据和评估协议支持关于“新被试观看这 15 个已见视频”的结论，但不能证明模型能够泛化到未见视频。若研究目标是刺激无关的生理解码，应进一步采用视频留出或被试×刺激交叉留出设计。

## 本地推理输入与输出

复现模型包要求输入目录采用以下结构：

```text
sample_ids.csv
data/<participant_id>/
  EEG_baselines.mat
  EEG_videos.mat
  fNIRS_baselines.mat
  fNIRS_videos.mat
```

推理结果写入 `predictions.csv`，其中包含以下三列：

```text
sample_id,valence,arousal
```

`sample_id` 用于唯一标识样本，`valence` 和 `arousal` 分别对应效价与唤醒度预测。
