# 数据集目录说明

> 数据基准：`docs/1109-整改V7.docx`（5.1.1 数据集选取、表 5-1、表 4-1、4.1.4）
> 完整下载清单、URL、字节数与校验命令见 [`data_list.txt`](./data_list.txt)
> 更新日期：2026-11-11

## 一、数据集版本

本项目使用 **Amazon Review Dataset 2023**（McAuley Lab, UCSD），
即论文参考文献 [38]（arXiv:2403.03952）对应的数据集版本。

⚠ **不再使用 SNAP v1（2018 版）**。两版差异如下，迁移时务必注意：

| | SNAP v1（2018，已废弃） | Amazon 2023（当前） |
|---|---|---|
| 用户标识 | `reviewerID` | `user_id` |
| 商品标识 | `asin` | `parent_asin` |
| 评分字段 | `overall`（int） | `rating`（float） |
| 时间戳 | `unixReviewTime`（秒） | `timestamp`（毫秒） |
| 评论正文字段 | `reviewText` / `summary` | `text` / `title` |
| 已验证购买 | `verified` | `verified_purchase` |
| 元数据主键 | `asin` | `parent_asin` |
| 元数据格式 | Python dict 字面量（单引号，`ast.literal_eval` 才能解析） | 标准 JSONL |
| 元数据品牌字段 | `brand` | `store`（品牌名）+ `details.Brand` |
| 官方 5-core | 无（需自行过滤） | **有**（`benchmark/5core/`） |

## 二、数据集概览

| 数据集 | 简称 | 角色（对应 docx） | 5-core 实测量级 |
|--------|------|------------------|----------------|
| Industrial & Scientific | IS | 主实验（5.2~5.4） | 50,985 用户 / 25,848 商品 / 412,947 交互 |
| Tools & Home Improvement | TH | 跨域验证（5.4.2 表 5-5） | 下载中，待实测 |
| Office Products | OP | 跨域验证（5.4.2 表 5-5） | 223,308 用户 / 77,551 商品 / 1,800,878 交互 |
| Alibaba IJCAI15 | AJ | 多行为加权独立验证（原生 click/cart/purchase） | 待下载实测 |

⚠ 上表中 IS 与 OP 均为实测值，与 docx 表 5-1 的 16,438/10,228/164,923 与
18,763/12,457/198,341 相差 2.5~12 倍，表 5-1 需按实测回填（见 `data_list.txt` 第七节）。

AJ 不是 Amazon 数据，需从天池 `dataset/42` 登录下载，详见 `data_list.txt` 第三节。

## 三、目录结构

```
data/
├── data_list.txt           # 下载清单：URL、精确字节数、校验脚本（权威）
├── README.md               # 本文件：版本差异、字段映射、脚本用法
├── compute_dataset_stats.py # 统计脚本（输出实测数据）
├── prepare_data.py         # 预处理脚本（⚠ 仍为 SNAP v1，见第六节）
├── quick_start.sh          # 一键下载 + 预处理（⚠ 同上）
│
├── raw_2023/               # Amazon 2023 实际数据（当前使用）
│   ├── IS_5core.csv.gz     # 评分文件（建模基础）
│   ├── TH_5core.csv.gz
│   ├── OP_5core.csv.gz
│   ├── loo/                # 官方 LOO 划分
│   │   ├── IS.{train,valid,test}.csv.gz
│   │   ├── TH.{train,valid,test}.csv.gz
│   │   └── OP.{train,valid,test}.csv.gz
│   └── raw/                # 评论与元数据（RAG 知识库用）
│       ├── IS_reviews.jsonl.gz
│       ├── IS_meta.jsonl.gz
│       ├── TH_reviews.jsonl.gz
│       ├── TH_meta.jsonl.gz
│       ├── OP_reviews.jsonl.gz
│       └── OP_meta.jsonl.gz
│
├── raw_aj/                 # AJ 天猫数据（已解压）
│   ├── data_format1/
│   │   ├── user_log_format1.csv   # 核心行为日志
│   │   ├── user_info_format1.csv  # 用户属性（可选）
│   │   ├── train_format1.csv      # 复购标签
│   │   └── test_format1.csv
│   ├── data_format2/
│   └── sample_submission.csv
│
└── processed/              # 预处理输出
    └── IS/
        ├── train.csv / val.csv / test.csv
        ├── item_meta.csv
        ├── id_maps/user2idx.json, item2idx.json
        └── stats.json
```

