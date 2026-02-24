# Issue - 控制面受限条件下的鲁棒性实验

## 依赖

- 依赖：节点失效与混合失效实验

## 目标

验证 SNN-SRA 不依赖理想控制面：在控制信息延迟、丢失和限频条件下仍保持核心优势。

## 实验维度

- 广播丢失率：0%, 5%, 10%, 20%
- 广播延迟：0, 2, 5, 10 steps
- 最小广播周期上调（限频）
- 路由表 TTL 缩短/放宽

## 输出

- `*_cp_impaired_runs.csv`
- `*_cp_impaired_summary.csv`
- `*_cp_impaired_significance.csv`
- `*_cp_boundary.csv`

## MinIO 与清理

- 按总控 issue 协议上传和清理
