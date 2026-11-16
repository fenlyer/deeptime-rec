# S2-a 召回基线 × 5 seed

- 周次：W2 基线（11/23 周一 – 11/29 周日）
- 线：研究线
- 估时：1 天人工 + 约 1.5 GPU 天（夜间队列）
- 依赖：G1

## 提示词

用 RecBole/RecBole-GNN 跑召回基线 BPR-MF、NGCF、LightGCN、SGL、SimGCL，数据为 IS 冻结切分（benchmark_filename）。
- 统一设置：d=64，最大 1000 轮，按验证集 NDCG@20 早停，耐心 30；所有运行经 common/run.py 记录。
- 先在 seed 0 上对每个模型做小网格调参（学习率、L2、各自关键超参，每个模型不超过 8 组），只看验证集；选定后写进 configs/recall/{model}_IS.yaml，并在 docs/decisions.md 记录网格与选择。
- 再用 seed 0–4 各跑一次正式实验，测试集评估一律调用 eval/full_rank.py。
- 写 experiments/run_recall.sh <model> <dataset>，一条命令复现一行；把全部命令追加到 experiments/queue.txt，由 queue.sh 后台执行，不在会话里等待。
全部完成后检查：每个 run 的 best_epoch ≥ 30，停止原因为耐心耗尽；不满足的列出来，不要自行改早停规则。

## 产出
configs/recall/*.yaml；results/recall_main/{model}/seed{0..4}/；experiments/run_recall.sh

## 验收
25 个 run 齐全；早停检查全部通过；make_tables 能生成召回基线表

## 论文落点
第 3 章对比方法与主结果表（基线行）；附录超参数表
