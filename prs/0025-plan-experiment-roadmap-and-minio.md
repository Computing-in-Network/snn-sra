# PR Draft: Plan Issue #11 - 实验路线图与 MinIO 归档规范

## 关联 Issue

- refs #11

## Why

将后续实验从“临时执行”升级为“可追踪计划驱动”，并统一 MinIO 上传与本地清理规范，确保每个实验结果可复现、可检索。

## 本 PR 内容

- 新增实验计划 issue 文档：
  - `issues/0026-experiment-roadmap-and-minio-protocol.md`
  - `issues/0027-v2-full-matrix-statistical-eval.md`
  - `issues/0028-targeted-attack-and-kfailure-boundary.md`
  - `issues/0029-recovery-dynamics-t50-t90-auc.md`
  - `issues/0030-node-and-hybrid-failure-resilience.md`
  - `issues/0031-control-plane-impaired-robustness.md`
  - `issues/0032-v2-parameter-sensitivity-and-stability.md`
  - `issues/0033-v2-overhead-and-final-repro-package.md`

## GitHub Issues（已创建）

- #11 实验总路线图与 MinIO 归档协议（总控）
- #12 V2 全矩阵统计主实验（v2 vs v1）
- #13 定向攻击与 k-failure 抗毁边界实验
- #14 故障恢复动力学实验（T50/T90/AUC）
- #15 节点失效与混合失效（节点+链路）抗毁实验
- #16 控制面受限条件下的鲁棒性实验
- #17 V2 参数敏感性与稳定区间实验
- #18 V2 开销复评估与终稿复现实验包

## 备注

- 本 PR 是计划与规范，不包含实验结果。
- issue #12~#18 将按顺序逐个执行，每次完成后上传 MinIO 并清理本地结果。
