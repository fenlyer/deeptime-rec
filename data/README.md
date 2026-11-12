# 数据集目录说明

完整下载清单、URL、字节数与校验命令见 [`data_list.txt`]。

---

## 一、数据集版本

本项目使用 **Amazon Review Dataset 2023**（McAuley Lab, UCSD）的 IS / TH / OP 三个类目，
以及 **Alibaba IJCAI15**（AJ）行为日志，全部经 5-core 过滤。

> **IS 的定位**：`Industrial & Scientific` 是 Amazon 面向个人消费者、实验室与中小企业的
> **零售（B2C）类目**（实验器材、测量仪器、防护用品、工业耗材），并非大宗工业品批发的
> B2B 平台。本文将其作为「品类最贴近工业采购场景的公开代理数据集」使用，结论的适用边界
> 据此收窄，详见论文 5.1.1。

---

## 二、数据集概览

| 数据集 | 全称 | 用户数 | 商品数 | 交互对数 | 行为记录数 | 稀疏度 | 均交互/用户 | 时间跨度 |
|---|---|---|---|---|---|---|---|---|
| IS | Industrial & Scientific | 50,985 | 25,848 | 412,947 | 412,947 | 99.9687% | 8.10 | 2001-07 ~ 2023-08 |
| TH | Tools & Home Improvement | 842,050 | 274,732 | 7,891,024 | 7,891,024 | 99.9966% | 9.37 | 1999-11 ~ 2023-09 |
| OP | Office Products | 223,308 | 77,551 | 1,800,878 | 1,800,878 | 99.9896% | 8.06 | 1999-08 ~ 2023-09 |
| AJ | Alibaba IJCAI15 | 420,027 | 574,926 | 30,875,771 | 35,336,563 | 99.9872% | 73.51 | 2014-05 ~ 2014-11 |

- 最小用户交互 5、最小商品交互 5（5-core 过滤后）
- Amazon 三个数据集的**交互对数 = 行为记录数**：每个用户-物品对只有一条评分记录
- AJ 的**行为记录数 > 交互对数**：同一对可有多条 `action_type` 事件

> 以上数字以 `processed/{name}/stats.json` 为准，可用
> `python data/verify_4_1_data.py <NAME>` 复核。

---

## 三、行为 / 反馈口径

Amazon 数据集**不含**点击、加购、收藏、曝光等原生行为日志，仅有 1~5 分评分。
预处理阶段按评分派生伪行为标签（**仅为兼容旧代码，论文 4.1 节已改为按反馈强度建模**）：

| 来源 | 原始字段 | 映射后 | 反馈强度权重 α |
|---|---|---|---|
| Amazon | rating=5 | buy | 3.0 |
| Amazon | rating=4 | collect | 1.5 |
| Amazon | rating=3 | click | 1.0 |
| Amazon | rating=1 或 2 | show | 0.1 |
| AJ | action_type=0 | click | 1.0 |
| AJ | action_type=1 | cart | 1.2 |
| AJ | action_type=2 | buy | 3.0 |
| AJ | action_type=3 | collect | 1.5 |

- Amazon 侧**恒无 cart**（`cart.count = 0`），表 4-1 的 1.2 档位仅对 AJ 与线上系统有意义
- 论文式(4-1) 统一写作 `w = α_r · exp(-λ·(T_now−t)/T)`：Amazon 侧 α_r 由评分查表，
  AJ 侧 α 由 action_type 折算，两者共用同一张加权二部图

---

## 四、处理产物（每个数据集 `processed/{name}/` 一致）

| 文件 | 列 | 对应论文位置 |
|---|---|---|
| `train.csv` | user_id, item_id, behavior, timestamp, n_records, alpha, is_positive, is_hard_negative, rating, user_idx, item_idx | 5.1.1 LOO 划分 |
| `val.csv` | 同上 | 5.1.1 LOO 划分（倒数第二条） |
| `test.csv` | 同上 | 5.1.1 LOO 划分（最后一条） |
| `edges.csv` | user_idx, item_idx, weight | **4.1.2 式(4-1) 加权边** |
| `triples.csv` | user_idx, pos_item_idx, neg_item_idx | 4.1.2 式(4-6) BPR 三元组 |
| `item_meta.csv` | item_id, title, brand, category, price, description, features, details | 4.3 / 4.5 RAG 知识库 |
| `stats.json` | 规模、稀疏度、长尾、行为分布、边权重统计、划分校验 | 表5-1、4.1.3、4.1.4 |
| `id_maps/{user2idx,item2idx}.json` | 原始 ID ↔ 连续索引 | 全部建模脚本 |

