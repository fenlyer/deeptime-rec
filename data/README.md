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
├── download_data.py        # 下载脚本（⚠ 仍为 SNAP v1 版本，见第六节）
├── prepare_data.py         # 预处理脚本（⚠ 解析逻辑仍为 SNAP v1，见第六节）
├── quick_start.sh          # 一键下载 + 预处理（⚠ 同上）
│
├── raw_2023/               # Amazon 2023 实际数据（当前使用）
│   ├── IS_5core.csv.gz     # 评分文件（建模基础）
│   ├── TH_5core.csv.gz
│   ├── OP_5core.csv.gz
│   ├── loo/                # 可选：官方 LOO 划分
│   │   └── IS.{train,valid,test}.csv.gz
│   └── raw/                # 可选：评论与元数据（RAG 知识库用）
│       ├── IS_reviews.jsonl.gz
│       └── IS_meta.jsonl.gz
│
├── raw/                    # ⚠ SNAP v1 遗留目录（脚本默认读这里）
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

# 预处理（--k-core 0：2023 benchmark 已过滤，不要再过滤一遍）
python3 prepare_data.py --categories IS TH OP --k-core 0 --output-format csv

# 仅看统计
python3 prepare_data.py --categories IS --stats-only

# 输出：processed/{IS,TH,OP}/{train,val,test}.csv + item_meta.csv + id_maps/ + stats.json
```

`prepare_data.py` 的划分参数 `--val-ratio` / `--test-ratio` 默认 0.1/0.1，是**比例划分，
不是 LOO**。若要生成论文口径的 LOO 划分，优先直接使用 `raw_2023/loo/` 的官方文件；
需要自建时须改 `temporal_split()`（当前实现会取最后 10%，交互多的用户会有多条进测试集）。

## 六、已知问题（脚本与新数据尚未对齐）

以下问题已在 `data_list.txt` 中登记，尚未修复：

| # | 位置 | 问题 | 影响 |
|---|------|------|------|
| 1 | `download_data.py` | 全部 URL 指向 SNAP v1 的 `productGraph/` 与 `deepyeti/`。这些地址仍可访问（实测 SNAP 返回 200），返回的是 **2018 版** `reviews_*.json.gz`，与 docx 指定的 2023 版不是同一份数据 | 下到的是旧版数据，字段与统计均不符 |
| 2 | `download_data.py` | `EXPECTED_SIZES` 为 2018 版大小（IS 46.6MB 等），与 2023 版（6.8MB）不符 | 大小校验全部失败 |
| 3 | `prepare_data.py` | `RAW_DIR = data/raw`，`glob("*{category}*")` 找 `*.json.gz`；2023 数据在 `raw_2023/*.csv.gz` | 找不到输入文件 |
| 4 | `prepare_data.py` | `load_json_gz` 用 `json.loads` 逐行解析，2023 版是 JSONL 可解析，但 2018 版 meta 是 dict 字面量会全部跳过 | 已不适用（改用 2023 后 meta 可正常解析） |
| 5 | `prepare_data.py` | `CATEGORIES["AJ"] = "Automotive"`，而 docx 的 AJ 是 Alibaba IJCAI15 | 类别定义错误 |
| 6 | `prepare_data.py` | `temporal_split` 按比例划分，非 LOO | 与 docx 5.1.1 口径不符 |
| 7 | `quick_start.sh` | 调用 `--k-core 5`，对已过滤的 2023 数据会二次过滤并显著缩小 | 数据量异常偏小 |
| 8 | 全项目 | docx 表 5-1、4.1.3、表 3-4、3.4 选型中的 16,438/10,228/164,923 与实测 50,985/25,848/412,947 不符 | 论文数字需回改 |

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
