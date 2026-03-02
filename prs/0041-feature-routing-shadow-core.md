## Linked Issue

- refs #29
- refs #28

## Why

在不接入前端的前提下，先把路由核心灰度实验跑通：同一时变拓扑输入下并行评估 SNN-SRA 与 OSPF Sync，验证稳定性与控制开销差异。

## What Changed

- 新增 `scripts_flow/run_routing_shadow.py`：
  - 输入 `.json/.jsonl` 拓扑轨迹（按 step 更新边集）
  - 并行运行 `SNNSimulator` 与 `OSPFSyncSimulator`
  - 输出逐步指标 CSV 与汇总 CSV
- 更新 `README.md`：新增“无前端路由灰度入口”命令示例。

## Validation

### Commands

```bash
python3 -m py_compile scripts_flow/run_routing_shadow.py
```

### Results

- 新脚本语法校验通过。
- 入口命令与输出文件路径已在 README 给出。

## Metrics Comparison (if applicable)

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Routing-only shadow entry | None | Available | + |
| Comparable per-step outputs | None | CSV (step + agg) | + |
| Frontend dependency | Required for topology UI path | Not required | - |

## Risks

- 当前脚本假设轨迹节点 ID 为整数且与仿真节点索引一致。
- 未引入节点名（SAT-POLAR/AIR/SHIP）到索引映射层。

## Rollback

- 删除 `scripts_flow/run_routing_shadow.py`。
- 回退 README 新增段落。
