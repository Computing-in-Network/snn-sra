# Issue - 实验总路线图与 MinIO 归档协议（总控）

## 背景

为严格遵循 Git Flow 并保证实验可追溯，需要先建立统一路线图与数据归档协议。后续所有实验 issue 按本 issue 定义的顺序执行。

## 目标

1. 固化实验执行顺序（依赖关系）
2. 固化 MinIO 上传命名规范、元数据规范、清理规范
3. 作为后续实验 issue 的引用基准

## 执行顺序（必须按序）

1. V2 全矩阵统计主实验（v2 vs v1）
2. 定向攻击与 k-failure 抗毁边界实验
3. 故障恢复动力学实验（T50/T90/AUC）
4. 节点失效与节点+链路混合失效实验
5. 控制面退化鲁棒性实验（广播丢失/同步延迟）
6. 参数敏感性与稳定区间实验
7. V2 复杂度与收益-代价比复评估
8. 终稿汇总实验（复现实验包）

## MinIO 归档协议（后续每个 issue 必须执行）

### 存储路径

- Bucket: `snn-sra-exp`（如不存在可自动创建）
- Prefix: `issue-<id>/<run_tag>/`

### 必传文件

1. 原始结果 CSV（runs/summary/significance）
2. 运行日志（stdout/stderr）
3. `metadata.json`，字段至少包括：
   - `issue_id`
   - `git_branch`
   - `git_commit`
   - `command`
   - `start_time`
   - `end_time`
   - `host`
   - `topos/sizes/seeds/steps/failure_profiles`
   - `out_prefix`

### 上传完成后的本地清理

1. 先校验上传成功（对象存在）
2. 执行本地删除（仅删除本次 run 生成文件）
3. 在 PR 描述中写明“已上传 MinIO + 已清理本地”

## 验收标准

- 后续每个实验 issue 都显式引用本规范
- 每个 issue 的结果都能在 MinIO 按 issue 号定位
- 本地不会长期堆积大规模结果文件
