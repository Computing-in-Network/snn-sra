# Issue - 定向攻击与 k-failure 抗毁边界实验

## 依赖

- 依赖：V2 全矩阵统计主实验

## 目标

量化 SNN-SRA 在“抗毁性”核心问题上的边界：

1. 随机故障 vs 定向攻击
2. k-failure 递增下的崩溃阈值

## 实验设计

- 攻击策略：
  - `random`
  - `edge_betweenness_topk`
  - `node_betweenness_topk`
- `k` 从 1 递增到 K（按规模比例）
- 记录每个 k 下指标曲线

## 输出

- `*_degradation_curve.csv`
- `*_boundary.csv`（robust/weakened/failed）
- `*_significance.csv`

## 核心指标

- PDR 退化幅度
- Loss 增长幅度
- 连通率（如可计算）
- 崩溃阈值 \(k^\*\)

## MinIO 与清理

- 按总控 issue 协议上传和清理
