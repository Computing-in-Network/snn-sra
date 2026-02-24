# Issue #16 - 控制面受限条件下的鲁棒性实验（执行记录）

关联 Issue： https://github.com/unicorners-compin/snn-sra/issues/16

## 目标

验证 SNN-SRA 在控制面受限场景下的鲁棒性，控制维度：
- 广播丢失率
- 控制信息延迟
- 最小广播周期上调（限频）
- 路由表 TTL 调整

## 关键实现文件

- [scripts_flow/control_plane_impaired_eval.py](/home/zyren/snn-sra/scripts_flow/control_plane_impaired_eval.py)
- [scripts_flow/snn_simulator.py](/home/zyren/snn-sra/scripts_flow/snn_simulator.py)（新增控制平面可控丢失/延迟/限频参数）

## Smoke 验证命令

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

## 输出文件

- `run_dir/issue16/issue16_smoke_cp_impaired_runs.csv`
- `run_dir/issue16/issue16_smoke_cp_impaired_summary.csv`
- `run_dir/issue16/issue16_smoke_cp_impaired_significance.csv`
- `run_dir/issue16/issue16_smoke_cp_boundary.csv`

## MinIO 上传信息

- 上传路径：`snn-sra-exp/issue16/run_20260224_193541_smoke/`
- 已上传对象：
  - `issue16_smoke_cp_impaired_runs.csv`
  - `issue16_smoke_cp_impaired_summary.csv`
  - `issue16_smoke_cp_impaired_significance.csv`
  - `issue16_smoke_cp_boundary.csv`

## 本地清理

- 已将本次 smoke 数据保留在 `run_dir/issue16/`，待完整矩阵完成后统一清理或归档。

## 初步结论（Smoke）

- 脚本链路可运行，所有文件输出成功。
- 控制平面事件通道已支持：
  - 丢失（`control_broadcast_loss`）
  - 延迟（`control_broadcast_delay`）
  - 最小频率约束（`control_min_broadcast_period`）
  - TTL 参数透传（`route_ttl`）
- `v1` 在该小规模配置下基于事件驱动 DV 模式表现仍存在极端退化（pdr 接近 0），这与历史实验中该参数组合一致，属于可复现行为；需在完整矩阵验证时进一步确认全域趋势。
- 下一步：按主流程完成完整矩阵跑完后上传完整结果并执行论文级解读。
