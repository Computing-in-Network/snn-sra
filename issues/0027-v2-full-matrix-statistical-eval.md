# Issue - V2 全矩阵统计主实验（v2 vs v1）

## 依赖

- 依赖：实验总路线图与 MinIO 协议 issue

## 目标

在完整矩阵上比较 `formula_mode=v2` 与 `v1`，给出论文主结论级统计证据。

## 实验矩阵

- 拓扑：`ba, er`
- 规模：`50, 100`
- seeds：`1-20`
- steps：`240`
- fail-step：`150`
- 故障：`single, frequent`
- 路由模式：`snn_event_dv`（主）+ `snn_spike_native`（补）

## 输出

- `*_runs.csv`
- `*_summary.csv`
- `*_significance.csv`（v2-v1 差值、CI、p-value）

## 核心指标

- `pdr_final`, `loss_final`, `delay_final`, `hop_final`
- `pdr_post`, `delay_post`

## MinIO 与清理

- 按总控 issue 的协议上传
- 上传后删除本地 `run_dir` 结果副本
