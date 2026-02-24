# Issue - V2 开销复评估与终稿复现实验包

## 依赖

- 依赖：V2 参数敏感性与稳定区间实验

## 目标

在 V2 最终配置下，完成“收益-代价”闭环和终稿可复现实验包。

## 任务

1. 复杂度与开销复评估（wall-clock / control msgs）
2. 收益-代价比重算（对 OSPF/OSPF_SYNC/ECMP/PPO）
3. 汇总最终结果包（论文图表所需 CSV）
4. 产出 `REPRODUCE.md`（一键复现实验命令）

## 输出

- `*_overhead_runs.csv`
- `*_overhead_summary.csv`
- `*_benefit_cost.csv`
- `*_final_bundle_manifest.json`
- `run_dir/REPRODUCE.md`

## MinIO 与清理

- 按总控 issue 协议上传和清理
- 清理后保留最小索引文件（manifest + reproduce 文档）
