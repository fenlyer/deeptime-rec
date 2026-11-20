# V9 周关口（gates）

5 周冲刺，每周一个关口。条件全部为「可机械验证」的条目：能跑一条命令、能看一个文件是否存在，
不写「基本完成」「效果良好」这类无法判定的描述。

- 判定：`make gate W=n` → `python -m gates.wn`，任一条件失败则非零退出。
- 关口通过**不等于**任务卡完成；关口只检查「本周必须为真的东西」。
- 顺序：G1 → G2 → G3 → G4 → G5，前一个不过不进入下一个的实验性工作。

---

## G1 · 11/21（W1 收口）评估地基 + 召回启动

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | 冻结数据可校验 | `sha256sum -c data/CHECKSUMS.sha256` 全 OK |
| 2 | 统一评估可复现 | `make test PY=/opt/anaconda3/bin/python3` 全过 |
| 3 | RecBole 环境可复现 | `environment/recbole.yml` 存在且 `conda env list` 有对应环境；冒烟 run 在 `results/_smoke/` |
| 4 | 数字管线可运行 | `make tables` 成功，产出 `thesis/generated/numbers.json` |
| 5 | 数据画像图就绪 | `figures/profile/IS_*.svg` 至少 5 个（含长尾与边权两张时另记） |
| 6 | 召回基线至少 1 个跑通 | `results/ch3_recall/baselines/` 下存在至少一个 `seed0/metrics.json` |
| 7 | 原型现状可查 | `docs/prototype_inventory.md` 存在 |

## G2 · 11/28（W2 收口）TI-LightGCN 主实验

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | 召回基线 25 runs | `results/ch3_recall/baselines/*/seed{0..4}/metrics.json` 共 25 个 |
| 2 | TI-LightGCN 代码与单测 | `models/ti_lightgcn.py` 存在；`tests/test_ti_lightgcn.py` 通过 |
| 3 | 主结果 5 seed | `results/ch3_recall/ti_lightgcn/seed{0..4}/metrics.json` 共 5 个 |
| 4 | α_r 与代码一致 | 表 3-1 五档权重逐一等于代码常量（单测断言） |
| 5 | 边权数值正确 | 单测覆盖 w(u,i)=α_r·exp(-λΔt/T) 的边界与单调性 |

## G3 · 12/05（W3 收口）召回实验全量

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | 表 3-6 完整 | 6 行模型 + 提升行，`numbers.json` 中对应 key 齐全 |
| 2 | 显著性检验完成 | `results/sig/*.json` 存在，p 值与效应量齐全 |
| 3 | 消融 9 runs | `results/ch3_recall/ablation/*/seed{0..2}/metrics.json` 共 9 个 |
| 4 | 敏感性至少 3 行 | λ / L / d 三组扫描完成，每组 ≥3 个候选值 |
| 5 | 画像五图齐 | 含商品长尾分布与边权分布（论文 3.1 节两张缺脚本的图） |

## G4 · 12/12（W4 前段）召回收尾 + 排序启动

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | 分层四层口径 | `eval/strata.py` 的 LAYERS 为 0-4/5-9/10-29/≥30；守恒校验通过 |
| 2 | 分层结果与表 3-11 一致 | IS 四层占比 ≈ 53.7/33.5/11.9/0.9（±0.1pp） |
| 3 | 跨域完成 | TH / OP 各 LightGCN + TI-LightGCN × 3 seed；AJ 列已决（跑或删） |
| 4 | 效率表可填 | 训练日志含单 epoch 耗时、峰值显存、收敛 epoch |
| 5 | DIN 基线 5 seed | `results/ch4_rank/baselines/din/seed{0..4}/metrics.json` |
| 6 | 候选集固定 | `results/ch4_rank/candidates/ti_top100.parquet` 存在且与主实验结果同源 |

## G5 · 12/19（W5 前段）排序 + 系统 + 回填

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | Temporal-DIN 5 seed | `results/ch4_rank/temporal_din/seed{0..4}/` |
| 2 | 蒸馏版 5 seed | `results/ch4_rank/temporal_din_distill/seed{0..4}/` |
| 3 | User Memory 产物 | `artifacts_llm/user_memory.*` 与 manifest 的 data_scope |
| 4 | 服务可启动且接口一致 | `serving/`（或 backend/）启动后 `/api/recommend` 返回 200；路径与表 5-7 一致 |
| 5 | 系统评测三项 | 压测（50 并发）、延迟分解、一致性校验结果文件齐 |
| 6 | 第三章/第四章无待实验 | 正文中 `【待实验` 在第三、四章计数为 0 |
| 7 | 数字全部可溯源 | 回填的每个数字在 `numbers.json` 中有 key 与 source |

---

## 与 V9 计划的对应关系

| 关口 | 覆盖任务卡 |
|-----|-----------|
| G1 | S0-a, S0-b, S1-a, S1-b, S1-c, S1-d, T-profile |
| G2 | S-recall-base, S-recall-main |
| G3 | S-recall-ablation, S-recall-sens, T-ch3（部分） |
| G4 | S-recall-cross, S-recall-cold, S-rank-base |
| G5 | S-rank-main, S-rank-distill, E-serve, S-system-test, T-ch3, T-ch4, T-ch5 |

## 说明

- G1 条件 5 与 7 在 STATUS.md 里写作「数据画像图 5 张」「原型现状表」，本文件按可机械验证的方式重写。
- `gates/w1.py` ~ `gates/w5.py` 尚未实现；实现前 `make gate W=n` 会明确报「尚未实现」而非静默通过。
