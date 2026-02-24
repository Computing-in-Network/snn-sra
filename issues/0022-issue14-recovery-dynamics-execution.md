# Issue #14 - 故障恢复动力学实验（T50/T90/AUC）执行记录

GitHub Issue: https://github.com/unicorners-compin/snn-sra/issues/14

## 目标

量化故障冲击后的恢复动态，包括：
- `MaxDrop`
- `T50`
- `T90`
- `AUC_recovery`

对比算法：`v1` / `v2` / `ospf_sync` / `ecmp` / `ppo`。

## 执行命令（基础验证）

```bash
python3 scripts_flow/recovery_dynamics_eval.py \
  --algos v1,v2,ospf_sync,ecmp,ppo \
  --topos ba,er \
  --sizes 50,100 \
  --seeds 1 \
  --steps 120 \
  --fail-step 70 \
  --failure-profiles single \
  --pre-window 20 \
  --snn-mode snn_event_dv \
  --out-prefix run_dir/issue14_recovery_smoke_20260224
```

输出：

- `run_dir/issue14_recovery_smoke_20260224_recovery_runs.csv`
- `run_dir/issue14_recovery_smoke_20260224_recovery_summary.csv`
- `run_dir/issue14_recovery_smoke_20260224_recovery_significance.csv`

## 说明

本次先做 smoke 验证，确认脚本可运行并产出预期列。完整矩阵（`seeds 1-20`）可在后续继续追加到同一 issue 结果体系后统一归档。
