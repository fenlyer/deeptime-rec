# S3-d 跨域：OP、TH 子采样、AJ 子采样

- 周次：W4 召回收尾与冻结（12/07 周一 – 12/13 周日）
- 线：研究线
- 估时：1 天人工 + 约 1.5 GPU 天
- 依赖：S3-b

## 提示词

1. 写 data/subsample.py：TH 随机抽 10 万用户、AJ 抽 5 万用户（数量与 seed 可配置），保留其全部交互后重新做 5-core 与 LOO，复用 data/prepare_data.py 里的函数，不复制逻辑。产出 processed/TH_s100k/、processed/AJ_s50k/，更新 CHECKSUMS，打 tag data-v1-sub；抽样参数写进 docs/预处理口径冻结.md 附录。
2. AJ 的多行为到 α 的映射先读 docs/预处理口径冻结.md；没有定义就停下来问我，不要自行设定。
3. 在 OP、TH_s100k、AJ_s50k 上跑 LightGCN、SimGCL、TI-LightGCN，各 3 个 seed（表注写明），超参沿用 IS 上选定的比例，不在这些数据集的测试集上调参。

## 产出
data/subsample.py；processed/TH_s100k/、AJ_s50k/；results/cross/

## 验收
3 数据集 × 3 模型 × 3 seed 齐全；tag data-v1-sub 存在

## 论文落点
第 3 章跨域表（替换 V8 表 5-5，平均提升列由脚本计算）
