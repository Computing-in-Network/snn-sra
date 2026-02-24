# PR Draft: Experiment Issue #14 - 故障恢复动力学（T50/T90/AUC）

## 关联 Issue

- refs #14

## 变更目标

补齐抗毁性实验的“恢复动力学”维度：
- `MaxDrop`：故障前后 PDR 降幅峰值
- `T50`：恢复到故障前 50% 目标所需步数
- `T90`：恢复到故障前 90% 目标所需步数
- `AUC_recovery`：故障后恢复曲线归一化面积

对比算法：`v1`、`v2`、`ospf_sync`、`ecmp`、`ppo`。

## 新增内容

- `scripts_flow/recovery_dynamics_eval.py`
  - 复用现有拓扑/流量生成与仿真器，增加恢复动力学指标计算。
  - 支持单故障场景的 k-time 统计、三类指标导出。
  - 输出文件：
    - `*_recovery_runs.csv`
    - `*_recovery_summary.csv`
    - `*_recovery_significance.csv`

- `issues/0022-issue14-recovery-dynamics-execution.md`
  - 本次执行记录与 smoke 运行命令。

## 执行与验证

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

结果文件已写出并用于 PR 验证。
