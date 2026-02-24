# PR Draft: Issue #16 - 控制面受限条件下的鲁棒性实验

## 关联 Issue

- refs #16

## 变更摘要

1. 在 SNN 仿真器控制面通道加入三类可控参数（默认关闭，保持向后兼容）：
   - `control_broadcast_loss`
   - `control_broadcast_delay`
   - `control_min_broadcast_period`
2. 新增 `scripts_flow/control_plane_impaired_eval.py`，用于完整生成：
   - `*_cp_impaired_runs.csv`
   - `*_cp_impaired_summary.csv`
   - `*_cp_impaired_significance.csv`
   - `*_cp_boundary.csv`
3. 覆盖控制面影响下的算法对比：`v1`、`v2`、`ospf_sync`、`ecmp`、`ppo`。

## 核心实现细节

1. 控制面丢失：对每次 SNN 控制广播进行概率丢弃（`control_broadcast_loss`）。
2. 控制面延迟：将广播更新任务按步数延迟应用（`control_broadcast_delay`）。
3. 控制面限频：按 `control_min_broadcast_period` 调整广播调度的最短间隔（可覆盖路由事件周期）。
4. 路由 TTL：仿真器 `route_ttl` 接口暴露为控制面受损参数之一。
5. 控制面失效场景下仍沿用统一的显著性分析框架（配对重采样 + sign-flip）。

## Smoke 验证

```bash
python3 scripts_flow/control_plane_impaired_eval.py \
  --algos v1,v2 \
  --topos ba \
  --sizes 20 \
  --seeds 1 \
  --steps 120 \
  --broadcast-losses 0,0.05 \
  --broadcast-delays 0,2 \
  --min-broadcast-periods 1,3 \
  --route-ttls 20,40 \
  --out-prefix run_dir/issue16/issue16_smoke
```

## 输出

- `run_dir/issue16/issue16_smoke_cp_impaired_runs.csv`
- `run_dir/issue16/issue16_smoke_cp_impaired_summary.csv`
- `run_dir/issue16/issue16_smoke_cp_impaired_significance.csv`
- `run_dir/issue16/issue16_smoke_cp_boundary.csv`

## 结论说明

- 本次 PR 为 Smoke 阶段：验证流程与脚本链路可运行，参数维度可控，输出完整。
- 全量矩阵跑完后，再补充最终方法级结论（尤其关于 v1/v2 的可解释退化和对比边界）。
