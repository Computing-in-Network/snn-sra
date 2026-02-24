# Issue - 故障恢复动力学实验（T50/T90/AUC）

## 依赖

- 依赖：定向攻击与 k-failure 抗毁边界实验

## 目标

把“抗毁性”从静态终值扩展到时序恢复能力，量化故障冲击后的恢复过程。

## 指标定义

- `MaxDrop`: 故障后最深退化
- `T50`: 恢复到故障前 50% 水平所需步数
- `T90`: 恢复到故障前 90% 水平所需步数
- `AUC_recovery`: 故障后恢复曲线面积

## 实验设置

- 沿用主矩阵（ba/er, 50/100, seeds 1-20）
- 对比：`v2`, `v1`, `ospf_sync`, `ecmp`, `ppo`

## 输出

- `*_recovery_runs.csv`
- `*_recovery_summary.csv`
- `*_recovery_significance.csv`

## MinIO 与清理

- 按总控 issue 协议上传和清理
