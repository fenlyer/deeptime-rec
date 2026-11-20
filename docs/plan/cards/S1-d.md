# S1-d 数字管线：results/ → numbers.json

- 周次：W1（11/20 – 11/26）
- 线：研究线（管线）
- 估时：0.5 天
- 依赖：S1-a（eval/）、S1-c（配对检验与分层）
- 阻塞：T-ch3 / T-ch4 / T-ch5（三张回填卡都从这里取数）

## 资源需求

| 类型 | 说明 |
|-----|------|
| **GPU** | ❌ 不需要 |
| **SSH** | 不需要（本机运行） |
| **时长** | ≈ 2 小时 |

## 为什么必须有这张卡

CLAUDE.md 红线 2：论文中的实验数字只能来自 `thesis/generated/numbers.json`，正文用 `{{n:key}}` 引用。
本卡是这条红线的**唯一实现**，也是 T-ch3/4/5 回填时"数字可溯源"的唯一依据。

V9 简化版原计划漏掉了这张卡，导致：
- 回填时只能手抄结果文件，无溯源链；
- `make tables` 目标（Makefile 已写）没有实现，永远报"尚未实现"。

## 目标

把 `results/` 下的 `metrics.json` / `per_user.parquet` / 分层 JSON 汇总为一张扁平的数字表，
每个数字带 `key`、`value`、`source`（结果文件路径）、`run`（exp/model/seed）四要素。

## 实现

`scripts/make_tables.py`：

```
results/{exp}/{model}/seed{n}/metrics.json  ──┐
results/{exp}/{model}/seed{n}/manifest.json ──┤
results/strata/*.json                        ──┼──> thesis/generated/numbers.json
results/*/paired_*.json                      ──┤
results/profile/*.json                       ──┘
```

### key 命名约定（与论文表号对应）

| 前缀 | 含义 | 例 |
|-----|------|-----|
| `recall.{model}.{metric}.mean` | 5 seed 均值 | `recall.ti_lightgcn.Recall@10.mean` |
| `recall.{model}.{metric}.std` | 5 seed 标准差 | `recall.ti_lightgcn.Recall@10.std` |
| `recall.{model}.{metric}.seeds` | 逐 seed 值 | `recall.ti_lightgcn.Recall@10.seeds` |
| `sig.{a}_vs_{b}.p_value` | 配对检验 | `sig.ti_vs_lg.p_value` |
| `strata.{model}.{layer}.Recall@10` | 分层 | `strata.ti_lightgcn.0-4.Recall@10` |
| `rank.{model}.{metric}.mean` | 排序指标 | `rank.temporal_din.AUC.mean` |
| `sys.{item}.{stat}` | 系统指标 | `sys.latency.P99` |
| `profile.{ds}.{field}` | 数据画像 | `profile.IS.gamma0` |

### 数值口径（不可违反）

- **均值/标准差只对 seed 聚合，不对用户聚合**；用户级统计走 `eval/paired_test.py`。
- 缺失值写 `null`，**不写 0、不写 "-"**；正文引用缺失 key 时构建失败。
- 保留原始精度（float repr），**不做任何取整**；取整只在论文排版层（`build_thesis.py --audit` 可查）。

## 产出

- `scripts/make_tables.py`
- `thesis/generated/numbers.json`
- `thesis/generated/tables/*.csv`（每张论文表一份，供排版对照）
- `tests/test_make_tables.py`

## 验收

- [ ] `make tables` 可从空 `results/` 运行不报错（输出空 numbers.json）
- [ ] 每个数字都有非空 `source` 字段，指向真实存在的文件
- [ ] 重复运行结果字节一致（排序稳定，无时间戳）
- [ ] 缺失指标的 key 不出现在输出里（而不是出现值为 null 的 key）
- [ ] pytest 通过

## 简化说明

- 不做表格排版（LaTeX/Word 生成归 T-ch3 手工回填）
- 不做跨表交叉校验（守恒检查在 `eval/strata.py` 已有）
- 不生成图（图由各实验卡自行产出）

## 论文落点

本卡不直接产出论文表，但**所有**实验数字表（3-6/3-7/3-8/3-10/3-12/3-14/3-15/3-16/4-2/4-5/5-9/5-10/5-11）的数字均经本卡落到 `numbers.json` 后回填。
