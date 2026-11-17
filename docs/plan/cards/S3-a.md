# S3-a TI-LightGCN 实现与命题测试

- 周次：W3 TI-LightGCN 主实验（11/30 周一 – 12/06 周日）
- 线：研究线
- 估时：1 天
- 依赖：S1-b、S0-b

## 提示词

在 models/ti_lightgcn.py 实现 TI-LightGCN（PyG，保留自研训练循环，不进入 RecBole；与第 6 章系统代码一致）：
- 边权 w(u,i) = α_r · exp(−λ · (τ_u − t_ui) / Δ_day)，只用训练集交互。τ_u 支持 global（训练集最大时间戳）与 user（该用户训练集最后一次交互时间）两种。λ 默认取 results/profile/IS.json 的 λ0。
- α_r 由配置给出（只有比值有意义）；rating≤2 的处理支持 in_graph（权重 α_1,2）、drop（不入图，只作 BPR 硬负）、signed（先 raise NotImplementedError）。
- 归一化 Ã = D^(-1/2) A D^(-1/2)，D 为加权度。加权邻接的构造写成独立函数 build_weighted_adj()，以后 TI-SimGCL 复用。
- 长尾正则：固定投影（SBERT 384 维经 PCA 降到 64 维，一次性算好存文件）的余弦形式，系数记为 μ。
先写 tests/test_ti_lightgcn.py：
 (1) 所有边权为 1 时，传播结果与自研 LightGCN 参考实现逐元素相等（容差 1e-6）；
 (2) 边权整体乘常数 c 时 Ã 不变；global 时钟下改变 T_now，Ã 不变（命题 1）；
 (3) 小图上 Ã 的特征值都落在 [−1, 1]（命题 2）。
测试全部通过后再接入训练脚本。

## 产出
models/ti_lightgcn.py；tests/test_ti_lightgcn.py；artifacts_static/tail_pca64.npy

## 验收
三项测试通过

## 论文落点
第 3 章模型、命题 1 与 2；附录命题的数值验证；实验设置注明基线来自 RecBole / RecBole-GNN 官方实现
