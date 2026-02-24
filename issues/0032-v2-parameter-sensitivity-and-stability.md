# Issue - V2 参数敏感性与稳定区间实验

## 依赖

- 依赖：控制面受限鲁棒性实验

## 目标

证明 V2 结论不是参数精调偶然，而是在合理参数扰动范围内稳定。

## 参数网格

- `stress_smooth_gain`
- `stress_smooth_center`
- `softmin_temperature`
- `switch_hysteresis`
- `route_ttl`

每个参数做单因素扰动（建议 ±20%）并做关键参数二因素交叉抽样。

## 输出

- `*_sensitivity_runs.csv`
- `*_sensitivity_summary.csv`
- `*_sensitivity_significance.csv`
- `*_stable_region.csv`（稳定区间）

## 核心指标

- 主收益：`pdr_final`, `loss_final`
- 代价：`delay_final`, `hop_final`
- 稳定性：`route_changes`, `table_updates`

## MinIO 与清理

- 按总控 issue 协议上传和清理
