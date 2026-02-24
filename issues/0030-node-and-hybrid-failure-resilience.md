# Issue - 节点失效与混合失效（节点+链路）抗毁实验

## 依赖

- 依赖：故障恢复动力学实验

## 目标

补齐当前以链路失效为主的空缺，验证 SNN-SRA 面对节点失效和混合失效时的稳健性。

## 实验设计

1. 仅节点失效（random / targeted）
2. 节点+链路混合失效（交替或同时注入）
3. 失效持续 vs 短时抖动（flap）

## 输出

- `*_node_failure_runs.csv`
- `*_hybrid_failure_runs.csv`
- `*_summary.csv`
- `*_significance.csv`

## 核心指标

- `pdr_final/post`
- `loss_final`
- `recovery metrics`（T50/T90/AUC）

## MinIO 与清理

- 按总控 issue 协议上传和清理
