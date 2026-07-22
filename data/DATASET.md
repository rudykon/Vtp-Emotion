# 本地 MER-PS 训练/验证数据

数据集仓库：<https://huggingface.co/datasets/MER-PS/MER-PS-trainval>

## 预期本地路径

```text
data/download/MER_PS_trainval.zip
data/MER_PS_trainval/
```

解压目录包含被试生理记录、动态情感标注、元数据、试验后评分、目标情绪标签以及 fNIRS 通道信息。项目默认使用 `data/MER_PS_trainval/` 作为训练、评估和特征提取的数据根目录。

## 下载方法

该数据集需要申请访问权限。账户获准访问后，先通过 Hugging Face 命令行工具完成身份验证，再运行：

```bash
bash scripts/download_data.sh
```

脚本会将下载的压缩包保存为：

```text
data/download/MER_PS_trainval.zip
```

账户令牌应保存在项目目录之外，不应写入脚本、文档或版本控制记录。

## 完整性检查与解压

解压前可使用以下命令检查压缩包完整性：

```bash
unzip -tq data/download/MER_PS_trainval.zip
```

解压后应确保研究数据根目录命名为 `data/MER_PS_trainval/`。训练、评估、特征提取和视频—时间先验构建脚本均默认使用该路径。

## 数据使用说明

详细的数据规模、信号结构和论文中的评估作用见 `docs/dataset.md`。由于所有被试观看相同的视频，被试留出分析仍保留刺激标识与时间信息，因此需要同时报告视频—时间先验等仅刺激基线。

## 许可证

本地数据集说明记录的许可证为 CC BY-NC-SA 4.0。使用或重新分发数据前，应再次核对数据仓库中的访问条件和许可证要求。
