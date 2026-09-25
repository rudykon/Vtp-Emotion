---
hide:
  - toc
---

<section class="project-hero">
  <div class="project-wordmark">
    <img src="../assets/brand/wordmark.svg" alt="Vtp-Emotion" width="460" height="94">
  </div>
  <h1>Vtp-Emotion</h1>
  <p class="project-subtitle">预测熟悉视频中新观众的情感变化</p>
  <p class="project-lead">视频—时间先验刻画群体共享的情感轨迹，EEG 与 fNIRS 提供幅度较小的个体修正。通过连续效价—唤醒度回归，分析预测准确性究竟来自哪里。</p>
  <div class="project-actions">
    <a class="md-button md-button--primary" href="demo/">本地演示</a>
    <a class="md-button" href="https://github.com/rudykon/Vtp-Emotion" target="_blank" rel="noopener">查看 GitHub</a>
    <a class="md-button" href="guide/method/">方法</a>
    <a class="md-button" href="research/evidence/">实验结果</a>
    <a class="md-button" href="reference/reproduction/">复现</a>
  </div>
</section>

## 研究设定与方法

<div class="setting-layout">
<figure class="paper-figure">
  <a href="../assets/figures/icassp2027/method_overview.pdf" target="_blank" rel="noopener" aria-label="视频—时间先验与 EEG–fNIRS 固定融合 (PDF)">
    <img src="../assets/figures/icassp2027/method_overview.png" alt="视频—时间先验与 EEG–fNIRS 固定融合" loading="lazy">
  </a>
  <figcaption>共享的视频—时间轨迹与新观众生理预测经固定权重融合。输出曲线仅作示意。</figcaption>
</figure>
  <div>
    <p>当训练与评估使用相同视频时，已知视频身份和播放时间本身就能构成强基线。Vtp-Emotion 区分这种共享反应与生理信号带来的个体修正。</p>
    <ul class="fact-list">
      <li><strong>15 个熟悉视频</strong><span>新观众、已知视频与对齐时间</span></li>
      <li><strong>1 Hz × 2</strong><span>[1, 255] 标度上的效价与唤醒度</span></li>
      <li><strong>EEG + fNIRS</strong><span>图编码器与跨模态注意力</span></li>
      <li><strong>0.99 / 0.92</strong><span>效价 / 唤醒度的固定先验权重</span></li>
      <li><strong>离线预测</strong><span>生理特征包含下一秒上下文</span></li>
    </ul>
  </div>
</div>

## 主要发现

| 问题 | 报告结果 |
| --- | --- |
| 五折新参与者评估 | 融合 MAE **29.01**；视频—时间先验 **29.06**；EEG–fNIRS **47.35**。 |
| 四名额外观众 | 融合 MAE **27.72**；视频—时间先验 **28.04**；EEG–fNIRS **42.75**。 |
| 准确性来自哪里？ | 从 EEG–fNIRS 单独预测到融合的 MAE 下降中，先验在内部与外部评估中分别贡献 **99.73%** 和 **97.89%**。 |
| 生理信号是否对所有人有效？ | 外部队列中，融合使 **4 人中的 3 人**、**15 个视频中的 9 个** MAE 降低。 |

[查看评估协议与完整结果 →](research/evidence.md)

## 适用边界

<div class="scope-box">
  <ul>
    <li>评估对象是观看训练中相同 15 个视频的新观众。</li>
    <li>使用未来生理上下文，当前估计器仅支持离线预测。</li>
    <li>检查点与权重选择未完全嵌套，收益按描述性结果解释。</li>
    <li>尚未评估未见视频或跨站点泛化。</li>
  </ul>
</div>