---

## 五、论文章节 → 脚本 → 产物 映射

### 5.1 唯一入口（产物生成）

| 脚本 | 职责 | 产物 |
|---|---|---|
| `prepare_data.py` | 预处理**唯一入口**：探测→加载→聚合→5-core→行为权重→统计→LOO 划分→连续 ID / 边权重 / BPR 三元组 | `processed/{name}/*` 全部文件 |

```bash
python data/prepare_data.py                              # IS/TH/OP 全量
python data/prepare_data.py --categories IS --with-triples
python data/prepare_data.py --categories AJ              # 需 ~2GB 内存
```

### 5.2 论文口径核验（只读，不写产物）

| 脚本 | 覆盖章节 | 核验内容 |
|---|---|---|
| `verify_5_1_data.py` | **表5-1** | 四数据集的用户数、商品数、交互数、稀疏度、平均交互/用户、时间跨度；内置与 `stats.json` 的交叉校验 |
| `verify_4_1_data.py` | **4.1.1 / 4.1.2 / 4.1.3 / 4.1.4 / 5.8.1** | 规模常数、评分分布、长尾占比、时间跨度、式(4-1) 在 λ=0.1/0.01/0.001 下的权重分布 |
| `verify_5_6_cold_start.py` | **5.6.1**（表5-8 分层占比）<br>5.6.2 / 5.6.3（表5-9、5-10 需模型输出） | 训练集口径的用户分层人数、占比、层内人均交互；测试集每题用户数 |

```bash
python data/verify_5_1_data.py                     # 表5-1 全表
python data/verify_5_1_data.py --check             # 附带 stats.json 一致性校验
python data/verify_5_1_data.py --markdown          # Markdown 表格，便于粘回论文

python data/verify_4_1_data.py                     # IS，全部小节
python data/verify_4_1_data.py IS --section lambda  # 只看 λ 敏感性
python data/verify_4_1_data.py IS TH OP AJ         # 四数据集对比

python data/verify_5_6_cold_start.py               # IS 分层表
python data/verify_5_6_cold_start.py IS --json     # JSON，便于回填论文
```

### 5.3 论文数字 → 脚本命令 对照

| 论文位置 | 数字 | 核验命令 |
|---|---|---|
| 表5-1 | 四数据集规模（用户/商品/交互/稀疏度/时间跨度） | `verify_5_1_data.py --check` |
| 4.1.1 局限一 | 评分分布 72.3/13.7/5.8/8.2 | `verify_4_1_data.py IS --section rating` |
| 4.1.1 局限二 | 时间跨度 22.1 年 | `verify_4_1_data.py IS --section span` |
| 4.1.2 式(4-1) | λ=0.001、半衰期 693 天 | `verify_4_1_data.py IS --section lambda` |
| 4.1.3 | \|U\|=50985、\|I\|=25848、\|E\|=412947 | `verify_4_1_data.py IS --section scale` |
| 4.1.4 | 前20%占56.5%、长尾53.0%承载21.6% | `verify_4_1_data.py IS --section tail` |
| 5.6.1 表5-8 | 分层占比 53.7/33.5/11.9/0.9 | `verify_5_6_cold_start.py IS` |
| 5.8.1 | λ 敏感性候选网格 | `verify_4_1_data.py IS --section lambda` |

---

## 六、口径注意事项

1. **统计单位是「用户-物品对」，不是行为记录**。AJ 按行计数会把 3533 万条记录误当成交对数，
   稀疏度与人均交互都会偏高；所有核验脚本均先 `drop_duplicates(['user_id','item_id'])`。
2. **训练集口径 vs 全量口径**。5-core 保证全量交互 ≥5 条，但 LOO 切走 test+val 两条后，
   全量 5~6 条的用户在训练集只剩 3~4 条，故 5.6.1 的超冷启动层（0~4 条）占比高达 53.7%。
   这不是数据错误，表5-8 已注明「训练集口径」。
3. **`stats.json` 的 `tail_item_ratio` 阈值为 <10**，与论文 4.1.4 的 θ=10 一致；
   4.1.4 的「覆盖 80% 交互所需商品比例」不在 stats.json 中，由 `verify_4_1_data.py` 现算。
4. **`behavior` 列是派生的伪标签**，仅用于兼容与 AJ 对齐；论文 4.1 节已改为按 `rating`
   映射反馈强度 α_r，请勿在正文中以 `behavior` 作论证依据。