## 四、数据文件说明

### 4.1 评分文件（`raw_2023/{IS,TH,OP}_5core.csv.gz`）

来自 `benchmark/5core/rating_only/`，**已完成 5-core 过滤**（用户与商品交互数均 ≥5，
无需再次过滤）。

```
user_id,parent_asin,rating,timestamp
AFNT6ZJCYQN3WDIKUSWHJDXNND2Q,B00DX7KEP8,2.0,1546537517929
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | str | 用户 ID（32 位大写字母数字） |
| `parent_asin` | str | 商品父级 ASIN，join 元数据时用它 |
| `rating` | float | 1.0~5.0 |
| `timestamp` | int | 毫秒级 UNIX 时间戳 |

行为类型由 `rating` 推导，规则见 docx 5.1.1 与表 4-1：

| rating | 行为 | 权重 α_b |
|--------|------|---------|
| 5 | buy | 3.0 |
| 4 | collect | 1.5 |
| 3 | click | 1.0 |
| 1~2 | show | 0.1 |

Amazon 数据无原生加购（cart）事件，权重 1.2 仅用于 AJ 与线上环境。

### 4.2 官方 LOO 划分（`raw_2023/loo/`，可选）

来自 `benchmark/5core/last_out/`，**口径与 docx 5.1.1 的留一法完全一致**：
每位用户最后一条 → test，倒数第二条 → valid，其余 → train。

已实测验证（IS）：三份文件合计 412,947 条，与 `rating_only` 全量一致；
50,984/50,985 位用户的最后一条落在 test、倒数第二条落在 valid。
**建议直接用官方划分，不必自己实现 LOO。**

### 4.3 评论文件（`raw_2023/raw/IS_reviews.jsonl.gz`）

从 `raw/review_categories/` 获取。每行一个 JSON 对象：

```json
{"rating": 5.0, "title": "...", "text": "...", "images": [],
 "asin": "...", "parent_asin": "...", "user_id": "...",
 "timestamp": 1676602453163, "helpful_vote": 3, "verified_purchase": true}
```

用途：docx 双层知识库的「用户评论摘要层」；若采用 `verified_purchase +
helpful_vote + rating` 三维度行为推导（见 `data_list.txt` 第四节），此文件为必需。

### 4.4 元数据文件（`raw_2023/raw/IS_meta.jsonl.gz`）

从 `raw/meta_categories/` 获取：

```json
{"main_category": "Industrial & Scientific", "title": "...",
 "average_rating": 4.4, "rating_number": 206,
 "features": ["...", "..."], "description": ["..."],
 "price": 14.27, "images": [{"thumb": "...", "large": "..."}],
 "videos": [], "store": "Carlisle FoodService Products",
 "categories": ["Industrial & Scientific", "..."],
 "details": {"Material": "Polypropylene", "Color": "green",
             "Brand": "...", "Item Dimensions LxWxH": "8 x 8 x 1 inches"},
 "parent_asin": "B07N83D8HC", "bought_together": null}
```

字段映射到处理后的数据：

| 2023 原字段 | 处理后期望字段 | 用途 |
|------------|--------------|------|
| `parent_asin` | `item_id` | join 键 |
| `title` | `title` | 商品展示、Sentence-BERT 编码 |
| `store` / `details.Brand` | `brand` | 品牌偏好 |
| `categories[0]` | `category` | 类目 |
| `description` + `features` | `description` / `features` | 知识库属性文档 |
| `details`（键值对） | `spec_text` | 技术规格自然语言化（docx 3.x metadata 表） |
| `price` | `price` | 价格区间 |
| `images[0].large` | `img_url` | 前端商品图 |

`details` 是 2023 版相对 2018 版的最大增益：Material/Color/Brand/Style/Dimensions
等结构化键值可直接转成规格文本，用于 docx 4.x 的「商品属性文档」层与
4.1.4 长尾正则化的语义锚点 ẽ_i^sem。

## 五、脚本用法

```bash
cd data

# 统计实测数据（输出用户数/商品数/交互数/行为分布等）
python3 compute_dataset_stats.py

# 预处理（--k-core 0：2023 benchmark 已过滤，不要再过滤一遍）
python3 prepare_data.py --categories IS TH OP --k-core 0 --output-format csv

# 仅看统计
python3 prepare_data.py --categories IS --stats-only
```

下载分组：

| 分组 | 内容 | 体积 |
|------|------|------|
| `core` | IS/TH/OP 三个 5-core 评分文件 | 172 MB |
| `rag` | IS 评论原文 + IS 商品元数据 | 913 MB |
| `loo` | 官方 LOO 划分（9 个 train/valid/test） | 212 MB |
| `meta` | TH/OP 商品元数据 | 1.6 GB |
| `reviews-ext` | TH/OP 评论原文（默认不下） | 4.8 GB |

`download_data.py` 的下载行为：

- 写入 `<file>.part`，**精确字节数 + `gzip -t` 双重校验通过后**才原子改名为正式文件
- 用 `flock` 排他锁防止多进程写同一文件
- 断点续传由 Python 侧重试驱动，**不使用 `curl --retry`**（它配合 `-C -` 会截断文件）
- `--speed-limit/--speed-time` 识别长时间零速的僵死连接

输出：`processed/{IS,TH,OP}/{train,val,test}.csv` + `item_meta.csv` + `id_maps/` + `stats.json`

`prepare_data.py` 默认 `--split-mode loo`（留一法，对齐 docx 5.1.1）。
已实测验证：IS 自建 LOO 划分与官方 `last_out/` **逐条完全一致**
（train/val/test = 310,977 / 50,985 / 50,985，test 集 50,985 条交集全中、零差异）。
需要旧的按比例划分时用 `--split-mode ratio`。

## 六、脚本与新数据的对齐状态

已修复（2026-11-11）：

| 脚本 | 改动 |
|------|------|
| `compute_dataset_stats.py` | 新增：统计 Amazon 2023 和 AJ 的实测数据 |
| `prepare_data.py` | `RAW_DIR` 改 `raw_2023/`；新增 CSV 读取（2023 的 5-core 是 CSV 不是 JSON）；毫秒→秒时间戳转换；`temporal_split` 新增 `--split-mode loo`（默认）；`CATEGORIES` 移除错误的 `AJ=Automotive` |
| `quick_start.sh` | 改调新分组参数；`--k-core 5` → `--k-core 0`；增加下载后校验步骤 |

待处理：

| # | 位置 | 问题 |
|---|------|------|
| 1 | `prepare_data.py` | 未实现 AJ（Alibaba IJCAI15）的加载路径。该数据集格式为 `user_id,item_id,cat_id,seller_id,brand_id,time_stamp,action_type`，与 Amazon 不同，需单独处理 |
| 2 | `prepare_data.py` | 行为类型推导（rating→buy/collect/click/show）尚未写入，当前输出只有 `rating` 原值 |
| 3 | 论文 | docx 表 5-1、4.1.3、表 3-4、3.4 选型的数字与实测不符，见 `data_list.txt` 第七节 |
| 4 | 行为加权设计 | buy 占比 72~73%，α_b 近似退化为常数，消融实验难做出差异；方案待定，见 `data_list.txt` 第四节 |

已删除：

| 脚本 | 说明 |
|------|------|
| `download_data.py` | 数据已下载完成，脚本不再需要 |

## 七、数据源

- **Amazon 2023 官方**：https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/
  - 5-core 评分：`benchmark/5core/rating_only/{Category}.csv.gz`
  - 官方 LOO：`benchmark/5core/last_out/{Category}.{train,valid,test}.csv.gz`
  - 原始评论：`raw/review_categories/{Category}.jsonl.gz`
  - 商品元数据：`raw/meta_categories/meta_{Category}.jsonl.gz`
- **AJ（天猫）**：https://tianchi.aliyun.com/dataset/42 （需登录）
- 数据集论文：Hou Y, Li J, He Z, et al. Bridging Language and Items for Retrieval
  and Recommendation. arXiv:2403.03952, 2024

## 八、注意事项

- **务必校验完整性**。2026-11-11 曾出现 TH/OP 下载中途截断（`gzip -t` 报
  `unexpected end of file`）却因文件名正确而被误认为已完成的情况。
  下载后请执行 `data_list.txt` 第五节的字节数 + `gzip -t` 双重校验。
- UCSD 服务器下行速度不稳定（实测 2~30 MB/min），下载大文件请用 `curl -C -` 续传。
- meta 文件较大（IS 268MB / TH 1.1GB / OP 504MB），建议在带宽更好的机器上下载后拷贝。
- 处理后 `id_maps/` 必须与训练、推理保持同一份，否则嵌入索引对不上号。
